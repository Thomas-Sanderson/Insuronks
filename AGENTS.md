# AGENTS.md

## Mission
Work in small, reversible changes to improve ACA SBC extraction quality and speed.

## Operating Rules
- Prefer task-based execution through `.vscode/tasks.json` for repeatability.
- Validate behavior with a command run before claiming completion.
- Keep edits scoped; do not refactor unrelated code.
- If a command mutates output files, state which files changed.

## Workflow
1. Clarify target outcome and acceptance criteria.
2. Inspect existing code paths before editing.
3. Implement the smallest fix.
4. Run smoke checks.
5. Summarize what changed, risks, and next step.

## Definition Of Done
- Change addresses the stated user issue.
- Relevant command(s) run without errors.
- Review checklist in `docs/checklists/code-review-checklist.md` is satisfied.

## Git Conventions
- Branch naming: `feat/<topic>`, `fix/<topic>`, `chore/<topic>`.
- Commit style: `type(scope): summary`.
- Avoid direct pushes to long-lived branches.

## Review Standard
- Prioritize correctness, regressions, and data integrity.
- Call out missing tests explicitly.
- Include file references for important changes.

