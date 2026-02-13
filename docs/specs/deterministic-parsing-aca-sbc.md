# Deterministic Parsing Spec

## Goal
Process large SBC corpora (22,000+ PDFs) with deterministic rules only.

## Runtime Constraints
- No AI calls in parsing runtime.
- Parser output schema is stable and column-compatible.
- Failures must be explicit (`error` column), not silent.

## Rule Strategy
1. Table-first extraction for canonical SBC rows.
2. Controlled regex fallback for missing table fields.
3. Value normalization pass for canonical output text.
4. Stable precedence order per field.

## Reliability Requirements
- Resumable bulk processing.
- Checkpointed output writes.
- Repeatable quality checks on output completeness and errors.

## Acceptance Gates
- Bulk run can resume after interruption.
- Error rate and blank-rate metrics are measurable per run.
- Any new rule includes an example failure it fixes.

## Phase 1 Thresholds (Task At Hand)
- `error_rate <= 5.0%` on the full corpus.
- `blank_rate <= 8.0%` for each key field: `INN DED`, `INN OOP`, `INN COI`, `INN COP`, `OON DED`, `OON OOP`, `OON COI`, `OON COP`.
- Resume test: stop mid-run, restart with `--resume`, and finish with no duplicated rows.
- Determinism test: same input and same code produce identical normalized values for sampled records.

## Agent Workflow (Swarm)
1. `researcher`: produce failure taxonomy and explicit extraction-rule map.
2. `worker`: implement deterministic rule changes and run checkpointed extraction.
3. `reviewer`: validate metrics against thresholds, list severity-ranked risks, and decide pass/fail.

## First Run Command Set (22k Pipeline)
1. Baseline extraction:
   `set PYTHONPATH=src && .venv\Scripts\python.exe -m aca_sbc.cli --csv "VIOP CS Tracker(ACA SBCs).csv" --out "out\plan_benefits_baseline.csv" --checkpoint-every 250`
2. Resume after interruption:
   `set PYTHONPATH=src && .venv\Scripts\python.exe -m aca_sbc.cli --csv "VIOP CS Tracker(ACA SBCs).csv" --out "out\plan_benefits_baseline.csv" --checkpoint-every 250 --resume`
3. Quality report:
   `set PYTHONPATH=src && .venv\Scripts\python.exe scripts\report_parse_quality.py --input "out\plan_benefits_baseline.csv" --json-out "out\plan_benefits_baseline.metrics.json"`

## Required Artifacts Per Improvement Cycle
- Updated parsing rules/code
- Run report (counts, errors, blank rates)
- Known unresolved failure classes

