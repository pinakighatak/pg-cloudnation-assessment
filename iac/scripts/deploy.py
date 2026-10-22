#!/usr/bin/env python3
"""Deploy the demo using an existing Azure CLI OIDC session."""

import argparse
import base64
import ipaddress
import json
import os
from pathlib import Path
import signal
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".deployment"
REQUIRED = (
    "AZURE_CLIENT_ID", "AZURE_TENANT_ID", "AZURE_SUBSCRIPTION_ID",
    "DATABASE_ADMIN_OBJECT_ID", "DATABASE_ADMIN_NAME", "API_CLIENT_ID",
    "API_AUDIENCE", "LOG_READER_GROUP_ID", "ALERT_ACTION_GROUP_ID",
)


def az(*arguments):
    result = subprocess.run(
        ["az", *arguments, "--only-show-errors", "--output", "json"],
        check=True, text=True, capture_output=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else None


def check_configuration():
    for key in REQUIRED:
        if not os.environ.get(key):
            raise ValueError(f"Required environment variable is missing: {key}")
    for key in REQUIRED:
        if key.endswith("_ID") and key != "ALERT_ACTION_GROUP_ID":
            if uuid.UUID(os.environ[key]).int == 0:
                raise ValueError(f"Replace the placeholder GUID in {key}")
    subscription = os.environ["AZURE_SUBSCRIPTION_ID"]
    if az("account", "show")["id"].lower() != subscription.lower():
        raise ValueError("The Azure CLI subscription does not match AZURE_SUBSCRIPTION_ID")
    token = az("account", "get-access-token")["accessToken"]
    payload = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    if claims.get("oid", "").lower() != os.environ["DATABASE_ADMIN_OBJECT_ID"].lower():
        raise ValueError("DATABASE_ADMIN_OBJECT_ID must identify the signed-in deployment principal")
    group = os.environ["ALERT_ACTION_GROUP_ID"]
    if not group.lower().startswith(f"/subscriptions/{subscription}/resourcegroups/".lower()):
        raise ValueError("ALERT_ACTION_GROUP_ID must be an existing action group in this subscription")
    if "/providers/microsoft.insights/actiongroups/" not in group.lower():
        raise ValueError("ALERT_ACTION_GROUP_ID is not an action-group resource ID")


class RunnerAccess:
    def __init__(self, path, invoke=az):
        self.path = Path(path)
        self.invoke = invoke
        self.entries = json.loads(self.path.read_text()) if self.path.exists() else []

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.entries, indent=2) + "\n")

    def add_database(self, region, address, rule):
        entry = {
            "kind": "database", "group": region["resourceGroup"],
            "name": region["serverName"], "rule": rule,
        }
        self.entries.append(entry)
        self.save()
        self.invoke(
            "postgres", "flexible-server", "firewall-rule", "create",
            "--resource-group", entry["group"], "--name", entry["name"],
            "--rule-name", rule, "--start-ip-address", address, "--end-ip-address", address,
        )

    def add_storage(self, region, address):
        existing = self.invoke(
            "storage", "account", "network-rule", "list",
            "--resource-group", region["resourceGroup"], "--account-name", region["storageName"],
        )
        if any(ipaddress.ip_address(address) in ipaddress.ip_network(rule["ipAddressOrRange"])
               for rule in existing.get("ipRules", [])):
            return
        entry = {
            "kind": "storage", "group": region["resourceGroup"],
            "name": region["storageName"], "address": address,
        }
        self.entries.append(entry)
        self.save()
        self.invoke(
            "storage", "account", "network-rule", "add",
            "--resource-group", entry["group"], "--account-name", entry["name"],
            "--ip-address", address,
        )

    def cleanup(self):
        failures = []
        for entry in list(reversed(self.entries)):
            try:
                if entry["kind"] == "database":
                    self.invoke(
                        "postgres", "flexible-server", "firewall-rule", "delete",
                        "--resource-group", entry["group"], "--name", entry["name"],
                        "--rule-name", entry["rule"], "--yes",
                    )
                else:
                    self.invoke(
                        "storage", "account", "network-rule", "remove",
                        "--resource-group", entry["group"], "--account-name", entry["name"],
                        "--ip-address", entry["address"],
                    )
                self.entries.remove(entry)
                self.save()
            except subprocess.CalledProcessError as error:
                print(f"FAILED to remove temporary {entry['kind']} access: {error.stderr}", file=sys.stderr)
                failures.append(entry)
        if failures:
            raise RuntimeError(f"Access cleanup FAILED; remediate entries in {self.path}")


def bootstrap_database(primary, regions):
    token = az("account", "get-access-token", "--resource-type", "oss-rdbms")["accessToken"]
    certificate = ssl.get_default_verify_paths().cafile
    if not certificate:
        raise RuntimeError("A system CA bundle is required for PostgreSQL TLS verification")
    environment = {
        **os.environ, "PGHOST": primary["databaseHost"], "PGDATABASE": "postgres",
        "PGUSER": os.environ["DATABASE_ADMIN_NAME"], "PGPASSWORD": token,
        "PGSSLMODE": "verify-full", "PGSSLROOTCERT": certificate, "PGCONNECT_TIMEOUT": "10",
    }
    sql = (ROOT / "iac/scripts/bootstrap-database.sql").read_text()
    for region in regions:
        for attempt in range(12):
            result = subprocess.run(
                ["psql", "-X", "-w", "--set", "ON_ERROR_STOP=1",
                 "--set", f"role_name={region['identityName']}",
                 "--set", f"principal_id={region['identityPrincipalId']}",
                 "--set", f"database_name={primary['databaseName']}"],
                input=sql, text=True, env=environment, capture_output=True,
            )
            if result.returncode == 0:
                break
            if attempt == 11:
                print(result.stderr, file=sys.stderr)
                raise RuntimeError("Database identity bootstrap FAILED after bounded retries")
            print("Database bootstrap not ready; retrying", file=sys.stderr)
            time.sleep(10)


def smoke_test(regions):
    token = az("account", "get-access-token", "--resource", os.environ["API_AUDIENCE"])["accessToken"]
    for region in regions:
        for endpoint, expected in (("health", "healthy"), ("ready", "ready")):
            url = f"https://{region['functionHost']}/api/{endpoint}"
            last_failure = ""
            for attempt in range(30):
                request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
                try:
                    with urllib.request.urlopen(request, timeout=15) as response:
                        if response.status == 200 and json.load(response) == {"status": expected}:
                            print(f"PASS: {region['functionName']} /api/{endpoint}")
                            break
                        last_failure = "Unexpected response body"
                except (urllib.error.URLError, TimeoutError) as error:
                    last_failure = f"{type(error).__name__}: {getattr(error, 'code', 'connection failure')}"
                if attempt == 29:
                    raise RuntimeError(f"Smoke test FAILED: {url}: {last_failure}")
                time.sleep(10)
        try:
            urllib.request.urlopen(f"https://{region['functionHost']}/api/health", timeout=15)
        except urllib.error.HTTPError as error:
            if error.code not in (401, 403):
                raise RuntimeError("Unauthenticated API returned an unexpected status") from error
        else:
            raise RuntimeError("Unauthenticated API access was not denied")


def deploy(environment, preview):
    check_configuration()
    STATE.mkdir(exist_ok=True)
    template = STATE / "main.json"
    parameters = STATE / f"{environment}.parameters.json"
    subprocess.run(
        ["az", "bicep", "build", "--file", str(ROOT / "iac/main.bicep"), "--outfile", str(template)],
        check=True,
    )
    subprocess.run(
        ["az", "bicep", "build-params", "--file", str(ROOT / f"iac/environments/{environment}.bicepparam"),
         "--outfile", str(parameters)], check=True,
    )
    arguments = (
        "--location", "westeurope", "--template-file", str(template),
        "--parameters", f"@{parameters}",
    )
    az("deployment", "sub", "validate", *arguments)
    subprocess.run(
        ["az", "deployment", "sub", "what-if", *arguments, "--no-pretty-print", "--only-show-errors"],
        check=True,
    )
    if preview:
        return
    run_id = uuid.uuid4().hex[:12]
    result = az("deployment", "sub", "create", "--name", f"novabank-{environment}-{run_id}", *arguments)
    regions = result["properties"]["outputs"]["regions"]["value"]
    (STATE / f"{environment}.regions.json").write_text(json.dumps(regions, indent=2) + "\n")
    publish = STATE / f"publish-{run_id}"
    subprocess.run(
        ["dotnet", "publish", str(ROOT / "src/NovaBank.Api"), "--configuration", "Release",
         "--output", str(publish)], check=True,
    )
    package = STATE / "api.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in publish.rglob("*"):
            if file.is_file():
                archive.write(file, file.relative_to(publish))
    with urllib.request.urlopen("https://api.ipify.org", timeout=15) as response:
        address = str(ipaddress.IPv4Address(response.read().decode().strip()))
    access = RunnerAccess(STATE / f"access-{environment}-{run_id}.json")
    try:
        access.add_database(regions[0], address, f"gha-{run_id}")
        for region in regions:
            access.add_storage(region, address)
        bootstrap_database(regions[0], regions)
        for region in regions:
            for attempt in range(12):
                try:
                    az(
                        "functionapp", "deployment", "source", "config-zip",
                        "--resource-group", region["resourceGroup"], "--name", region["functionName"],
                        "--src", str(package), "--build-remote", "false",
                    )
                    break
                except subprocess.CalledProcessError as error:
                    if attempt == 11:
                        raise
                    print(f"Package deployment not ready: {error.stderr}", file=sys.stderr)
                    time.sleep(10)
        smoke_test(regions)
    finally:
        deployment_error = sys.exc_info()[1]
        try:
            access.cleanup()
        except RuntimeError:
            if deployment_error is not None:
                detail = (deployment_error.stderr
                          if isinstance(deployment_error, subprocess.CalledProcessError)
                          else str(deployment_error))
                print(f"Deployment also FAILED before cleanup: {detail}", file=sys.stderr)
            raise


def interrupted(signum, frame):
    raise KeyboardInterrupt(f"Deployment interrupted by signal {signum}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment", choices=["dev", "prod"])
    parser.add_argument("--preview", action="store_true", help="Validate and what-if only")
    parser.add_argument("--cleanup", action="store_true", help="Remove recorded temporary access only")
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, interrupted)
    try:
        if args.cleanup:
            for path in STATE.glob(f"access-{args.environment}-*.json"):
                RunnerAccess(path).cleanup()
        else:
            deploy(args.environment, args.preview)
    except subprocess.CalledProcessError as error:
        print(error.stderr or str(error), file=sys.stderr)
        return 1
    except (ValueError, RuntimeError, OSError) as error:
        print(f"FAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
