from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm

from .download import download_pdf
from .parse import parse_pdf


def detect_url_column(df: pd.DataFrame) -> str:
    for candidate in [
        "URLForSummaryofBenefitsCoverage",
        "url",
        "URL",
        "pdf",
        "PDF",
        "link",
        "Link",
    ]:
        if candidate in df.columns:
            return candidate
    return df.columns[0]


def _get_col(df: pd.DataFrame, *candidates: str) -> str | None:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def _combine_payer_plan(row: pd.Series, payer_col: str | None, plan_col: str | None) -> str:
    payer = str(row[payer_col]).strip() if payer_col else ""
    plan = str(row[plan_col]).strip() if plan_col else ""
    if payer and plan:
        return f"{payer} - {plan}"
    return payer or plan or ""


def _build_row(
    row: pd.Series,
    state_col: str | None,
    payer_col: str | None,
    plan_col: str | None,
    parsed: Any = None,
    error: str | None = None,
) -> dict[str, Any]:
    out = {
        "STATE": str(row[state_col]).strip() if state_col else "",
        "NETWORK": "",
        "PAYER NAME/PLAN": _combine_payer_plan(row, payer_col, plan_col),
        "INN DED": "",
        "INN OOP": "",
        "INN COI": "",
        "INN COP": "",
        "OON DED": "",
        "OON OOP": "",
        "OON COI": "",
        "OON COP": "",
    }
    if parsed is not None:
        out.update(
            {
                "INN DED": parsed.inn_deductible,
                "INN OOP": parsed.inn_oop_max,
                "INN COI": parsed.inn_coinsurance,
                "INN COP": parsed.inn_iop_copay,
                "OON DED": parsed.oon_deductible,
                "OON OOP": parsed.oon_oop_max,
                "OON COI": parsed.oon_coinsurance,
                "OON COP": parsed.oon_iop_copay,
            }
        )
    if error:
        out["error"] = error
    return out


def _append_rows(rows: list[dict[str, Any]], out_path: Path, write_header: bool) -> None:
    if not rows:
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_path, mode="a", header=write_header, index=False)


def _count_output_rows(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return len(pd.read_csv(path))
    except Exception:
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract ACA SBC benefit fields from PDFs")
    parser.add_argument("--csv", required=True, help="Input CSV with URL column")
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--url-col", default=None, help="URL column name")
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=250,
        help="Flush output every N rows for resumability",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing output file row count",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    url_col = args.url_col or detect_url_column(df)

    state_col = _get_col(df, "StateCode", "STATE", "state")
    payer_col = _get_col(df, "IssuerMarketPlaceMarketingName", "PAYER NAME/PLAN", "payer")
    plan_col = _get_col(df, "PlanMarketingName", "PLAN NAME", "plan")

    out_path = Path(args.out)
    start_idx = _count_output_rows(out_path) if args.resume else 0
    write_header = not (args.resume and out_path.exists() and start_idx > 0)

    rows_buffer: list[dict[str, Any]] = []
    checkpoint_every = max(1, args.checkpoint_every)

    iterable = df.iloc[start_idx:].iterrows()
    total = max(0, len(df) - start_idx)
    for idx, row in tqdm(iterable, total=total, desc="PDFs"):
        url = str(row[url_col]).strip()
        try:
            pdf_path = download_pdf(url)
            parsed = parse_pdf(str(pdf_path))
            rows_buffer.append(_build_row(row, state_col, payer_col, plan_col, parsed=parsed))
        except Exception as exc:
            rows_buffer.append(_build_row(row, state_col, payer_col, plan_col, error=str(exc)))

        if len(rows_buffer) >= checkpoint_every:
            _append_rows(rows_buffer, out_path, write_header)
            write_header = False
            rows_buffer.clear()

    if rows_buffer:
        _append_rows(rows_buffer, out_path, write_header)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
