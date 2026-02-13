# Insuronks: ACA SBC Deterministic Parser

Deterministic extraction pipeline for ACA SBC PDFs, with a repeatable quality workflow and optional Codex swarm orchestration for parser improvement.

## Start Here
1. Install dependencies:
   `.venv\Scripts\python.exe -m pip install -r requirements.txt`
2. Run baseline extraction:
   `.venv\Scripts\python.exe -m aca_sbc.cli --csv "VIOP CS Tracker(ACA SBCs).csv" --out "out\plan_benefits_baseline.csv" --checkpoint-every 250`
3. Resume interrupted run:
   `.venv\Scripts\python.exe -m aca_sbc.cli --csv "VIOP CS Tracker(ACA SBCs).csv" --out "out\plan_benefits_baseline.csv" --checkpoint-every 250 --resume`
4. Generate quality metrics:
   `.venv\Scripts\python.exe scripts\report_parse_quality.py --input "out\plan_benefits_baseline.csv" --json-out "out\plan_benefits_baseline.metrics.json"`

## Human-Facing Docs
- `docs/README.md` : documentation index
- `docs/specs/deterministic-parsing-aca-sbc.md` : reliability spec and thresholds
- `docs/checklists/code-review-checklist.md` : review checklist
- `docs/smoke-test-playbook.md` : controlled sub-agent + parser smoke run guide

## Automation / Agent Files
- `AGENTS.md` : operating rules for code changes
- `.agent/` : role templates and run artifacts for orchestration
- `.vscode/tasks.json` : one-command task runner for extraction, reporting, and swarm launch

## Source Layout
- `src/aca_sbc/parse.py` : deterministic field extraction rules
- `src/aca_sbc/cli.py` : bulk runner with resume/checkpoint support
- `scripts/report_parse_quality.py` : run metrics
- `scripts/pds-orchestrate.ps1` : generic role orchestration
- `scripts/pds-parse-swarm.ps1` : parsing-focused swarm launcher
