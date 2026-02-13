from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


TARGET_COLUMNS = [
    "STATE",
    "NETWORK",
    "INN DED",
    "INN OOP",
    "INN COI",
    "INN COP",
    "OON DED",
    "OON OOP",
    "OON COI",
    "OON COP",
]


def _read_csv_robust(path: str) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    last_err: Exception | None = None
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError as exc:
            last_err = exc
    if last_err:
        raise last_err
    return pd.read_csv(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge a smoke-run output back into a plan benefits CSV copy for review."
    )
    parser.add_argument("--base", required=True, help="Base plan benefits CSV path")
    parser.add_argument("--smoke", required=True, help="Smoke output CSV path")
    parser.add_argument("--out", required=True, help="Merged output CSV path")
    parser.add_argument(
        "--start-row",
        type=int,
        default=0,
        help="Start row in base file to replace when SOURCE_ROW is unavailable",
    )
    args = parser.parse_args()

    base_df = _read_csv_robust(args.base)
    smoke_df = _read_csv_robust(args.smoke)

    missing = [c for c in TARGET_COLUMNS if c not in base_df.columns]
    if missing:
        raise SystemExit(f"Base file missing expected columns: {missing}")

    for col in TARGET_COLUMNS:
        if col not in smoke_df.columns:
            smoke_df[col] = ""

    has_joint_payer_col = "PAYER NAME/PLAN" in base_df.columns
    has_split_payer_cols = "PAYER NAME" in base_df.columns and "PLAN NAME" in base_df.columns
    if "PAYER NAME/PLAN" not in smoke_df.columns:
        smoke_df["PAYER NAME/PLAN"] = ""

    def apply_row(idx: int, row: pd.Series) -> None:
        for col in TARGET_COLUMNS:
            base_df.at[idx, col] = row[col]
        payer_plan = str(row.get("PAYER NAME/PLAN", "")).strip()
        if has_joint_payer_col:
            base_df.at[idx, "PAYER NAME/PLAN"] = payer_plan
        if has_split_payer_cols and payer_plan:
            parts = payer_plan.split(" - ", 1)
            base_df.at[idx, "PAYER NAME"] = parts[0].strip()
            base_df.at[idx, "PLAN NAME"] = parts[1].strip() if len(parts) > 1 else ""

    updated = 0
    if "SOURCE_ROW" in smoke_df.columns:
        for _, row in smoke_df.iterrows():
            try:
                idx = int(row["SOURCE_ROW"])
            except Exception:
                continue
            if idx < 0 or idx >= len(base_df):
                continue
            apply_row(idx, row)
            updated += 1
    else:
        for i, (_, row) in enumerate(smoke_df.iterrows()):
            idx = args.start_row + i
            if idx >= len(base_df):
                break
            apply_row(idx, row)
            updated += 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base_df.to_csv(out_path, index=False)

    print(f"updated_rows={updated}")
    print(f"output={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
