from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

KEY_FIELDS = [
    "INN DED",
    "INN OOP",
    "INN COI",
    "INN COP",
    "OON DED",
    "OON OOP",
    "OON COI",
    "OON COP",
]


def _blank_rate(series: pd.Series) -> float:
    text = series.fillna("").astype(str).str.strip()
    if len(text) == 0:
        return 0.0
    blanks = (text == "").sum()
    return float(blanks) / float(len(text))


def build_report(df: pd.DataFrame) -> dict:
    total_rows = int(len(df))
    error_count = int(df["error"].fillna("").astype(str).str.strip().ne("").sum()) if "error" in df.columns else 0
    error_rate = float(error_count) / float(total_rows) if total_rows else 0.0

    fields = {}
    for field in KEY_FIELDS:
        if field in df.columns:
            fields[field] = {"blank_rate": _blank_rate(df[field])}
        else:
            fields[field] = {"blank_rate": None, "missing_column": True}

    return {
        "rows": total_rows,
        "error_count": error_count,
        "error_rate": error_rate,
        "fields": fields,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Report parse quality metrics for ACA SBC output CSV.")
    parser.add_argument("--input", required=True, help="Extractor output CSV path")
    parser.add_argument("--json-out", default=None, help="Optional JSON output path")
    args = parser.parse_args()

    path = Path(args.input)
    df = pd.read_csv(path)
    report = build_report(df)

    print(f"rows={report['rows']}")
    print(f"error_count={report['error_count']}")
    print(f"error_rate={report['error_rate']:.4%}")
    for field, stats in report["fields"].items():
        if stats.get("missing_column"):
            print(f"{field}: missing")
        else:
            print(f"{field}: blank_rate={stats['blank_rate']:.4%}")

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
