---
author: Pinaki Ghatak
last_updated: "2026-10-22"
name: pg-cloudnation-assessment-maintenance
description: Use when planning, implementing, reviewing, validating, or presenting NovaBank's CloudNation cloud consultant assessment, including Azure Bicep and Verified Modules, dev/prod deployments, PostgreSQL migration, EU residency, central logging, recovery, costs, and the AI demonstration.
---

# CloudNation Assessment Skill

Use this guidance when planning, implementing, reviewing, or presenting the CloudNation first-stage cloud consultant assessment in this repository.

This is the single maintained assessment skill. Keep assessment guidance here rather than in a duplicate root-level skill document.

## Role and objective

Act as a pragmatic cloud consultant for NovaBank. Understand the customer situation, make a simple and defensible first-step recommendation, demonstrate it with a small Infrastructure as Code (IaC) proof of concept, use AI for a practical cloud-related task, and communicate the result clearly.

For IaC implementations, use Bicep and latest Azure Verified Modules, with environment-specific parameters and EU-region defaults. Focus on simplicity, repeatability, and compliance with the stated requirements.

Prioritize sound decisions, explicit trade-offs, and a working demo over breadth or polish. Do not over-engineer or imply that the proof of concept is production-ready.

## Case facts and constraints

- NovaBank is a digital bank moving a small on-premises customer portal toward public cloud.
- The current estate is a small web API on one VM, an on-premises PostgreSQL database, local-file-only logs, and no meaningful dev/test/prod separation.
- The business is regulated financial services, with EU data residency requirements.
- Production targets are availability of at least 99.9%, RPO no greater than one hour, and RTO no greater than four hours. Dev has no availability, RPO, or RTO target and should use the lowest-cost configuration that supports the demo.
- Application and infrastructure logs must be retained centrally for at least 12 months with restricted access.
- The first cloud step must satisfy this checklist:
  1. Environments: include at least dev and prod.
  2. Deployment: use repeatable automated deployments rather than click-ops.
  3. Logging: retain logs centrally for at least 12 months for both dev and prod environments.
  4. Starting point: keep the initial solution simple.
  5. Cost: provide a monthly estimate for dev and prod using the cloud provider's pricing calculator or a stated price source.
  6. Justification: justify each SKU or service choice as the lowest-cost option that meets the applicable environment's targets: for prod, availability of at least 99.9%, RPO no greater than one hour, and RTO no greater than four hours; for dev, the lowest-cost configuration that supports the demo, with no availability, RPO, or RTO target. Both environments must retain logs centrally for at least 12 months.
  7. Pricing fallback: if live pricing cannot be retrieved, use a clearly stated list-price assumption with its date and source, and mark the cost figures as NOT VERIFIED.
- The original assessment permits Azure or AWS; this repository has selected Azure. Explain that choice and its trade-offs. Do not reopen cloud selection unless the user explicitly requests it.

Treat any unstated implementation details as assumptions. Record assumptions explicitly, especially where they affect residency, availability, recovery, security, cost, and operational ownership.

## Expected deliverables

1. **Management summary** (maximum three pages): business context and objectives, proposed direction with a Mermaid flowchart diagram embedded in docs/architecture-summary.md, key decisions and trade-offs, assumptions, risks, and a link to the CloudNation 6D model. Do not reproduce the full 6D model.
2. **Cloud proof of concept**: a minimal Azure deployment using IaC, with one API or function, a basic data store, and central logging. Include a clear repeatable deployment path using CLI scripts or a small CI example.
   1. **Region**: default all IaC templates to an EU region (for example West Europe or Germany West Central).
   2. **Residency**: keep all data stores, backups, disaster-recovery replicas, and central log storage in EU regions, including any secondary region used to meet the RPO and RTO targets. Reject any non-EU region with a policy check or parameter validation. Reject any design that places data outside the EU and document it as a residency risk.
   3. **Data store**: state the Azure PostgreSQL service (for example Azure Database for PostgreSQL Flexible Server), the environment-specific SKU, the approach for migrating or replicating the on-premises PostgreSQL data, and how the prod RPO of no greater than one hour is achieved.
   4. **Verification**: confirm that the chosen PostgreSQL SKU, the zone-redundant or standby option, and the secondary EU region are available in the selected regions. Record the check and its date in docs/assumptions.md.
   5. **Fallback**: if a required option is unavailable, select the next lowest-cost option that meets the prod targets and document its RPO and RTO impact.
3. **Presentation**: 15–20 minutes plus a short demo for no more than 20 minutes for NovaBank's CTO and Head of Engineering. Explain the direction, demonstrate the proof of concept, and outline next steps.

Suggested repository structure:

```text
/docs/
  architecture-summary.md
  assumptions.md
  timelog.md
/iac/
/ai/
  README.md
/demo/
  README.md
/slides/                 # optional
```

The human assessment author must maintain docs/timelog.md, recording actual time spent per workstream in hours and stating any time budget used for scope decisions. The model must only create a template with the workstream rows (planning, IaC, AI helper, documentation, demo) and leave hour values blank until the author fills them in; preserve any author-recorded hours.

The management summary (docs/architecture-summary.md) must include the business context, proposed direction, diagram, assumptions, risks, and 6D reference. Do not create a separate architecture summary document. The demo README should state prerequisites, deployment and test commands, and expected outcomes. Slides are optional but recommended.

## Recommended workflow

1. Extract the customer goals, constraints, success targets, stakeholders, and unknowns from the case before choosing services.
2. Use the selected Azure direction and a deliberately small architecture. Explain how the design addresses dev/prod separation, deployment repeatability, logging and retention, data residency, availability, recovery, and cost.
3. Make trade-offs explicit. Distinguish what the proof of concept demonstrates from what would require production hardening or validation.
4. Implement only the slice needed to demonstrate the direction. Keep deployment reproducible and document prerequisites, commands, and expected results. If a deployment or test cannot be executed in the current environment, do not report it as successful. Document the exact command, the reason it was not run, and the expected result, and mark the status as NOT VERIFIED. If a deployment or test fails, report the exact command, observed failure, and expected result, and mark the status as FAILED.
5. Add one practical AI helper, such as IaC review, architecture explanation, or log insight summarization. Show what context it receives and how its output is used; do not present AI as a substitute for validation or human decisions. The AI helper must only receive synthetic data generated for this demo, or non-log data from which all personal identifiers, customer PII, account numbers, and account data have been removed, with removal verified by a named reviewer. Production logs and data derived from production logs are prohibited, even after redaction or de-identification; use only synthetic logs for log insight summarization. Its service endpoint must be in an EU region, and the demo must document which data was sent to it. If the chosen Azure AI service has no EU-region endpoint, do not use that service. Choose an alternative Azure AI service with an EU-region endpoint. If no suitable Azure alternative is available, defer the AI helper, mark it NOT VERIFIED, and document the reason. Do not switch cloud providers unless the user explicitly requests it.
6. Prepare a concise management summary and a presentation/demo narrative for technical and business stakeholders.
7. Apply time-budget scope decisions as follows:
   a. If no time budget is stated in hours, do not assume one or cut scope on that basis.
   b. If a time budget is stated and cannot be met, keep dev and prod deployments and central logging.
   c. Keep the AI helper unless step 5 requires deferral. Step 5's EU-endpoint rule applies regardless of the budget; mark a deferred helper NOT VERIFIED and document the reason.
   d. Only when the stated time budget cannot be met, defer all other items and list them with next steps.

## Decision and quality checks

- Keep the solution specific to NovaBank and the stated financial-services constraints.
- Avoid complex platforms and unnecessary components. For prod, use the lowest-cost SKU and configuration for the API and database that meet the availability, RPO, and RTO targets, not merely the smallest SKU that runs the workload. For dev, use the lowest-cost configuration that supports the demo. Explain any larger SKU or redundancy required to meet the production targets. Enable autoscaling only on the API compute tier. If the API is a container or VM service, document a minimum and maximum instance count. If the API is a serverless function, state that instance scaling is platform-managed and document the concurrency or scale limit instead.
- Make cost, operational ownership, security, and compliance implications understandable to leadership.
- Do not claim a target such as 99.9% availability, RPO, or RTO is met unless the design and evidence support it. Identify validation still needed.
- Ensure central log access is limited to named security or platform operator groups through role-based access control (RBAC), with no shared keys or anonymous access, and the retention design keeps logs for at least 12 months.
- Keep environments and deployments repeatable; avoid undocumented manual cloud changes.
- Use AI for a bounded, demonstrable cloud-related task and review its output.
- Keep the management summary within three pages and the presentation within the stated 15–20 minute slot plus demo.

## CloudNation 6D reference

Include this link in the management summary, and refer to the model only where it helps explain the approach:

https://www.cloudnation.nl/en/inspiration/blogs/moving-to-the-cloud-how-to-structure-a-successful-migration
