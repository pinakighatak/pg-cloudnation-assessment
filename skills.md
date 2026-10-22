# CloudNation Assessment Skill

Use this guidance when planning, implementing, reviewing, or presenting the CloudNation first-stage cloud consultant assessment in this repository.

## Role and objective

Act as a pragmatic cloud consultant for NovaBank. Understand the customer situation, make a simple and defensible first-step recommendation, demonstrate it with a small Infrastructure as Code (IaC) proof of concept, use AI for a practical cloud-related task, and communicate the result clearly.

Prioritize sound decisions, explicit trade-offs, and a working demo over breadth or polish. Do not over-engineer or imply that the proof of concept is production-ready.

## Case facts and constraints

- NovaBank is a digital bank moving a small on-premises customer portal toward public cloud.
- The current estate is a small web API on one VM, an on-premises PostgreSQL database, local-file-only logs, and no meaningful dev/test/prod separation.
- The business is regulated financial services, with EU data residency requirements.
- Baseline targets are availability of at least 99.9%, RPO no greater than one hour, and RTO no greater than four hours.
- Application and infrastructure logs must be retained centrally for at least 12 months with restricted access.
- The first cloud step must include at least dev and prod, repeatable automated deployments rather than click-ops, central logging, a simple starting point, and defensible cost choices.
- Choose Azure or AWS based on the case and explain why. The assessment does not prescribe a provider or a specific service stack.

Treat any unstated implementation details as assumptions. Record assumptions explicitly, especially where they affect residency, availability, recovery, security, cost, and operational ownership.

## Expected deliverables

1. **Management summary** (maximum three pages): business context and objectives, proposed direction with a simple diagram, key decisions and trade-offs, assumptions, risks, and a link to the CloudNation 6D model. Do not reproduce the full 6D model.
2. **Cloud proof of concept**: a minimal deployment in the selected cloud using IaC, with one API or function, a basic data store, and central logging. Include a clear repeatable deployment path using CLI scripts or a small CI example.
3. **Presentation**: 15–20 minutes plus a short demo for NovaBank's CTO and Head of Engineering. Explain the direction, demonstrate the proof of concept, and outline next steps.

Suggested repository structure:

```text
/docs/
  architecture-summary.pdf or architecture-summary.md
  assumptions.md
  timelog.md
/iac/
/ai/
  README.md
/demo/
  README.md
/slides/                 # optional
```

The architecture summary should include the business context, proposed direction, diagram, assumptions, risks, and 6D reference. The demo README should state prerequisites, deployment and test commands, and expected outcomes. Slides are optional but recommended.

## Recommended workflow

1. Extract the customer goals, constraints, success targets, stakeholders, and unknowns from the case before choosing services.
2. Select one cloud and a deliberately small architecture. Explain how the design addresses dev/prod separation, deployment repeatability, logging and retention, data residency, availability, recovery, and cost.
3. Make trade-offs explicit. Distinguish what the proof of concept demonstrates from what would require production hardening or validation.
4. Implement only the slice needed to demonstrate the direction. Keep deployment reproducible and document prerequisites, commands, and expected results.
5. Add one practical AI helper, such as IaC review, architecture explanation, or log insight summarization. Show what context it receives and how its output is used; do not present AI as a substitute for validation or human decisions.
6. Prepare a concise management summary and a presentation/demo narrative for technical and business stakeholders.
7. If time limits force scope cuts, state what was deferred and what should be done next.

## Decision and quality checks

- Keep the solution specific to NovaBank and the stated financial-services constraints.
- Avoid complex platforms and unnecessary components; prefer small SKUs and autoscaling where appropriate.
- Make cost, operational ownership, security, and compliance implications understandable to leadership.
- Do not claim a target such as 99.9% availability, RPO, or RTO is met unless the design and evidence support it. Identify validation still needed.
- Ensure central log access is restricted and the retention design supports the 12-month requirement.
- Keep environments and deployments repeatable; avoid undocumented manual cloud changes.
- Use AI for a bounded, demonstrable cloud-related task and review its output.
- Keep the management summary within three pages and the presentation within the stated 15–20 minute slot plus demo.

## CloudNation 6D reference

Include this link in the management summary, and refer to the model only where it helps explain the approach:

https://www.cloudnation.nl/en/inspiration/blogs/moving-to-the-cloud-how-to-structure-a-successful-migration
