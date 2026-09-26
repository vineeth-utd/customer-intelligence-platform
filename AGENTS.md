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

### Repository Hygiene

Do not create or leave temporary editing artifacts in the repository, including `*.orig`, `*.bak`, `patch_*.py`, `fix_*.py`, `temp_*.py`, or similar helper/backup files.

Edit the intended source or test files directly. If temporary files are required during tooling, create them outside the repository and remove them when finished.

Before completing a task, run `git status --short` and ensure that every new or modified file is an intentional project change. Never delete or restore pre-existing user changes without explicit approval.

### Python Import Placement

Before adding an import to an existing Python file, inspect the module's existing import section.

All ordinary imports must be placed in the module-level import block at the top of the file, after the module docstring and before all declarations.

Do not place a new import immediately above the function/class that uses it or elsewhere in the middle of a module.

Deferred/local imports are allowed only when technically required, such as for an unavoidable circular dependency or optional dependency. Add a brief comment explaining the reason when one is necessary.

Before completing a Python task, verify that newly added imports are located in the existing top-level import section.

### API Implementation Rules

When implementing FastAPI endpoints:

- Routers remain thin and delegate business behavior to the Business Service Layer.
- Routers must not contain SQL, direct DAL access, or business aggregation logic.
- Reuse existing Business Service and DAL capabilities before adding new ones.
- Use typed Pydantic request/response schemas; do not expose SQLAlchemy models directly.
- Follow the API contracts, naming, versioning, pagination, and error conventions defined in the authoritative API design.
- Validate query/path parameters at the API boundary where appropriate.
- Date ranges must reject `start_date > end_date`.
- Missing requested resources return the project's standard not-found response.
- Empty valid result sets are successful responses, not not-found errors.
- Paginated endpoints must use deterministic ordering and the project's standard pagination shape.
- Keep APIs business/resource-oriented rather than coupled to a specific frontend screen.
- Do not introduce Prototype-only shortcuts; endpoints should remain reusable in later phases.
- Add focused API tests covering successful responses, validation, not-found behavior, and relevant empty-result cases.

### Test Verification

Run tests using the repository's canonical commands without temporary `PYTHONPATH`, `sys.path`, or other import-path/environment overrides.

Do not use path hacks to make tests pass. If the canonical test command fails because of package/import configuration, fix the repository/test structure instead.

### Frontend Implementation Rules

When implementing frontend functionality:

- Follow the frontend architecture, directory structure, component responsibilities, and state-management decisions defined in the authoritative frontend design.
- Reuse existing components, hooks, API clients, types, and utilities before creating new ones.
- Keep server state in TanStack Query; do not duplicate API-derived state into local/global client state without a concrete need.
- Keep API access out of presentation components. Use the established API client/query-hook layers.
- Use TypeScript types for API contracts and component interfaces; avoid `any` unless genuinely unavoidable.
- Components should have focused responsibilities. Do not place data fetching, transformation, and large presentation logic into a single component when the established architecture separates them.
- Implement explicit loading, error, empty, and success states for server-backed UI.
- Do not hardcode backend data that is available through the API.
- Do not introduce new UI/state/data-fetching libraries unless required by the existing design.
- Preserve responsive behavior and existing styling/design conventions.
- Add or update focused tests where required by the project's frontend testing strategy.

### Existing File Modifications

Before modifying an existing file, inspect enough of the file to understand its structure, imports, conventions, and nearby abstractions.

Integrate changes into the existing structure rather than appending locally convenient code, imports, helpers, or duplicate abstractions near the modification point.