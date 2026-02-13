# Smoke Test Playbook (Sub-Agent + Deterministic Parser)

## Purpose
Run a small, controlled end-to-end test that proves:
- branch + push + PR behavior
- sub-agent orchestration flow
- deterministic parser run on real PDFs
- merge-back preview into plan-benefit schema

## Scope
- Recommended sample size: `30` rows
- Input: `VIOP CS Tracker(ACA SBCs).csv`
- Output files are written under `out/`

## Steps
1. Build sample:
   `PDS: Smoke Build Sample CSV`
2. Run parse swarm in dry mode first:
   `PDS: Parse Swarm (Deterministic Rules)`
3. Extract sample deterministically:
   `PDS: Smoke Extract Sample`
4. Report quality:
   `PDS: Smoke Report Quality`
5. Merge-back preview:
   `PDS: Smoke Merge Into Plan Benefits Preview`

## Review Outputs
- `out/smoke_input.csv`
- `out/smoke_plan_benefits.csv`
- `out/smoke_plan_benefits.metrics.json`
- `out/VIOP Plan Benefits.smoke-merged-preview.csv`

## Notes
- The merge step writes a preview file only. It does not overwrite your primary plan benefits file.
- For contiguous head-sampling, merge-back mapping is exact (`SOURCE_ROW` metadata included in extraction output).
