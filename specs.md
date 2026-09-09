# Customer Intelligence Platform - Specification Guide

## Purpose

This file is the entry point for project specifications.

The finalized design documents are stored in `docs/` and remain the source of truth for implementation decisions.

For every implementation task:

1. Read `Implementation_Plan.md` for the current phase, milestone, and progress.
2. Read only the design documents relevant to the task using the guide below.
3. Load additional documents only when required by a cross-cutting dependency or missing information.
4. Do not load the entire `docs/` directory by default.

The goal is to remain aligned with the finalized architecture while minimizing unnecessary context usage.

---

## Specification Map

| Document                                                              | Use For                                                                                    |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| [`00_Project_Design_Journal.md`](./docs/00_Project_Design_Journal.md) | Historical reasoning and architectural tradeoffs. Read only when needed.                   |
| [`01_Product_Foundation.md`](./docs/01_Product_Foundation.md)         | Product vision, business domain, scope, and philosophy.                                    |
| [`02_Product_Requirements.md`](./docs/02_Product_Requirements.md)     | Functional requirements, personas, Prototype/MVP/Version 1 scope.                          |
| [`03_User_Workflows.md`](./docs/03_User_Workflows.md)                 | User-facing business workflows.                                                            |
| [`04_Product_Workflows.md`](./docs/04_Product_Workflows.md)           | End-to-end product behaviour.                                                              |
| [`05_System_Architecture.md`](./docs/05_System_Architecture.md)       | System components, boundaries, and end-to-end flows.                                       |
| [`06_Data_Architecture.md`](./docs/06_Data_Architecture.md)           | Data layers, entities, data products, lineage, and source-of-truth boundaries.             |
| [`07_AI_Architecture.md`](./docs/07_AI_Architecture.md)               | AI Gateway, investigation agent, retrieval, tools, knowledge layer, and AI security.       |
| [`08_API_Design.md`](./docs/08_API_Design.md)                         | REST capabilities and API interaction patterns.                                            |
| [`09_Technology_Decisions.md`](./docs/09_Technology_Decisions.md)     | Finalized technologies and infrastructure decisions.                                       |
| [`10_Backend_Design.md`](./docs/10_Backend_Design.md)                 | Backend structure, services, data access, event/background processing, and AI integration. |
| [`11_Database_Design.md`](./docs/11_Database_Design.md)               | PostgreSQL tables, columns, relationships, constraints, indexes, and materialized views.   |
| [`12_Frontend_Design.md`](./docs/12_Frontend_Design.md)               | React structure, dashboards, state management, and investigation UI.                       |

Current implementation status and execution sequence:

[`Implementation_Plan.md`](./Implementation_Plan.md)

---

## Task-Based Reading Guide

| Task                         | Read                                     |
| ---------------------------- | ---------------------------------------- |
| Infrastructure/project setup | `Implementation_Plan`, `09`, `10`, `12`  |
| Backend implementation       | `10` + relevant domain specification     |
| Database models/migrations   | `11`, `10`                               |
| Kafka/event ingestion        | `05`, `09`, `10`, relevant `11` sections |
| Business event processing    | `06`, `10`, `11`                         |
| Profiles/journeys/segments   | `06`, `11`                               |
| Analytics/metrics            | `06`, `11`                               |
| REST APIs                    | `08`, `10`                               |
| Frontend/dashboard           | `08`, `12`                               |
| AI Knowledge Pipeline        | `06`, `07`, `09`                         |
| AI Gateway/tools             | `07`, `08`, `10`                         |
| Investigation Agent          | `07`, `10`, relevant `11` sections       |
| Investigation UI             | `07`, `08`, `12`                         |
| Design conflict              | Relevant specification + `00`            |

---

## Implementation Rules

The architecture and technology decisions are already finalized.

* Do not redesign established decisions unless implementation exposes a genuine issue.
* Do not introduce new technologies without a clear requirement.
* Do not implement beyond the current task or milestone unless required by a dependency.
* Follow `11_Database_Design.md` for established database schema decisions.
* Keep business logic in the Business Service Layer.
* Keep persistence logic in the Data Access Layer.
* Reuse Business Services across APIs, Kafka consumers, scheduled jobs, and AI tools.
* Keep deterministic business processing independent of AI.
* Phase 1 code must continue directly into the MVP rather than being disposable Prototype code.

If specifications appear to conflict, identify the conflict before implementing rather than silently choosing or redesigning.
