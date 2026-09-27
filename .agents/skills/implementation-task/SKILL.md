---
name: implementation-task
description: Execute implementation, bug-fix, refactoring, and code-quality tasks in the Customer Intelligence Platform using the project's inspect-plan-approve-implement-verify-report workflow. Use for repository code changes that require understanding existing implementation, making focused changes, testing them, and reporting the result.
---

# Implementation Task

Use this skill when implementing or modifying code in the Customer Intelligence Platform.

Repository-wide architecture, scope, quality, and safety rules are defined in `AGENTS.md` and remain authoritative. Use `specs.md` to identify the design documents relevant to the task.

## 1. Understand the Task

Before changing code:

1. Read the current task carefully.
2. Read `specs.md` and the relevant portions of `Implementation_Plan.md`.
3. Read only the design documents relevant to the task.
4. Inspect the existing implementation, tests, and nearby patterns.
5. Reuse existing abstractions and capabilities where appropriate.

Do not begin by designing from assumptions when the repository can answer the question.

## 2. Classify the Change

Classify the task before implementation.

### Small / Well-Defined Change

Examples include:

- Renaming an existing component or symbol.
- Adding a clearly specified response field.
- Correcting a localized bug with an established expected behaviour.
- Updating a small configuration or documentation detail.
- Performing a mechanical refactor with no architectural impact.

For these tasks, proceed directly from inspection to implementation unless inspection reveals ambiguity or a design issue.

### Substantial / Ambiguous Change

Examples include:

- Cross-layer functionality.
- New business behaviour.
- Database/schema changes.
- Event-pipeline changes.
- New analytical data products.
- New dependencies or technologies.
- Changes affecting established architecture.
- Requirements whose semantics are not completely defined.

For these tasks:

1. Inspect the relevant implementation and specifications.
2. Produce a concise implementation plan.
3. Identify:
   - source data and affected layers;
   - existing capabilities that can be reused;
   - expected files/components to change;
   - test strategy;
   - genuine gaps, conflicts, or decisions requiring approval.
4. Stop after the plan.
5. Do not modify files until the user approves the implementation.

Do not manufacture approval questions when the specifications and implementation already provide a clear answer.

## 3. Implement the Approved Scope

During implementation:

1. Make the smallest coherent change that satisfies the task.
2. Follow existing repository structure and conventions.
3. Reuse existing services, DAL functions, schemas, components, hooks, utilities, and infrastructure where appropriate.
4. Keep changes within the approved task boundary.
5. Update tests alongside meaningful behavioural changes.
6. Do not continue into adjacent features or the next milestone without explicit instruction.

If implementation exposes a genuine design conflict, stop and follow the design-issue procedure in `AGENTS.md`.

## 4. Verify Incrementally

After implementation, verify the changed behaviour before running broad regression checks.

Recommended order:

```text
Changed behaviour
      ↓
Focused tests / checks
      ↓
Fix genuine failures
      ↓
Relevant integration tests
      ↓
Appropriate regression suite
```

Use the repository's canonical commands.

Do not use temporary environment, import-path, or test modifications merely to obtain a passing result.

If verification fails:

1. Start with the first/root failure.
2. Determine whether it is:
   - a production-code regression;
   - an incorrect or incomplete test;
   - test isolation/state pollution;
   - an infrastructure/environment problem;
   - an unrelated existing failure.
3. Gather evidence before changing code.
4. Fix the responsible layer rather than weakening unrelated tests or assertions.
5. Re-run the focused verification before returning to the broader suite.

Do not label failures as pre-existing without evidence.

## 5. Review the Final Change

Before reporting completion:

1. Review the final diff.
2. Check for:
   - unintended files;
   - unrelated changes;
   - temporary artifacts;
   - duplicated abstractions;
   - misplaced imports;
   - accidental dependency or lock-file changes;
   - debugging code or temporary workarounds.
3. Run:

```bash
git status --short
```

Do not commit, push, merge, checkout, restore, or delete user changes unless explicitly requested.

## 6. Report the Result

Return a concise structured completion report containing:

### Files Changed

List the files intentionally added or modified.

### Implementation

Summarize the behaviour implemented or corrected and the important design choices.

### Verification

Report the exact focused and regression checks performed and their results.

Do not claim verification that was not actually performed.

### Unresolved Issues

List genuine remaining issues, decisions, skipped verification, or environmental limitations.

If none remain, state that clearly.

### Git Status

Report the final relevant working-tree state.

## Completion Criteria

A task is complete only when:

- the requested behaviour is implemented;
- the implementation follows the approved architecture and scope;
- relevant tests/checks pass, or any failures are accurately explained;
- no unintended repository changes remain;
- the final status is reported accurately.