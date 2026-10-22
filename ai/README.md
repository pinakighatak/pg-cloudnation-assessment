---
author: Pinaki Ghatak
last_updated: "2026-10-22"
---

# NovaBank: learned implementation plan and delivery review

Recorded on 2026-10-22 after implementation and repeat validation.

This document preserves the approved plan, the decisions refined during delivery,
how AI-assisted work was checked, and what still requires evidence. It is a
delivery record, not a second architecture summary or a production-readiness
certificate. The canonical design is the
[architecture summary](../docs/architecture-summary.md); operational commands and
prerequisites are in the [demo guide](../demo/README.md).

**Status:** implementation artifacts exist and local checks pass. Live Azure
deployment, GitHub workflow execution, successful Azure PostgreSQL connectivity,
log ingestion, migration and recovery targets remain **NOT VERIFIED**.

## 1. Problem and agreed approach

NovaBank's starting point is an on-premises API VM, PostgreSQL, local-file logs and
no meaningful environment separation. The first cloud step must demonstrate a
small, repeatable Azure deployment without pretending to be the finished portal.

Use Bicep wrappers around pinned Azure Verified Modules (AVM), with separate
Functions and PostgreSQL folders, shared networking and monitoring, and independent
dev/prod configuration. Include a minimal .NET isolated API and a GitHub Actions
workflow that validates pull requests and deploys a selected environment manually
through Azure OIDC.

### Confirmed scope

- .NET 10 isolated Azure Functions with `GET /api/health` and `GET /api/ready`.
  Readiness executes `SELECT 1`; no business CRUD, customer records or application
  tables are included.
- Azure Database for PostgreSQL Flexible Server, using managed-identity
  authentication rather than passwords.
- West Europe primary region, North Europe production recovery region.
  All regional workload stores, backups, replicas, deployment packages and log
  stores must stay in this EU pair.
- Dev uses a low-cost, single-region configuration with no availability, RPO or
  RTO target. Production is designed toward availability >=99.9%, RPO <=1 hour
  and RTO <=4 hours; these are acceptance targets, not measured results.
- Production has a zone-redundant primary database, zone-resilient primary API,
  a second-region read replica and a small standby Function app with its regional
  identity, storage, network and logging dependencies.
- Use standard GitHub-hosted runners with documented, narrowly scoped network
  exceptions rather than requiring a private runner for this demo.
- Entra-authenticated API ingress and managed identities for runtime access.
  Tenant application registrations, OIDC federation, administrator permissions,
  log-reader groups and alert routing are setup prerequisites, not silently
  created tenant configuration.
- Document online on-premises PostgreSQL migration and cutover, without
  contacting or transferring real customer data.
- Include deployment, assumptions, costs, migration, recovery and demo
  documentation. No automatic failover, global traffic-routing service, slides
  or separately deployed AI helper was requested in this implementation scope.
- Implementation approval did not authorize deployment to Azure. No Azure
  resources were created or changed during this work.

No time budget was supplied. Scope decisions were based on the agreed demo,
not an invented deadline. Author effort was not reliably measured; see the
[work log](../docs/timelog.md) rather than inferring effort from command runtimes.

## 2. Complete implementation work plan

The original plan contained eight workstreams. The table records their intended
outcomes and the evidence boundary after implementation.

| ID | Workstream and required outcome | Current evidence |
|---|---|---|
| 1 | Verify published AVM versions, parameter/output contracts, stable API options, .NET support, identity-based deployment, networking, zones and replica constraints before authoring. | Published module metadata/source and Microsoft documentation were consulted; pinned modules restore and compile. Live regional capacity remains unverified. |
| 2 | Implement subscription orchestration, resource groups, deterministic names/tags, EU-only environment parameters, identities, VNet/subnets, DNS, Functions storage and restricted central monitoring with at least 12 months of retention. Disable storage shared-key access. | Bicep and configuration tests pass; actual provisioning, access and retention behavior remain unverified. |
| 3 | Implement Entra-only PostgreSQL and the demo database, private runtime access, environment-specific sizing/backups, prod zone HA, compatible second-region replica and actionable lag monitoring. | Modules compile and configuration contracts are tested; server creation, replication and alert delivery remain unverified. |
| 4 | Implement primary/standby Functions and health/readiness API, Entra ingress, managed identities, identity-based package/host storage, bounded scaling, token refresh, TLS verification, timeouts and sanitized failures. | Clean build, unit tests, publish metadata and real local health/dependency-failure HTTP checks pass. Azure ingress and successful database readiness remain unverified. |
| 5 | Implement idempotent database principal bootstrap and least-privilege SQL grants, incremental deployment, temporary runner-only access, bounded retries and explicit cleanup failures. Keep runtime identities separate from the database administrator. | Orchestration and cleanup success/failure tests pass with synthetic external responses. Real Azure SQL extension behavior and network propagation remain unverified. |
| 6 | Implement credential-free PR validation and manual environment-selected OIDC deployment, environment protection prerequisites, per-environment concurrency, what-if, API publishing and authenticated primary/secondary smoke tests. | Workflow and inline shell syntax pass; orchestration is exercised locally with mocks. No GitHub Actions run or live OIDC deployment was executed. |
| 7 | Document setup, roles, variables, commands, expected responses, costs, assumptions, management summary, migration, promotion, endpoint switching, split-brain prevention and post-failover reconciliation. Preserve unrelated user files. | Documentation exists and explicitly distinguishes assumptions and unverified objectives from observed results. |
| 8 | Validate all local Bicep entry points/parameters, .NET restore/build/tests/publish, workflow/shell syntax, environment/residency/retention contracts, readiness and cleanup failures. Run a scanner and inspect its coverage, not just its exit code. | 17 Python tests and 8 .NET tests pass; local runtime checks pass. Checkov scans zero resources, so scanner coverage and live end-to-end acceptance remain incomplete. |

### Dependencies and execution order

1. Workstream 1 precedes shared infrastructure (2).
2. Shared infrastructure (2) precedes PostgreSQL (3) and Functions/API (4).
   Functions database settings must match PostgreSQL outputs.
3. PostgreSQL (3) and Functions/API (4) precede deployment/bootstrap logic (5).
4. Deployment logic (5) precedes workflow wiring (6).
5. Documentation (7) records actual PostgreSQL, API and workflow behavior
   from workstreams 3, 4 and 6.
6. Final validation (8) follows workflow/documentation completion and is repeated
   after any defects are corrected.

These dependencies avoid designing workflow commands against imagined outputs or
writing acceptance claims before tests exist.

## 3. Resulting repository structure

```text
.github/workflows/
  validate.yml
  deploy.yml
ai/
  README.md
demo/
  README.md
docs/
  architecture-summary.md
  assumptions.md
  costs.md
  migration-and-recovery.md
  timelog.md
iac/
  main.bicep
  regional.bicep
  bicepconfig.json
  environments/
    dev.bicepparam
    prod.bicepparam
  functions/main.bicep
  postgresql/main.bicep
  networking/main.bicep
  monitoring/main.bicep
  scripts/
    validate.sh
    deploy.py
    bootstrap-database.sql
src/NovaBank.Api/
tests/
  NovaBank.Api.Tests/
  infrastructure/test_deployment.py
global.json
```

### Refinements from the initial layout

- A regional wrapper connects identity, monitoring, networking, PostgreSQL and
  Functions consistently in each region.
- The initial plan suggested separate deployment/bootstrap/smoke-test shell
  scripts. A single Python orchestrator now owns those stages, retries and
  cleanup, with a separate SQL bootstrap file. This follows the plan's allowance
  to consolidate scripts where simpler; it is not missing deployment scope.
- The EU allowlists were narrowed to West Europe for primary and North Europe
  for recovery. This also prevents selecting the same region twice without
  requiring experimental Bicep assertions.
- Functions instance memory was refined to 512 MB and HTTP concurrency to 4 for
  this deliberately tiny probe workload. These settings are starting assumptions,
  not measured capacity for the original customer portal.

## 4. Technical decisions captured during delivery

### Infrastructure and module contracts

Use the declared, pinned AVM versions rather than floating tags:

| Service | AVM resource module | Version |
|---|---|---|
| Function App | `avm/res/web/site` | `0.24.0` |
| Functions hosting plan | `avm/res/web/serverfarm` | `0.7.0` |
| PostgreSQL Flexible Server | `avm/res/db-for-postgre-sql/flexible-server` | `0.13.2` |
| Storage | `avm/res/storage/storage-account` | `0.33.1` |
| Virtual network | `avm/res/network/virtual-network` | `0.10.2` |
| Private DNS | `avm/res/network/private-dns-zone` | `0.8.1` |
| User-assigned identity | `avm/res/managed-identity/user-assigned-identity` | `0.6.0` |
| Log Analytics | `avm/res/operational-insights/workspace` | `0.16.1` |
| Application Insights | `avm/res/insights/component` | `0.8.0` |

PostgreSQL AVM `0.13.2` was chosen for its stable `2024-08-01` ARM API and needed
features; newer examined versions used preview APIs. Private endpoints are
configured through the server module. Resource groups, subscription Activity Log
diagnostic extensions and the explicit replica-lag alert use direct Bicep
resources. Do not assume all resource types or parameters have the same AVM
interface.

### Environment-specific configuration

| Area | Dev | Primary prod | Production recovery |
|---|---|---|---|
| Region | West Europe | West Europe | North Europe |
| PostgreSQL | `Standard_B1ms`, Burstable | `Standard_D2ds_v5`, General Purpose, zone HA | Matching General Purpose async read replica |
| Database backup retention | 7 days | 35-day setting | Replica backup behavior requires live service validation |
| Functions | Flex, scale to zero | Flex, zone redundancy, two always-ready HTTP instances | Flex standby, scale to zero |
| Instance memory/concurrency | 512 MB / 4 | 512 MB / 4 | 512 MB / 4 |
| Maximum on-demand instances | 40 | 40, in addition to always-ready capacity | 40 |
| Functions storage | LRS | ZRS | LRS |
| Central workspace retention | 400 days | 400 days | 400 days |

Database automatic storage growth is enabled; database compute autoscaling is
not. Connection pools are bounded at 5 per application process, but total
connections at maximum API scale still need workload testing.

The [cost model](../docs/costs.md) combines retrieved retail unit rates with stated
assumptions. Approximate monthly budgets are USD 35 dev and USD 550 prod;
**overall totals are NOT VERIFIED**. Region/SKU availability, HA billing,
retention volume, backup usage, traffic and threat-protection charges require
target-subscription validation.

### Identity, networking and logging

- Runtime PostgreSQL connections use the local VNet/private endpoint/private DNS,
  Entra token refresh and full TLS verification.
- SQL bootstrap uses the authorized deployment principal as Entra administrator.
  Runtime identities get database `CONNECT`, not administrator rights. SQL grants
  and Azure RBAC are different authorization layers.
- Functions storage disables shared-key and anonymous access and uses
  default-deny network ACLs with an approved runtime subnet service endpoint.
- Hosted runners temporarily add their own single IPv4 address for database
  bootstrap/storage access. The orchestrator journals run-owned rules and removes
  them in `finally`; the workflow also invokes cleanup with `always()`.
- Public API ingress requires the configured Entra audience and allowed caller.
  Anonymous Function trigger declarations do not bypass Azure's front-end
  authentication; local Core Tools does not emulate that front end.
- Log Analytics uses 400-day retention and explicit security/platform group
  access. Existing inherited administration is not removed.
- Activity Log exports include subscription-wide management metadata. Reader
  groups must be authorized for that scope; duplicated exports also affect cost.

These are demo trade-offs, not a private-only production design. Hard runner
termination can leave stale IP rules, which have no server-enforced expiry.
Same-region Azure runner/storage networking can also require a private runner.
Monitoring public endpoints, inherited permissions, GitHub processing and Azure
control-plane metadata need their own compliance review; EU workload placement
does not prove every supporting platform processes data only in the EU.

### Migration and recovery

- On-premises migration is a documented online migration/change-capture and
  cutover approach, not an executed transfer.
- Monitor source-to-primary migration lag separately from Azure
  primary-to-replica lag.
- The replica alert uses `physical_replication_delay_in_seconds`, a maximum over
  five minutes, evaluated every minute, with a threshold above 900 seconds.
- Async replication can lag beyond one hour. The alert provides response
  headroom but cannot guarantee RPO.
- Regional recovery requires fencing the old writer, approving promotion,
  verifying writable data and identities, restoring application access, and
  switching clients manually. `SELECT 1` does not prove write readiness.
- After promotion, reconcile IaC with the recovered topology before normal
  deployments resume. Blindly redeploying the original primary/replica layout
  can conflict with the incident recovery.

The detailed procedure and acceptance evidence are in the
[migration and recovery runbook](../docs/migration-and-recovery.md).

## 5. Review: how this was achieved

### Requirements before code

The assistant asked the user to resolve choices that materially changed the
implementation: infrastructure-only versus an API, dev/prod scope, runtime,
workflow triggers, public/private deployment access, regional recovery, endpoint
behavior and whether real data migration was required.

The user selected .NET isolated, a small health/readiness API, manually triggered
OIDC deployment, standard hosted runners with explicit exceptions, a second EU
region/read replica, and migration documentation rather than real migration.
This prevented hidden assumptions about private runners, business functionality
or authority to modify Azure.

### Research, implementation and feedback

1. Inspected the initially small repository and its assessment-specific skill.
2. Saved an approval-gated implementation plan and tracked its dependencies.
3. Looked up published module versions, inspected actual AVM parameter/output
   contracts, and consulted Microsoft documentation instead of guessing inputs.
4. Built small module wrappers, wired their outputs into the regional/root
   deployment, and added the API and explicit environment configuration.
5. Implemented the deployment stages and wired them into PR/manual workflows.
6. Used compiler output, focused tests and publish artifacts to refine the code.
7. Repeated validation more broadly when the user requested start-to-end testing.
   That uncovered a workflow defect missed by the first validation pass.

### Defects and gaps found, and the response

| Observation | Response and lesson |
|---|---|
| AVM diagnostics used an incorrect property spelling. | Switched to the actual `logCategoriesAndGroups` contract and recompiled. Typed compilation matters even when examples look plausible. |
| The proposed Bicep assertion required an experimental feature. | Used explicit, disjoint primary/recovery region allowlists instead. Prefer stable, simpler constraints. |
| An unused module parameter caused the configured linter to fail. | Removed the unused parameter rather than weakening the rule. |
| Compiled ARM traversal encountered expression-valued properties and existing-resource references. | Adjusted the contract-test traversal to match the actual generated representation. Test the compiler's output shape, not an assumed list of ordinary resources. |
| Both workflows contained an empty Bash `then` block. Actionlint passed without ShellCheck. | Fixed the blocks and added `bash -n` checks for each current inline `run` step. Valid YAML/action expressions do not imply valid embedded shell. |
| Initial tests did not exercise the complete deployment orchestration. | Added preview/dev/prod, bootstrap failure, package retry and cleanup failure scenarios with synthetic external responses. Mocks expand control-flow coverage but do not prove cloud compatibility. |
| Checkov exited successfully while scanning no resources. | Inspected the JSON summary and recorded incomplete coverage. Neither a zero exit code nor the number of ARM entries is a scanner coverage count. |
| Local runtime tools were missing; Docker had no running daemon. | Installed isolated Core Tools/Azurite for a bounded local HTTP test, recovered an unextracted Core Tools archive, and stopped the exact owned processes afterward. No shared daemon was started. |

No unresolved finding was converted into an unsupported success claim. In
particular, successful compilation was not treated as an Azure deployment, and
mocked or dependency-failure tests were not treated as proof of successful
database authentication.

### AI's role and its limits

AI assisted with requirement clarification, service/module research, code and
documentation generation, interpreting diagnostics, and designing regression
tests. Public official references, local source inspection and executed tools
were used to check its output.

The tests used dummy GUIDs, synthetic token claims and local emulator
configuration. No customer database, customer records or production logs were
accessed for this work. Tokens and live credentials are not included in this
record.

This retrospective is **not** evidence of a deployed EU-hosted AI helper.
No dedicated helper endpoint, its residency, or its data handling was validated.
That assessment component remains outside the agreed implementation and
**NOT VERIFIED**. Before adding one, select an EU endpoint, document the exact
synthetic or named-reviewer-approved sanitized inputs, and review its output
without replacing ordinary tests or human approval.

## 6. Observed verification results

The repeat validation produced the following evidence:

| Check | Observed result | What it does not establish |
|---|---|---|
| All six local Bicep entry points | Compiled successfully | Azure policy, quota, regional availability or deployment acceptance |
| Dev/prod parameter files | Compiled with dummy environment inputs | Correctness of real identity/application configuration |
| Python tests | 17 passed | Live Azure service behavior |
| Clean .NET rebuild/unit tests | 8 passed | Successful real PostgreSQL token authentication |
| Functions publishing | Successful; `health`/`ready` metadata present; local settings absent | Cloud package activation |
| Actionlint and inline Bash syntax | Passed after fixes | Successful hosted workflow execution |
| Actual local Functions/Azurite HTTP run | Health 200, unavailable dependency readiness 503, health still 200 afterward | Entra ingress enforcement, a successful database query, HA or failover |
| Checkov 3.3.30 JSON summary | `passed=0`, `failed=0`, `resource_count=0` | Any meaningful clean security-scan result |
| Azure/GitHub deployment and recovery | Not executed | Availability, RPO/RTO, log compliance or production readiness |

The local HTTP run used loopback services and disabled real Azure credential
sources. Functions and Azurite were stopped and temporary test data/logs removed.
This was a real local host test, separate from the mocked deployment tests.

### Reproducing the local checks

Use the dummy-variable setup in the [demo guide](../demo/README.md), then:

```bash
bash iac/scripts/validate.sh
dotnet clean tests/NovaBank.Api.Tests/NovaBank.Api.Tests.csproj --configuration Release
dotnet test tests/NovaBank.Api.Tests/NovaBank.Api.Tests.csproj --configuration Release
dotnet publish src/NovaBank.Api --configuration Release --output .deployment/verification-publish
bash -n iac/scripts/validate.sh
actionlint
checkov -f .deployment/main.json --framework arm --quiet --skip-download --output json
```

Actionlint and Checkov must be installed or invoked by their actual installation
paths; they are not guaranteed to be on a developer's PATH. The local HTTP test
also needs Functions Core Tools v4 and Azurite. It was an isolated verification
exercise, not an additional committed automated integration-test runner.

The scanner command above documents the known coverage gap; it is not an
acceptance gate that currently proves scanning completeness.

## 7. Remaining acceptance work

1. Configure the environment-specific OIDC identities, API registrations and
   consent, deployment/RBAC permissions, database administrator, authorized
   log-reader group and tested action group.
2. Verify provider registrations, service/SKU availability, zones, quotas, policy
   and current pricing in the selected subscription and EU regions.
3. Obtain explicit deployment approval and run the workflow's preview-only path.
   Review what-if, resource scopes, roles, residency and cost before provisioning.
4. Deploy dev, verify real identity bootstrap and a successful authenticated
   readiness query, and check that unauthenticated ingress is rejected.
5. Verify network-rule cleanup, journals, actual diagnostics ingestion, table
   retention, log-reader authorization and stale-rule remediation.
6. Deploy prod after approval; validate both regions, replication and alert
   routing, then load-test memory, latency, database connection limits and lag.
7. Rehearse an approved online migration and a recovery drill with transaction
   markers, write validation, split-brain prevention and measured client switching.
   Record actual RPO/RTO, including any uncertainty or target breach.
8. Close the zero-resource scanner coverage gap with a supported validation path
   before treating the infrastructure as security-validated.
9. Replace demo networking/bootstrap privilege compromises for production,
   reconcile recovered-state IaC, and separately address the assessment's AI
   helper and presentation scope.

**Final review:** the work delivered a locally validated implementation and a
repeatable deployment path, with a stronger regression suite after retesting.
It did not deliver evidence of a successful Azure deployment or proven production
recovery objectives. That distinction is the main lesson to preserve when
continuing the plan.
