from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


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
    parser = argparse.ArgumentParser(description="Create a small smoke-test sample CSV from a larger input CSV.")
    parser.add_argument("--input", required=True, help="Full input CSV path")
    parser.add_argument("--output", required=True, help="Sample CSV output path")
    parser.add_argument("--rows", type=int, default=30, help="Number of rows to include")
    parser.add_argument(
        "--mode",
        choices=["head", "random"],
        default="head",
        help="Sampling mode. head is deterministic contiguous rows.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed when mode=random")
    args = parser.parse_args()

    df = _read_csv_robust(args.input)
    rows = max(1, args.rows)

    if args.mode == "random":
        sample = df.sample(n=min(rows, len(df)), random_state=args.seed).copy()
    else:
        sample = df.head(rows).copy()

    sample.insert(0, "_source_row", sample.index)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(out_path, index=False)

    print(f"sample_rows={len(sample)}")
    print(f"output={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
