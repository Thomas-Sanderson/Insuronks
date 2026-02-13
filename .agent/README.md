# Agent Orchestration

This folder supports a lightweight multi-agent workflow for Codex CLI.

## Roles
- `researcher`: reads code and writes a plan.
- `worker`: implements changes.
- `reviewer`: checks for bugs, regressions, and test gaps.

## Run Artifacts
Each orchestration run creates `.agent/runs/<run-id>/`:
- `task.md` shared task brief
- `<role>/prompt.md` role-specific prompt
- `<role>/status.txt` lifecycle (`queued`, `running`, `completed`, `failed`)
- `<role>/output.md` final model response
- `<role>/stdout.log`, `<role>/stderr.log` process logs

## Script
Run from workspace root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\pds-orchestrate.ps1 -Task "Your task here"
```

Optional:
- `-Roles researcher,worker,reviewer`
- `-OpenWindowsTerminal` to open one tab per role
- `-NoAutoApply` to disable `codex exec --full-auto`
- `-Model gpt-5`
