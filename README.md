---
author: Pinaki Ghatak
last_updated: "2026-10-22"
---

## 1. Purpose

At CloudNation, we help organizations accelerate with **public cloud** and **AI**. We combine deep technical expertise with a no‑nonsense, people‑first mindset. This first‑stage assessment evaluates how you think and operate as a **consultant** — not just how you build.

We want to see how you:

- Assess a customer situation and the surrounding playing field (stakeholders, risks, constraints).
- Propose a sensible **cloud direction** without over‑engineering.
- Use **Infrastructure as Code (IaC)** pragmatically and repeatably.
- Communicate clearly (concise documentation + presentation).
- Use **AI** in a practical, cloud‑related way that genuinely helps.

Please keep solutions simple. We value **good decisions, explicit trade‑offs, and working demos** over scope and polish.

## 2. CloudNation’s 6D Model (reference only)

CloudNation uses a 6D Delivery Model to structure cloud journeys. For this assessment, **do not restate the full model**. Where relevant, reference how your approach aligns with the 6D model and **include a link** to it in your management summary:

> 6D reference link: **[CloudNation 6D Model](https://www.cloudnation.nl/en/inspiration/blogs/moving-to-the-cloud-how-to-structure-a-successful-migration)**

## 3. Case — NovaBank

**NovaBank** is a digital bank running a small customer portal on‑premises. They want to move to the **public cloud** and are evaluating CloudNation for a low‑risk, future‑proof start. CloudNation has been invited to propose the first step.

#### Current situation

- A small **web API** on a single VM.
- A **PostgreSQL** database on‑premises.
- **Logs** written to local files only.
- **One environment** — no real separation between development, test and production.

#### Business & compliance context

- **Regulated industry (financial services)**; **data residency: EU**.
- Baseline targets: availability ≥ **99.9%**, **RPO ≤ 1 hour**, **RTO ≤ 4 hours**.
- **Auditability**: application and infrastructure logs retained centrally for **≥ 12 months** with restricted access.

#### What NovaBank wants from the first step

- At least **dev** and **prod** in the cloud (**Azure or AWS** — you choose).
- Repeatable, automated deployments (no click‑ops).
- Central logging for application behaviour and incident investigation.
- A simple, clean starting point (avoid complex platforms at this stage).
- Cost awareness and choices that leadership can defend.

> **Important:** We deliberately keep the solution open. Choose reasonable cloud services and patterns that fit the case and constraints. Focus on explaining **why** your direction makes sense rather than listing every component.

## 4. Your role

You step in as a **consultant**. Understand the landscape, balance trade‑offs, and guide the customer to a pragmatic first step while demonstrating hands‑on capability.

You will:

- Propose a **simple, defensible cloud direction** for NovaBank (Azure or AWS).
- Build a **small proof‑of‑concept** in the cloud using **IaC** to illustrate that direction.
- Use **AI** to help your workflow (review, explain, or extract insight).
- **Present** your approach and recommendations clearly and concisely.

## 5. Scope & deliverables

We don’t expect a production‑grade system. Pick an achievable slice that demonstrates good judgement.

#### Deliverables

1. **Management summary** (max 3 pages)
   - Business context and objectives
   - Proposed direction (one simple diagram is enough)
   - Key decisions & trade‑offs, **assumptions**, **risks**
   - **Link** to CloudNation’s 6D model (no need to restate it)

2. **Cloud proof‑of‑concept**
   - Minimal deployment in the chosen cloud using **IaC**
   - One API/function, a basic data store, and **central logging**
   - Clear, repeatable deployment (CLI scripts or a small CI example)

3. **Presentation** (15–20 minutes + short demo)
   - Explain your direction; show the PoC; outline next steps
   - Assume the audience is NovaBank’s CTO and Head of Engineering

#### AI component examples

- **AI IaC Reviewer** — flag missing tags, public endpoints, lack of diagnostics, etc.
- **AI Architecture Explainer** — generate a one‑page, non‑technical rationale for leadership.
- **AI Log Insights Helper** — summarise app/infra logs and suggest likely next steps.

> Minimal working examples are fine. Show how you would feed context to an LLM and use the response.

## 6. How we assess

- **Consultative thinking**: stakeholders, constraints, trade‑offs.
- Clarity of cloud direction and its business justification.
- Use of IaC and clean, reproducible engineering.
- Practical use of AI (not just a buzzword).
- Communication: concise docs and a confident, honest presentation.

> If you have to cut scope due to time, be explicit and state what you would do next with more time.

## 7. Submission guidelines (repo structure)

Please submit a Git repository with at least:

```
/docs/
  architecture-summary.pdf   # or .md — includes business context, proposed direction, diagram, assumptions, risks, and 6D link
  assumptions.md
  timelog.md                 # rough overview of time spent per part
/iac/                        # your Bicep / Terraform / CDK code
/ai/                         # your AI helper + short README
/demo/README.md              # how to deploy and test the PoC (commands, prerequisites, expected outcome)
/slides/                     # optional: presentation PDF
```

## 8. Practical notes

- You may make **assumptions** — just list them in `/docs/assumptions.md`.
- Keep costs reasonable (small SKUs, autoscaling where applicable, no over‑engineering).
- Keep the **solution specific to the business case**, but avoid locking into a single tooling stack unless justified.
- Slides are optional but recommended.

## Implemented Azure proof of concept

See the [deployment and demo guide](demo/README.md) for the AVM-backed Bicep,
dev/prod setup, .NET isolated Functions API, OIDC GitHub Actions workflow and
verification boundaries. The [architecture summary](docs/architecture-summary.md)
explains the EU-only design and production recovery trade-offs.