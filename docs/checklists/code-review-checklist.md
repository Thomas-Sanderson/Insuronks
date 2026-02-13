# Code Review Checklist

## Correctness
- [ ] Logic matches acceptance criteria
- [ ] No obvious regressions in extraction paths
- [ ] Error handling paths are tested manually or via command

## Data Integrity
- [ ] CSV column names unchanged unless intentional
- [ ] Row counts and key fields sanity-checked
- [ ] Null/empty handling verified for affected fields

## Maintainability
- [ ] Change is scoped and readable
- [ ] Comments explain non-obvious behavior only
- [ ] Follow-up work captured explicitly

## Validation Commands
- [ ] `PDS: Smoke CLI (--help)`
- [ ] `PDS: Extract Plan Benefits CSV` (when parser/data behavior changed)
- [ ] `PDS: Git Preflight` (for repo-based workflows)

