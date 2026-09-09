# Customer Intelligence Platform - Agent Instructions

## Before Working

1. Read `specs.md` for specification routing.
2. Read `Implementation_Plan.md` for the current phase, milestone, and progress.
3. Read only the design documents relevant to the current task.
4. Inspect existing code before proposing changes.
5. Do not load the entire `docs/` directory unless genuinely required.

## Implementation Workflow

For substantial changes:

1. Understand the requested task and relevant specifications.
2. Inspect the affected files and existing patterns.
3. Propose a concise implementation plan before modifying code.
4. Implement only after the plan is approved.
5. Run relevant tests, checks, or startup verification after implementation.
6. Report what changed, verification performed, and any unresolved issues.

Keep changes focused on the requested implementation unit.

## Architecture Boundaries

* Follow the finalized architecture and technology decisions.
* Do not redesign established decisions unless implementation exposes a genuine issue.
* Do not introduce new technologies or dependencies without justification.
* Keep API handlers thin.
* Keep business logic in the Business Service Layer.
* Keep database queries and persistence logic in the Data Access Layer.
* Reuse Business Services across APIs, Kafka consumers, scheduled jobs, and AI tools.
* Keep deterministic business processing independent of AI.
* Follow `11_Database_Design.md` for established schema, relationships, constraints, and indexes.
* Preserve source-of-truth, lineage, and data-integrity boundaries defined by the specifications.

## Scope & Code Quality

* Do not implement functionality outside the current task unless required by a direct dependency.
* Phase 1 code is production-inspired foundation code and must continue into the MVP rather than being disposable Prototype code.
* Prefer simple, readable implementations over unnecessary abstractions.
* Follow existing project conventions once established.
* Avoid premature optimization.
* Do not leave dead code, placeholder architecture, or unnecessary TODOs.
* Add or update tests for meaningful behaviour introduced by the task.

## Handling Design Issues

If implementation conflicts with a specification:

1. Stop before introducing a conflicting design.
2. Identify the affected specification.
3. Explain the implementation issue and tradeoffs.
4. Wait for approval before changing the established design.

Never silently override a documented architectural decision.
