import importlib.util
import io
import json
import re
import textwrap
import base64
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("deployment", ROOT / "iac/scripts/deploy.py")
deployment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deployment)


class RunnerAccessTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.calls = []
        self.region = {"resourceGroup": "demo", "serverName": "database", "storageName": "host"}

    def invoke(self, *args):
        self.calls.append(args)
        return {"ipRules": []}

    def access(self, invoke=None):
        return deployment.RunnerAccess(Path(self.directory.name) / "access.json", invoke or self.invoke)

    def test_cleanup_removes_only_recorded_rules_and_is_repeatable(self):
        access = self.access()
        access.add_database(self.region, "192.0.2.1", "unique-rule")
        access.add_storage(self.region, "192.0.2.1")
        access.cleanup()
        count = len(self.calls)
        access.cleanup()
        self.assertEqual(count, len(self.calls))
        self.assertIn("unique-rule", self.calls[-1])
        self.assertEqual([], json.loads(access.path.read_text()))

    def test_preexisting_storage_rule_is_not_removed(self):
        access = self.access(lambda *args: {"ipRules": [{"ipAddressOrRange": "192.0.2.1/32"}]})
        access.add_storage(self.region, "192.0.2.1")
        self.assertEqual([], access.entries)

    def test_failed_creation_still_leaves_a_cleanup_record(self):
        def fail(*args):
            raise subprocess.CalledProcessError(1, "az", stderr="simulated failure")
        access = self.access(fail)
        with self.assertRaises(subprocess.CalledProcessError):
            access.add_database(self.region, "192.0.2.1", "unique-rule")
        self.assertEqual("unique-rule", json.loads(access.path.read_text())[0]["rule"])

    def test_failed_cleanup_is_visible_and_preserves_state(self):
        access = self.access()
        access.add_database(self.region, "192.0.2.1", "unique-rule")
        def fail(*args):
            raise subprocess.CalledProcessError(1, "az", stderr="simulated cleanup failure")
        access.invoke = fail
        errors = io.StringIO()
        with self.assertRaisesRegex(RuntimeError, "cleanup FAILED"), redirect_stderr(errors):
            access.cleanup()
        self.assertEqual(1, len(json.loads(access.path.read_text())))
        self.assertIn("simulated cleanup failure", errors.getvalue())

    def test_cleanup_continues_after_one_rule_fails(self):
        access = self.access()
        access.add_database(self.region, "192.0.2.1", "unique-rule")
        access.add_storage(self.region, "192.0.2.1")
        def fail_storage(*args):
            self.calls.append(args)
            if args[0] == "storage":
                raise subprocess.CalledProcessError(1, "az", stderr="simulated storage failure")
        access.invoke = fail_storage
        with self.assertRaisesRegex(RuntimeError, "cleanup FAILED"), redirect_stderr(io.StringIO()):
            access.cleanup()
        self.assertEqual(["storage"], [entry["kind"] for entry in access.entries])
        self.assertIn("unique-rule", self.calls[-1])


class ReadinessSmokeTests(unittest.TestCase):
    def test_missing_authentication_must_not_succeed(self):
        region = {"functionHost": "example.invalid", "functionName": "example"}
        class Response:
            status = 200
            def __init__(self, body):
                self.body = body
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return self.body
        with patch.object(deployment, "az", return_value={"accessToken": "test-token"}), \
             patch.dict(deployment.os.environ, {"API_AUDIENCE": "api://test"}), \
             patch.object(deployment.urllib.request, "urlopen", side_effect=[
                 Response(b'{"status":"healthy"}'), Response(b'{"status":"ready"}'), Response(b"{}")]):
            with self.assertRaisesRegex(RuntimeError, "Unauthenticated API access was not denied"), \
                 redirect_stdout(io.StringIO()):
                deployment.smoke_test([region])


class TemplateContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = json.loads((ROOT / ".deployment/main.json").read_text())

    def test_regions_are_restricted_to_distinct_eu_locations(self):
        parameters = self.template["parameters"]
        self.assertEqual(["westeurope"], parameters["primaryLocation"]["allowedValues"])
        self.assertEqual(["northeurope"], parameters["recoveryLocation"]["allowedValues"])
        self.assertNotIn("eastus", parameters["primaryLocation"]["allowedValues"])
        self.assertTrue(set(parameters["primaryLocation"]["allowedValues"]).isdisjoint(
            parameters["recoveryLocation"]["allowedValues"]))

    def test_environment_contract(self):
        self.assertEqual(["dev", "prod"], self.template["parameters"]["environmentName"]["allowedValues"])
        recovery = next(value for value in self.template["resources"].values()
                        if value.get("type") == "Microsoft.Resources/deployments"
                        and value.get("name") == "[format('{0}-recovery', parameters('environmentName'))]")
        self.assertIn("'prod'", recovery["condition"])

    def test_security_and_retention_contracts_in_compiled_templates(self):
        resources = []
        def visit(template):
            values = template.get("resources", {})
            for resource in values.values() if isinstance(values, dict) else values:
                resources.append(resource)
                properties = resource.get("properties", {})
                nested = properties.get("template") if isinstance(properties, dict) else None
                if nested:
                    visit(nested)
        visit(self.template)
        storage = [r for r in resources if r["type"] == "Microsoft.Storage/storageAccounts"
                   and not r.get("existing", False)]
        self.assertTrue(storage)
        for resource in storage:
            self.assertIn("allowSharedKeyAccess", resource["properties"])
        functions_source = (ROOT / "iac/functions/main.bicep").read_text()
        self.assertIn("allowSharedKeyAccess: false", functions_source)
        self.assertIn("requireAuthentication: true", functions_source)
        self.assertIn("defaultAction: 'Deny'", functions_source)
        self.assertNotIn("AzureWebJobsStorage:", functions_source)
        monitoring_source = (ROOT / "iac/monitoring/main.bicep").read_text()
        self.assertIn("dataRetention: 400", monitoring_source)
        postgres_source = (ROOT / "iac/postgresql/main.bicep").read_text()
        self.assertIn("threshold: 900", postgres_source)
        self.assertNotIn("administratorLoginPassword:", postgres_source)
        alerts = [r for r in resources if r["type"] == "Microsoft.Insights/metricAlerts"]
        self.assertTrue(alerts)
        self.assertEqual(900, alerts[0]["properties"]["criteria"]["allOf"][0]["threshold"])
        self.assertEqual("physical_replication_delay_in_seconds",
                         alerts[0]["properties"]["criteria"]["allOf"][0]["metricName"])
        workspace_calls = [r for r in resources if r["type"] == "Microsoft.Resources/deployments"
                           and isinstance(r.get("properties"), dict)
                           and "dataRetention" in r["properties"].get("parameters", {})]
        self.assertTrue(workspace_calls)
        self.assertTrue(all(r["properties"]["parameters"]["dataRetention"]["value"] >= 366
                            for r in workspace_calls))


class WorkflowShellTests(unittest.TestCase):
    def test_every_current_workflow_run_step_has_valid_bash_syntax(self):
        for workflow in (ROOT / ".github/workflows").glob("*.yml"):
            lines = workflow.read_text().splitlines()
            scripts = []
            for index, line in enumerate(lines):
                match = re.match(r"^(\s+)run:\s*(.*)$", line)
                if not match:
                    continue
                indent, value = match.groups()
                if value == "|":
                    block = []
                    for following in lines[index + 1:]:
                        if following.strip() and len(following) - len(following.lstrip()) <= len(indent):
                            break
                        block.append(following)
                    script = textwrap.dedent("\n".join(block))
                else:
                    script = value
                scripts.append(script)
                with self.subTest(workflow=workflow.name, line=index + 1):
                    result = subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True)
                    self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(scripts, f"No run steps checked in {workflow}")


class DeploymentOrchestrationTests(unittest.TestCase):
    """Exercise the real orchestrator while replacing external Azure/HTTP processes."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state = Path(directory.name)
        self.calls = []
        self.http_requests = []
        self.package_failures = 0
        self.bootstrap_fails = False
        self.cleanup_fails = False
        self.primary = {
            "resourceGroup": "demo-primary", "serverName": "primary", "databaseName": "novabank",
            "databaseHost": "primary.postgres.database.azure.com", "functionName": "primary-api",
            "functionHost": "primary-api.azurewebsites.net", "storageName": "primaryhost",
            "identityName": "primary-identity", "identityPrincipalId": "66666666-6666-6666-6666-666666666666",
        }
        self.secondary = {
            **self.primary, "resourceGroup": "demo-recovery", "functionName": "recovery-api",
            "functionHost": "recovery-api.azurewebsites.net", "storageName": "recoveryhost",
            "identityName": "recovery-identity", "identityPrincipalId": "77777777-7777-7777-7777-777777777777",
        }
        self.regions = [self.primary]
        configuration = {
            "AZURE_CLIENT_ID": "11111111-1111-1111-1111-111111111111",
            "AZURE_TENANT_ID": "22222222-2222-2222-2222-222222222222",
            "AZURE_SUBSCRIPTION_ID": "33333333-3333-3333-3333-333333333333",
            "DATABASE_ADMIN_OBJECT_ID": "44444444-4444-4444-4444-444444444444",
            "DATABASE_ADMIN_NAME": "synthetic-deployment-principal",
            "API_CLIENT_ID": "55555555-5555-5555-5555-555555555555",
            "API_AUDIENCE": "api://55555555-5555-5555-5555-555555555555",
            "LOG_READER_GROUP_ID": "88888888-8888-8888-8888-888888888888",
            "ALERT_ACTION_GROUP_ID": (
                "/subscriptions/33333333-3333-3333-3333-333333333333/resourceGroups/monitor"
                "/providers/Microsoft.Insights/actionGroups/operators"),
        }
        claims = base64.urlsafe_b64encode(
            json.dumps({"oid": configuration["DATABASE_ADMIN_OBJECT_ID"]}).encode()).decode().rstrip("=")
        self.token = f"synthetic.{claims}.not-a-real-token"
        for replacement in (
            patch.object(deployment, "STATE", self.state),
            patch.dict(deployment.os.environ, configuration, clear=True),
            patch.object(deployment.subprocess, "run", side_effect=self.run_process),
            patch.object(deployment.urllib.request, "urlopen", side_effect=self.urlopen),
            patch.object(deployment.time, "sleep"),
        ):
            replacement.start()
            self.addCleanup(replacement.stop)

    def run_process(self, arguments, **kwargs):
        arguments = tuple(arguments)
        self.calls.append((arguments, kwargs))
        output = None
        if arguments[:3] == ("az", "account", "show"):
            output = {"id": deployment.os.environ["AZURE_SUBSCRIPTION_ID"]}
        elif arguments[:3] == ("az", "account", "get-access-token"):
            output = {"accessToken": self.token}
        elif arguments[:4] == ("az", "deployment", "sub", "create"):
            output = {"properties": {"outputs": {"regions": {"value": self.regions}}}}
        elif arguments[:5] == ("az", "storage", "account", "network-rule", "list"):
            output = {"ipRules": []}
        elif arguments[:2] == ("dotnet", "publish"):
            publish = Path(arguments[arguments.index("--output") + 1])
            publish.mkdir()
            (publish / "host.json").write_text('{"version":"2.0"}')
        elif arguments[0] == "psql" and self.bootstrap_fails:
            return subprocess.CompletedProcess(arguments, 1, "", "synthetic SQL failure")
        elif arguments[:5] == ("az", "functionapp", "deployment", "source", "config-zip"):
            if self.package_failures:
                self.package_failures -= 1
                raise subprocess.CalledProcessError(1, arguments, stderr="synthetic package failure")
        if self.cleanup_fails and arguments[:5] == (
                "az", "postgres", "flexible-server", "firewall-rule", "delete"):
            raise subprocess.CalledProcessError(1, arguments, stderr="synthetic cleanup failure")
        return subprocess.CompletedProcess(arguments, 0, json.dumps(output) if output else "", "")

    def urlopen(self, request, **kwargs):
        self.http_requests.append(request)
        if isinstance(request, str):
            if request == "https://api.ipify.org":
                return io.BytesIO(b"192.0.2.1")
            raise deployment.urllib.error.HTTPError(request, 401, "Unauthorized", {}, None)
        self.assertEqual(f"Bearer {self.token}", request.get_header("Authorization"))
        status = "healthy" if request.full_url.endswith("/health") else "ready"
        response = io.BytesIO(json.dumps({"status": status}).encode())
        response.status = 200
        return response

    def execute(self, environment="dev", preview=False):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            deployment.deploy(environment, preview)

    def test_preview_validates_and_previews_without_provisioning_or_firewall_changes(self):
        self.execute(preview=True)
        commands = [args for args, _ in self.calls]
        self.assertTrue(any(args[:4] == ("az", "deployment", "sub", "validate") for args in commands))
        self.assertTrue(any(args[:4] == ("az", "deployment", "sub", "what-if") for args in commands))
        self.assertFalse(any(args[:4] == ("az", "deployment", "sub", "create") for args in commands))
        self.assertFalse(any(args[0] in ("dotnet", "psql") for args in commands))
        self.assertEqual([], self.http_requests)

    def test_dev_runs_provision_bootstrap_publish_smoke_and_cleanup_in_order(self):
        self.execute()
        commands = [args for args, _ in self.calls]
        bootstrap = next(index for index, args in enumerate(commands) if args[0] == "psql")
        publish = next(index for index, args in enumerate(commands)
                       if args[:5] == ("az", "functionapp", "deployment", "source", "config-zip"))
        cleanup = next(index for index, args in enumerate(commands)
                       if args[:5] == ("az", "storage", "account", "network-rule", "remove"))
        self.assertLess(bootstrap, publish)
        self.assertLess(publish, cleanup)
        with deployment.zipfile.ZipFile(self.state / "api.zip") as package:
            self.assertEqual(["host.json"], package.namelist())
        self.assertEqual([], json.loads(next(self.state.glob("access-dev-*.json")).read_text()))
        self.assertEqual(4, len(self.http_requests))

    def test_prod_bootstraps_and_publishes_both_regions(self):
        self.regions.append(self.secondary)
        self.execute("prod")
        commands = [args for args, _ in self.calls]
        bootstrap = [args for args in commands if args[0] == "psql"]
        self.assertEqual(2, len(bootstrap))
        publish = [args for args in commands
                   if args[:5] == ("az", "functionapp", "deployment", "source", "config-zip")]
        self.assertEqual({"primary-api", "recovery-api"},
                         {args[args.index("--name") + 1] for args in publish})
        self.assertEqual(7, len(self.http_requests))
        self.assertEqual([], json.loads(next(self.state.glob("access-prod-*.json")).read_text()))

    def test_package_failure_retries_and_then_succeeds(self):
        self.package_failures = 1
        self.execute()
        self.assertEqual(2, sum(args[:5] == (
            "az", "functionapp", "deployment", "source", "config-zip") for args, _ in self.calls))

    def test_exhausted_package_retries_still_remove_network_access(self):
        self.package_failures = 12
        with self.assertRaises(subprocess.CalledProcessError):
            self.execute()
        self.assertEqual([], json.loads(next(self.state.glob("access-dev-*.json")).read_text()))

    def test_failed_sql_bootstrap_does_not_publish_and_removes_network_access(self):
        self.bootstrap_fails = True
        with self.assertRaisesRegex(RuntimeError, "bootstrap FAILED"):
            self.execute()
        self.assertFalse(any(args[:5] == (
            "az", "functionapp", "deployment", "source", "config-zip") for args, _ in self.calls))
        self.assertEqual([], json.loads(next(self.state.glob("access-dev-*.json")).read_text()))

    def test_cleanup_failure_fails_successful_deployment_and_keeps_journal(self):
        self.cleanup_fails = True
        with self.assertRaisesRegex(RuntimeError, "cleanup FAILED"):
            self.execute()
        entries = json.loads(next(self.state.glob("access-dev-*.json")).read_text())
        self.assertEqual(["database"], [entry["kind"] for entry in entries])


if __name__ == "__main__":
    unittest.main()
