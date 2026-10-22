---
author: Pinaki Ghatak
last_updated: "2026-10-22"
---

# Deploy and demonstrate NovaBank

This is a synthetic infrastructure demo, not a customer-data migration or a production certification. It deploys Azure Functions (.NET 10 isolated), Azure Database for PostgreSQL Flexible Server, and central logging. Dev and prod are independent. Production also has a North Europe read replica and standby API.

Start with the [architecture](../docs/architecture-summary.md), [assumptions and exceptions](../docs/assumptions.md), [cost estimate](../docs/costs.md), and [migration/recovery runbook](../docs/migration-and-recovery.md).

## Prerequisites

- Azure CLI with Bicep (tested with CLI 2.90.0 and Bicep 0.48.1), .NET 10 SDK, Python 3.9+, and PostgreSQL `psql` with a system CA bundle. GitHub-hosted Ubuntu runners supply most tools; workflows install missing Bicep/psql and use `actions/setup-dotnet`.
- An Azure subscription permitting West Europe and North Europe, the selected SKUs, private endpoints, and sufficient Functions regional quota. Register `Microsoft.Web`, `Microsoft.App`, `Microsoft.Storage`, `Microsoft.Network`, `Microsoft.DBforPostgreSQL`, `Microsoft.ManagedIdentity`, `Microsoft.OperationalInsights`, and `Microsoft.Insights` before deployment. Confirm PostgreSQL 17, `Standard_B1ms` and `Standard_D2ds_v5` availability using `az postgres flexible-server list-skus --location westeurope` and the equivalent North Europe command; check Flex region support with `az functionapp list-flexconsumption-locations`. Do not silently substitute another region or weaken production HA if capacity is unavailable.
- Separate GitHub environments named `dev` and `prod`. Protect prod with required reviewers and restrict deployments to your approved branch. Keep ordinary branch protection for pull requests.
- A separate Entra deployment application/service principal per environment with GitHub workload identity federation:
  - issuer: `https://token.actions.githubusercontent.com`
  - audience: `api://AzureADTokenExchange`
  - subject: `repo:<owner>/<repository>:environment:dev` or `...:environment:prod`
  - no client secret, storage key, or publish profile.
- An Entra API application per environment with an Application ID URI (for example `api://<api-client-id>`), v2 access tokens, and an application role assigned to the deployment service principal. The API's App Service Authentication also limits callers to that environment's deployment client ID. An interactive user or a different service principal is intentionally not an allowed demo caller without changing this explicit allowlist. Configure application permissions/admin consent as required by your tenant before running smoke tests.
- An existing Monitor action group in the subscription, with a tested notification route for production replica-lag alerts. An authorized security/platform operator Entra group must be provided for log access.

### Deployment permissions

An administrator must bootstrap permissions; the workflow does not grant itself subscription access or directory permissions.

The subscription-scope entry point creates/updates named resource groups and subscription Activity Log exports. Its principal needs subscription deployment, resource-group write/read, and diagnostic-settings permissions. It also needs resource management and role-assignment permissions in its target groups. A simple **demo-only** setup is subscription Contributor plus Role Based Access Control Administrator on the pre-created target groups:

- dev: `rg-novabank-dev-primary`
- prod: `rg-novabank-prod-primary`, `rg-novabank-prod-recovery`

For tighter privileges, replace subscription Contributor with a reviewed custom role limited to subscription deployment, resource-group, and Activity Log diagnostic-setting operations, plus Contributor on those groups. Never grant subscription Owner or directory-wide read merely for this demo. Existing inherited subscription/resource permissions still apply; this IaC does not revoke them.

The OIDC principal is also the PostgreSQL Entra administrator used for the automated bootstrap. `DATABASE_ADMIN_OBJECT_ID` must equal the object ID (`oid`) of the signed-in service principal, **not** its application/client ID. Database SQL grants are separate from Azure RBAC. The runtime managed identities receive only `CONNECT` on the demo database; they are not database administrators and cannot create business tables. Object-ID-based principal creation avoids directory-wide Graph lookup permissions.

### GitHub environment variables

Configure these as environment **variables**, not committed credentials:

| Variable | Meaning |
|---|---|
| `AZURE_CLIENT_ID` | Environment-specific OIDC application/client ID; also the permitted API caller |
| `AZURE_TENANT_ID` | Entra tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Target subscription |
| `DATABASE_ADMIN_OBJECT_ID` | OIDC service principal object ID |
| `DATABASE_ADMIN_NAME` | Its configured Entra principal/display name, used as PostgreSQL login |
| `API_CLIENT_ID` | Entra API application/client ID |
| `API_AUDIENCE` | Its Application ID URI, e.g. `api://<API_CLIENT_ID>` |
| `LOG_READER_GROUP_ID` | Security/platform operator group object ID |
| `ALERT_ACTION_GROUP_ID` | Existing action group's full ARM ID, required in both environments for one consistent parameter contract; only prod uses it |

Use an authorized subscription-wide security/platform group for log readers: Activity Log exports include subscription-wide management metadata, not just one environment. Do not grant a dev-only application team access to those exports.

## Validate locally (no Azure login)

The following GUIDs are explicitly dummy validation inputs, not usable deployment identities:

```bash
export DATABASE_ADMIN_OBJECT_ID=11111111-1111-1111-1111-111111111111
export DATABASE_ADMIN_NAME=validation-only
export API_CLIENT_ID=22222222-2222-2222-2222-222222222222
export API_AUDIENCE=api://22222222-2222-2222-2222-222222222222
export AZURE_CLIENT_ID=33333333-3333-3333-3333-333333333333
export LOG_READER_GROUP_ID=44444444-4444-4444-4444-444444444444
export ALERT_ACTION_GROUP_ID=/subscriptions/55555555-5555-5555-5555-555555555555/resourceGroups/validation/providers/Microsoft.Insights/actionGroups/validation
bash iac/scripts/validate.sh
bash -n iac/scripts/validate.sh
```

Expected: Bicep entry point and both parameter files compile, infrastructure/cleanup tests pass, and .NET tests pass. PR validation does this without Azure credentials and also runs actionlint. The GUIDs are only for compilation; deployment requires your real environment configuration.

## Run GitHub Actions

1. Push the files through a pull request and inspect **Validate proof of concept**.
2. Open **Actions -> Deploy NovaBank -> Run workflow**.
3. Select `dev` and leave **preview_only** enabled. This performs live validation and shows what-if; it does not create resources.
4. Review the proposed resources, roles, regions, and costs. Run again with **preview_only** disabled to provision, bootstrap database identities, publish the API, and smoke-test it.
5. Repeat for `prod` only after approval. Dev and prod have independent deployment concurrency locks; an in-progress deployment is not cancelled by another run.

The workflow does not run automatically on a push to the default branch. Infrastructure creation is incremental. No deletion or database promotion is automated.

For an equivalent CLI deployment, export the real variables above, sign in as the authorized deployment principal using your approved method, select the subscription, then:

```bash
python3 iac/scripts/deploy.py dev --preview
python3 iac/scripts/deploy.py dev
```

CLI execution must not overlap another deployment to the same environment; GitHub concurrency cannot lock an external terminal.

### What the deployment tests

- `/api/health` returns HTTP 200 and exactly `{"status":"healthy"}` for the permitted caller.
- `/api/ready` returns HTTP 200 and exactly `{"status":"ready"}` after a real authenticated, TLS-verified `SELECT 1`.
- Dependency failures return HTTP 503 and `{"status":"not-ready"}` without database error text or tokens. Host health remains independent of database health.
- Missing authentication returns HTTP 401/403.
- Production tests both primary and recovery APIs. The recovery API reads its local read replica; passing readiness does **not** prove it is writable or that failover meets RPO/RTO.

Output includes `PASS: <function-name> /api/<endpoint>`. Deployment metadata is saved locally under ignored `.deployment/<environment>.regions.json`; it contains resource names, not tokens. Do not print bearer tokens in workflow logs.

### Temporary runner network access

Runtime PostgreSQL traffic follows VNet/private endpoint/private DNS. Public PostgreSQL access is enabled with **no permanent firewall allow rule**, so the hosted deployment runner can temporarily add only its own IPv4 address. Functions storage uses default-deny network ACLs, the Functions subnet's storage service endpoint, and a temporary runner IP rule. Storage shared-key and anonymous blob access are disabled.

The runner obtains its public address from `https://api.ipify.org`; no repository content or Azure credentials are sent there. Firewall changes, identity propagation, deployment and smoke tests have bounded retries. Cleanup runs in Python `finally` and an Actions `always()` step. Each created rule has a local journal:

```bash
python3 iac/scripts/deploy.py dev --cleanup
```

This removes only recorded temporary rules, not an existing storage allowlist entry. Cleanup failures fail the workflow and retain journal entries. If a runner is killed or lost, its local journal may be lost too: inspect **all** `gha-...` PostgreSQL rules and storage IP ACLs against the approved baseline, remove stale run-specific entries, and record the remediation. These rules do not have server-enforced expiry.

Storage IP rules may not permit traffic from an Azure runner in the **same region** as the account. If this occurs, fail rather than opening broad access; use a properly connected private runner (or a separately approved runner location). Hosted-runner network access is a demo exception, not a production recommendation.

## Local API development

Install Functions Core Tools v4 and Azurite separately if local hosting is needed. Copy `src/NovaBank.Api/local.settings.example.json` to ignored `local.settings.json`, replace its non-secret database settings, start Azurite, and use `az login` as a database-authorized developer identity. Local development requires deliberately approved database connectivity. Do not permanently open the database firewall for convenience.

```bash
cd src/NovaBank.Api
func start
```

Local Core Tools does not emulate App Service Authentication: its anonymous HTTP triggers are appropriate only for loopback development. Azure ingress enforces Entra authentication through IaC. .NET tests can run without Core Tools, Azurite, Azure access, or a database.

## Verification status

The repeat validation found and fixed empty Bash `then` blocks in both GitHub
workflows. Regression tests now check every current workflow `run` step with
`bash -n`, in addition to actionlint. The deployment orchestrator is exercised
with synthetic Azure CLI/HTTP responses for dev, both production regions,
preview-only behavior, SQL/bootstrap failure, bounded package retries, and
network-rule cleanup success/failure. These are mocked orchestration tests,
not evidence that Azure accepted a deployment.

Repeat local results:

| Check | Result |
|---|---|
| All six local Bicep entry points and both environment parameter files | PASS |
| Python infrastructure, workflow-shell and deployment-orchestration tests | 17 passed |
| Clean .NET rebuild and unit tests | 8 passed |
| Functions publish and generated `health`/`ready` route metadata | PASS; no local settings in package |
| Actionlint and validation-script shell syntax | PASS |
| Actual local Functions host with isolated Azurite | Health 200; unavailable dependency readiness 503; health still 200 afterward |
| Checkov 3.3.30, JSON summary | 0 resources scanned; INCOMPLETE coverage |
| Live Azure provisioning, OIDC, successful database connection and recovery drill | NOT VERIFIED |

The local HTTP run used synthetic configuration, loopback services and disabled
real Azure credential sources. It does not emulate Entra ingress authentication
or the Azure PostgreSQL identity extension. Its Functions/Azurite processes were
stopped after the check.

Local validation is distinct from a live deployment. No Azure deployment, online migration, recovery drill, or GitHub workflow execution was performed during implementation. Live resource provisioning, token issuance/SQL grants, data-plane connectivity, log ingestion/retention and recovery objectives remain **NOT VERIFIED** until the documented commands run in the target subscription.

Checkov 3.3.30 was run on the compiled ARM template with network downloads disabled. It reported **zero scanned resources** for the generated symbolic/nested template; that is a coverage failure, not a clean security result. Bicep compilation, explicit configuration tests and manual configuration checks provide local evidence, but do not replace a supported scanner or live security validation.
