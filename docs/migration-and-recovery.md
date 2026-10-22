---
author: Pinaki Ghatak
last_updated: "2026-10-22"
---

# PostgreSQL migration and recovery runbook

**Status: NOT VERIFIED.** This is an operational design and acceptance checklist. No on-premises database was contacted, migrated or synchronized, and no failover or restore was executed.

## Migrate the existing on-premises PostgreSQL

Use the [Azure Database for PostgreSQL migration service](https://learn.microsoft.com/azure/postgresql/migrate/migration-service/concepts-migration-service-postgresql) with an **online** migration, after verifying supported source/target versions, extensions, roles, networking and migration-service limitations. The target is the primary Azure PostgreSQL Flexible Server, not its read-only replica.

1. Inventory source version, database size, peak WAL/write rate, extensions, large objects, encodings, users, ownership and incompatible features. Do not assume a schema or source connectivity not supplied by NovaBank.
2. Approve EU-only staging/transfer paths and private source connectivity. Test using synthetic or explicitly authorized sanitized data, never customer data in GitHub Actions.
3. Configure migration prerequisites, including logical replication/WAL settings, a minimally privileged migration identity and temporary approved network access. Do not store source credentials in Git or normal workflow variables.
4. Rehearse initial load plus continuous change capture against a representative data set. Validate row counts/checksums, sequences, roles, extensions and application reads/writes. The current probe API intentionally has no business schema or writes.
5. Monitor **source-to-primary** replication lag separately from **Azure-primary-to-EU-replica** lag. The Azure read replica does not migrate the on-premises database. Alarm below the one-hour budget and pause cutover if the lag/replay position or validation is unacceptable.
6. At approved cutover, stop source writes, wait for confirmed catch-up, validate the last committed transaction, finalize migration, change the application's target, and run business acceptance checks. Prevent dual writers. Retain the source read-only for an approved rollback period.
7. Record actual source/target transaction markers, replication delay, downtime, failures, reconciliation and rollback decisions. Recheck the Azure replica after migration; a large initial load can increase replica lag.

The production one-hour RPO is an acceptance objective for both migration/cutover and steady-state recovery, not a promise supplied by this document. Online migration plus monitored catch-up can support it only when observed lag and transaction evidence remain within that budget.

## Steady-state recovery mechanisms

| Failure | Mechanism | Evidence required |
|---|---|---|
| Primary zone loss | Prod PostgreSQL zone-redundant HA and zone-resilient primary Functions | Actual supported service SLAs, availability/load observations and rehearsed failover behavior |
| Accidental data loss | PostgreSQL point-in-time restore, prod backup retention 35 days | Restore to a separate server, verify data and identities, measure recovery and reconnection |
| Primary region unavailable | North Europe PostgreSQL async replica plus pre-provisioned standby API | Lag history, promotion, writable-data validation, authenticated API readiness and client switch |
| Logging region unavailable | Independent North Europe workspace and DR resource logs | Query permissions, actual log ingestion and retention; primary workspace history is not replicated |

Backups are region-local, not an unvalidated geo-redundant backup. The EU read replica provides a regional database copy but **does not protect against logical deletions** already replicated. PostgreSQL backups and logs have distinct retention purposes.

## Replica monitoring

The prod replica has a Monitor alert on `physical_replication_delay_in_seconds`, maximum over five minutes, evaluated every minute, threshold greater than **900 seconds**. The existing action group must route it to an accountable database/platform operator.

On an alert, check source workload, replica replay, capacity, connectivity and service health. Treat missing metric data as unknown, not zero lag. A five-minute evaluation window and async replication leave operational response time but cannot guarantee RPO <=3,600 seconds; prolonged lag or a region failure can breach the target. Record and escalate breaches rather than claiming compliance.

Official reference: [PostgreSQL replication metrics](https://learn.microsoft.com/azure/azure-monitor/reference/supported-metrics/microsoft-dbforpostgresql-flexibleservers-metrics).

## Manual regional recovery

Only execute with incident commander and database-owner approval. Promotion changes the replication topology; **do not** use it as an ordinary deployment step.

1. Record incident start, last successful transaction marker and the replica's last replay position/observed lag. If the primary is unreachable, document the uncertainty and possible data loss. Freeze primary writes or otherwise fence the primary before accepting writes elsewhere.
2. Confirm North Europe health, the standby app's published package, private DNS, database identity configuration, Entra token issuance, monitoring and required operator access.
3. Follow the current [read-replica promotion procedure](https://learn.microsoft.com/azure/postgresql/read-replica/concepts-read-replicas-promote) for the selected topology. Choose planned versus forced promotion explicitly; forced promotion accepts potential data loss. Do not guess CLI promotion flags or automatically force a promotion.
4. Verify that the recovered database is writable. `SELECT 1` and `/api/ready` are insufficient: use an approved recovery-validation transaction on the real application's authorized schema. This demo grants only `CONNECT` and intentionally cannot perform business writes.
5. The standby API already uses the replica's regional FQDN and its own managed identity. Verify whether the chosen promotion mode retains that endpoint. If it changes, update `Database__Host` deliberately; verify its Entra administrator/runtime principal and TLS connectivity. Do not fall back to passwords or grant the runtime identity administrator rights.
6. Obtain an audience-correct Entra token and verify `/api/health`, `/api/ready`, logging, and then business acceptance checks. Route clients to the secondary Function hostname through your approved manual endpoint configuration. There is no automatic global front door or DNS failover in this starter.
7. Record recovery completion and compute measured RTO from incident start to accepted service restoration. Compute RPO from known committed versus recovered transaction positions/timestamps; report unknowns. Accept only if demonstrated RPO <=1 hour and RTO <=4 hours.
8. Keep the original primary fenced. Reconcile missing transactions, rebuild replication/HA as required, and plan failback as another approved change. Never automatically let two servers accept independent writes.

After promotion, **do not blindly rerun the original prod IaC**: it still describes the original primary/replica relationship. Reconcile the desired state with the recovered topology before any deployment, to avoid reversing the recovery or attempting an invalid replica update. Restore zone redundancy and sufficient compute/always-ready capacity on the new primary application/database as part of the approved recovered-state design.

## Acceptance record to complete after a drill

- Environment, exact deployment/version, primary and recovery EU regions.
- Operator approvals and incident/change reference.
- Last committed/recovered transaction markers, maximum replica lag and any uncertain period.
- Promotion/restore start and finish; authenticated application restoration and client switch.
- Actual RPO/RTO; target met, breached or unknown with supporting evidence.
- Log-ingestion and retained-log queries, alerts received, identity/permission validation.
- Split-brain prevention, reconciliation and IaC/topology update before normal deployments resume.

Until this record is populated, the recovery targets remain **NOT VERIFIED**.
