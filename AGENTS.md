# Customer Intelligence Platform - Agent Instructions

## Before Working

1. Read `specs.md` for specification routing.
2. Read `Implementation_Plan.md` for the current phase, milestone, and progress.
3. Read only the design documents relevant to the current task.
4. Inspect existing code before proposing changes.
5. Do not load the entire `docs/` directory unless genuinely required.

## Implementation Workflow

First classify the task.

### Small / Well-Defined Changes

For local, mechanical, or clearly specified changes:

1. Read the relevant specifications and inspect the affected code.
2. Implement the smallest correct change.
3. Run focused verification.
4. Run broader regression checks when the change can affect shared behaviour.
5. Inspect the final diff and `git status --short`.
6. Report the changes and verification results.

### Substantial / Ambiguous Changes

For architectural, cross-layer, schema-changing, or ambiguous work:

1. Understand the task and relevant specifications.
2. Inspect the affected implementation and existing patterns.
3. Propose a concise implementation plan.
4. Identify genuine decisions, conflicts, or assumptions requiring approval.
5. Wait for approval before implementation.
6. Implement only the approved scope.
7. Run focused verification followed by appropriate regression checks.
8. Inspect the final diff and `git status --short`.
9. Report the changes, verification results, and unresolved issues.

Keep changes focused on the requested implementation unit. Do not continue into the next task or milestone without explicit instruction.

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
* Implementation from completed phases is foundation code for subsequent phases; do not replace working architecture with phase-specific shortcuts.
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

### Existing File Modifications

Before modifying an existing file, inspect enough of the file to understand its structure, imports, conventions, and nearby abstractions.

Integrate changes into the existing structure rather than appending locally convenient code, imports, helpers, or duplicate abstractions near the modification point.

### Python Import Placement

Before adding an import to an existing Python file, inspect the module's existing import section.

All ordinary imports must be placed in the module-level import block at the top of the file, after the module docstring and before all declarations.

Do not place a new import immediately above the function/class that uses it or elsewhere in the middle of a module.

Deferred/local imports are allowed only when technically required, such as for an unavoidable circular dependency or optional dependency. Add a brief comment explaining the reason when one is necessary.

Before completing a Python task, verify that newly added imports are located in the existing top-level import section.

### Dependencies

Before adding a dependency:

- Check whether the required capability already exists in the repository or standard library.
- Use technologies already selected in the authoritative design where applicable.
- Do not add a new library merely for convenience when existing project dependencies adequately solve the problem.
- If a genuinely new dependency is required, explain why before introducing it for substantial changes.
- Update the appropriate dependency and lock files together.

### Database Changes

For database/schema changes:

- Follow `11_Database_Design.md` and existing SQLAlchemy/Alembic conventions.
- Do not modify an already-applied migration to represent a new schema change; create a new migration.
- Preserve foreign-key, uniqueness, indexing, and lineage requirements.
- Consider test-fixture cleanup/isolation when introducing new foreign-key relationships.
- Verify migrations with upgrade/downgrade/upgrade where appropriate.
- Do not use destructive shortcuts such as CASCADE to hide dependency/order problems unless explicitly intended by the design.

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

### Test Verification

Use the repository's canonical test and verification commands.

Do not use temporary `PYTHONPATH`, `sys.path`, environment, or import-path overrides to make tests pass. If canonical commands expose an import/configuration problem, fix the repository structure instead.

When a test fails:

- Diagnose the first/root failure before making broad changes.
- Do not assume or report that a failure is "pre-existing" unless verified against the known baseline or repository history.
- Do not weaken assertions, increase arbitrary limits, skip tests, or modify unrelated tests merely to obtain a green suite.
- Distinguish genuine regressions from test-environment pollution such as stale Kafka messages or synthetic database state.
- Fix production code when production behaviour is wrong; fix tests only when the test itself is incorrect or its isolation/setup is incomplete.

Run focused tests for the changed behaviour first, then the appropriate regression suite.

### Local Runtime & Infrastructure

Before diagnosing runtime integration issues, verify which processes/containers are actually serving the relevant ports.

Do not run duplicate local and Dockerized application services on the same host port.

Treat synthetic E2E environments and clean automated-test environments separately. Reset stateful infrastructure when necessary rather than changing correct tests to accommodate polluted Kafka/database state.

### Task Completion

Before reporting completion:

- Review the final diff for unintended or unrelated changes.
- Run `git status --short`.
- Do not commit, push, merge, restore, checkout, or delete user changes unless explicitly requested.
- Report:
  - files changed
  - implementation summary
  - verification/tests performed and their results
  - unresolved issues or decisions
  - final git status

Do not claim a task is fully verified if required tests were skipped, unavailable, or run using non-standard workarounds.