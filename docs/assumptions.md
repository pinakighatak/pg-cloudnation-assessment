---
author: Pinaki Ghatak
last_updated: "2026-10-22"
---

# Assumptions, boundaries and risks

## Confirmed scope

- Azure, Bicep and Azure Verified Modules; separate Functions and PostgreSQL IaC folders.
- Dev and prod, .NET isolated API, health plus `SELECT 1` readiness only.
- Manual OIDC deployment from standard GitHub-hosted runners, PR validation without credentials.
- West Europe primary, North Europe production replica and standby API; all regional workload data, backups, packages and logs stay in this EU pair.
- Document an online on-premises migration approach; do not access or migrate real data.
- No AI helper, business tables, customer CRUD, slides, automatic failover or global routing service in this change.

## Implementation assumptions

1. The target subscription supports the chosen Functions plan, PostgreSQL version/SKUs, zones and quotas in both regions. Live capability checks must pass; no substitution into non-EU regions is allowed.
2. A separate OIDC principal and Entra API application exist per environment. Administrator-approved API permissions, federation, database-admin principal details, log-reader group and action group are prerequisites.
3. The database administrator is the signed-in workflow service principal. Runtime identities are separate and only granted database `CONNECT`. No customer schema or permission model is implied.
4. The initial 512-MB Functions instance, concurrency 4 and pool size 5 are a low-cost starting point for two probe endpoints, not measured capacity for the real portal. The maximum of 40 on-demand instances plus two primary-prod always-ready instances can create many connections. Benchmark and cap concurrency against actual database limits before adding queries or traffic.
5. Each environment/region has independent resources and identities. Fixed private address ranges are not peered; address planning must be revisited before joining a real enterprise network.
6. The authorized log-reader group is allowed to view subscription-wide management metadata. The application identities do not get log-reader roles; existing inherited administrators remain able to access logs.
7. Workspace retention is 400 days. Application Insights uses the workspace's effective retention; its legacy component retention setting is not the audit-retention authority. Verify actual table retention and live ingestion before declaring compliance.
8. The platform team's existing action group is reachable and owned. Database operators respond to replica-lag alerts. A 15-minute lag alert is not proof of an RPO guarantee, and missing telemetry needs an operational response.
9. Production targets apply to a validated system, not simply to successfully created resources. No measured availability, RPO, RTO, migration or restore result exists yet.
10. The security/platform team owns deployment approval, stale firewall audits, Entra consent, log access reviews and incident response. The database team owns migration, cutover and database recovery. Application owners own endpoint switching and acceptance.

## Explicit demo exceptions

- API ingress is public HTTPS but requires tenant-issued Entra tokens and the configured caller client ID. Public ingress is not anonymous access.
- PostgreSQL uses private endpoints for runtime traffic but permits a temporary runner-specific IPv4 firewall rule for setup. No permanent `0.0.0.0` Azure-services rule is created.
- Storage retains a public endpoint with default-deny ACLs, approved runtime subnet service endpoints, and temporary runner IP access. Anonymous blobs, shared-key authentication and cross-tenant replication are disabled.
- Monitoring ingestion/query endpoints are public, with Entra-only local-auth disabling and restricted RBAC. Private Monitor access is deferred rather than falsely claimed.
- GitHub-hosted runners and GitHub control-plane data are not regional workload storage; they handle code, deployment metadata and synthetic probe responses only. Never send customer data, production logs or database extracts through them. EU workload residency does not establish that all identity, GitHub or Azure control-plane processing is EU-only; legal/compliance review remains required.
- Python cleanup and an Actions `always()` step remove only run-owned access entries. Hard termination can leave stale rules because Azure IP rules have no TTL. Audit and manual remediation are required after interrupted runs.
- CLI-created deployments are not protected by GitHub's concurrency lock. Do not overlap them with another deployment in the same environment.
- The deployment principal's database-admin and role-assignment privileges are intentionally powerful for bootstrap. Separate infrastructure/bootstrap/runtime duties and use private runners before production adoption.
- Checkov's ARM parser did not scan the generated nested/symbolic resources. Zero findings from zero resources are not a successful security scan.

## AVM choices

Pinned published versions are declared in the Bicep source. PostgreSQL uses AVM `0.13.2` because it uses stable `2024-08-01` ARM schemas and supports Entra-only authentication, private endpoints and read replicas; newer examined releases use preview APIs. Subscription resource groups, Activity Log diagnostic extensions and the specific replica-lag metric alert are direct Bicep resources; workload services use AVM. AVM output schemas may expose unused key-related outputs: protect Azure deployment-history permissions even though this application never consumes those keys.

## Residency rejection rule

Reject a design or parameter change that introduces non-EU data stores, backups, replicas, runtime package storage or log stores; record it as a residency risk rather than deploying it. The starter's root parameters allow only West Europe for primary and North Europe for recovery, which also prevents equal primary/recovery regions. Azure's globally scoped DNS, identity and alert management metadata do not relocate regional workload storage.
