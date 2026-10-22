---
author: Pinaki Ghatak
last_updated: "2026-10-22"
---

# Monthly cost model

**Indicative totals: dev about USD 35/month; prod about USD 550/month. Overall totals are NOT VERIFIED.** These are transparent planning assumptions, not a quote, invoice, measured workload bill or commitment that the targets have been met.

## Sources and units

Public [Azure Retail Prices API](https://prices.azure.com/api/retail/prices) queried on **2026-10-22**, USD Consumption pricing, West Europe and North Europe. Filter by `serviceName`, `armRegionName` and `priceType eq 'Consumption'`; follow `NextPageLink`. Distinguish exact SKU/hour prices from generic per-vCore prices. Do not multiply the two-vCore SKU price by two again.

Retrieved unit rates:

| Item | Retrieved USD unit price |
|---|---:|
| West Europe PostgreSQL Flexible Server B1MS | 0.0199/hour |
| West Europe PostgreSQL Flexible Server `Standard_D2ds_v5` (2-vCore SKU) | 0.212/hour |
| North Europe PostgreSQL Flexible Server `Standard_D2ds_v5` (2-vCore SKU) | 0.198/hour |
| West Europe PostgreSQL Flex Server storage | 0.1369/GB-month |
| West Europe PostgreSQL Flex backup storage LRS | 0.103/GB-month |
| West Europe Functions Flex always-ready baseline | 0.000004/GB-second |
| West Europe Functions Flex always-ready execution | 0.000016/GB-second |
| West Europe Functions Flex on-demand execution | 0.000026/GB-second |
| West Europe Functions Flex executions | 0.000004 per 10 executions |

References: [Functions pricing](https://azure.microsoft.com/pricing/details/functions/), [PostgreSQL pricing](https://azure.microsoft.com/pricing/details/postgresql/flexible-server/), [Monitor pricing](https://azure.microsoft.com/pricing/details/monitor/), [Private Link pricing](https://azure.microsoft.com/pricing/details/private-link/), [Defender pricing](https://azure.microsoft.com/pricing/details/defender-for-cloud/), and the [Azure calculator](https://azure.microsoft.com/pricing/calculator/).

## Assumptions

- 730 hours/month, 100,000 primary API calls/month, 100 ms average active duration at 0.5 GB per instance. This is an illustrative assumption, not observed usage. Ignore free grants and reservations for a conservative, reproducible baseline.
- Production database HA incurs two West Europe two-vCore server equivalents; the North Europe replica adds a third server. Confirm the actual HA billing model in the calculator.
- Database storage is 32 GB per server equivalent. North Europe and HA storage billing are approximated using the West Europe rate; **NOT VERIFIED**.
- Each database server has one private endpoint: one for dev; two for prod primary and replica. Assume USD 0.01/endpoint-hour; this unit rate was not retrieved in this session and is **NOT VERIFIED**.
- Runtime blob/queue metadata and deployment packages are small. Allocate USD 1/month per regional storage account; **NOT VERIFIED**.
- Allocate USD 6/month per environment's active regional logging baseline (ingestion plus long-term retention), and USD 12/month for prod's two regions. These are explicit allowances, not retrieved meter prices. Actual volumes, 400-day retention, duplicated Activity Logs, table plans and query charges must be calculated; **NOT VERIFIED**.
- Production enables PostgreSQL advanced threat protection; dev explicitly disables it to minimize demo cost. Assume USD 15/protected logical server-month for the primary and replica (USD 30 prod); this list-price assumption was not retrieved and is **NOT VERIFIED**. Confirm the meter and HA treatment in the calculator.
- Allowances for notifications/alerts, excess backup usage and cross-region transfer are listed separately. Database auto-grow, additional metrics/diagnostics, GitHub billed minutes and internet transfer can increase costs. No business traffic is simulated by the probe API.

## Breakdown

| Component | Dev USD/month | Prod USD/month | Basis |
|---|---:|---:|---|
| PostgreSQL compute | 14.53 | 454.06 | Dev: 0.0199 x 730; prod: (2 x 0.212 + 0.198) x 730 |
| PostgreSQL storage | 4.38 | 13.14 | 32 x 0.1369, prod approximates three copies |
| Functions primary always-ready baseline | 0 | 10.51 | Prod: 2 x 0.5 GB x 730 x 3600 x 0.000004 |
| Primary API active execution + requests | 0.17 | 0.12 | Dev: 5,000 GB-s x 0.000026 + 0.04; prod: 5,000 GB-s x 0.000016 + 0.04 |
| Secondary API probes | 0 | 0.01 | Approximate small probe volume |
| PostgreSQL private endpoints | 7.30 | 14.60 | Assumed endpoint-hour rate |
| Functions storage | 1.00 | 2.00 | Assumed small regional storage allowance |
| Logging including retained logs | 6.00 | 12.00 | Assumed allowance; volume/retention not measured |
| Alerts/notifications | 1.00 | 2.00 | Assumed allowance |
| PostgreSQL advanced threat protection | 0 | 30.00 | Assumed USD 15 per protected logical server |
| Excess backup storage | 0 | 3.30 | Assumed 32 GB excess x 0.103, rounded |
| Cross-region/network transfer | 0 | 5.00 | Assumed allowance; workload-dependent |
| **Illustrative subtotal** | **34.38** | **546.84** | **NOT VERIFIED**, rounded budgets approximately 35 / 550 |

The HA/storage/logging/traffic/threat-protection assumptions make the totals unverified even though several unit rates were retrieved. Validate all line items, selected-region rates and actual workload volumes before approving spend.

## Why not simply deploy the smallest production SKU?

Dev has no availability/RPO/RTO target: Burstable PostgreSQL, a single region, scale-to-zero Functions and LRS host storage minimize ongoing demo cost. Prod cannot use Burstable for its required HA/read replica design; the selected General Purpose two-vCore configuration is the starting minimum for that design, subject to actual regional availability. Production Functions retain the smallest supported memory size for this tiny probe workload, adding only zone redundancy and its required two always-ready HTTP instances. Database autoscaling is not enabled; automatic storage growth prevents disk exhaustion but can increase spend.

After measuring memory, API latency, connection counts and replica lag, revise the sizing with evidence rather than assuming this probe workload represents the real customer portal.
