from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import pdfplumber

NO_COPAY_RE = re.compile(r"\b(no copay|no copayment)\b", re.I)
NO_COINS_RE = re.compile(r"\b(no coinsurance)\b", re.I)
NO_CHARGE_RE = re.compile(r"\b(no charge|no cost|covered in full)\b", re.I)
UNLIMITED_RE = re.compile(r"\bunlimited\b", re.I)
ZERO_RE = re.compile(r"^0+(?:\.0+)?$")
MONEY_RE = re.compile(r"\$\s*([0-9][0-9,]*)")

@dataclass
class ParsedBenefits:
    inn_deductible: Optional[str]
    oon_deductible: Optional[str]
    inn_oop_max: Optional[str]
    oon_oop_max: Optional[str]
    inn_coinsurance: Optional[str]
    oon_coinsurance: Optional[str]
    inn_iop_copay: Optional[str]
    oon_iop_copay: Optional[str]


def _normalize_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    low = text.lower().rstrip(".;:")
    if low in {"not covered", "not-covered"}:
        return "Not Covered"
    if NO_CHARGE_RE.search(low):
        return "No charge"
    if NO_COPAY_RE.search(low):
        return "No copay"
    if NO_COINS_RE.search(low):
        return "No coinsurance"
    if UNLIMITED_RE.search(low):
        return "Unlimited"
    text = re.sub(r"\$\s+([0-9])", r"$\1", text)
    text = re.sub(r"([0-9])\s+%", r"\1%", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return text.strip()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _extract_important_questions(text: str) -> tuple[Optional[str], Optional[str]]:
    # Pull deductible and out-of-pocket limit from the "Important Questions" section.
    deductible = None
    oop = None
    for line in text.splitlines():
        norm = _normalize(line)
        if "what is the overall" in norm and "deductible" in norm:
            # Line likely includes question + answer, but answer might be on next line.
            continue
    # Fallback: scan tables (more reliable)
    return deductible, oop


def _parse_cost_share(cell: str) -> tuple[Optional[str], Optional[str]]:
    if not cell:
        return None, None
    text = " ".join(cell.split())
    copay = None
    coins = None
    if NO_COPAY_RE.search(text):
        copay = "No copay"
    if NO_COINS_RE.search(text):
        coins = "No coinsurance"
    if NO_CHARGE_RE.search(text) and not copay and not coins:
        copay = "No charge"
        coins = "No charge"
    m = re.search(r"\$[0-9,]+[^;\\n]*?copayment[^;\\n]*", text, re.I)
    if m:
        copay = m.group(0).strip()
    # If "other outpatient" appears, prefer the last $ amount in the cell.
    if "other outpatient" in text.lower():
        amounts = re.findall(r"\$([0-9,]+)", text)
        if amounts:
            copay = f"${amounts[-1]} copayment/visit"
    m = re.search(r"[0-9]+%\s*coinsurance[^;\n]*", text, re.I)
    if m:
        coins = m.group(0).strip()
    return coins, copay


def _first_amount_token(text: str) -> Optional[str]:
    if not text:
        return None
    if UNLIMITED_RE.search(text):
        return "Unlimited"
    if NO_CHARGE_RE.search(text):
        return "No charge"
    m = MONEY_RE.search(text)
    if m:
        return f"${m.group(1)}"
    if ZERO_RE.fullmatch(text.strip()):
        return "0"
    m = re.search(r"\b0\b", text)
    if m:
        return "0"
    return None


def _extract_in_out_from_sentence(text: str) -> tuple[Optional[str], Optional[str]]:
    if not text:
        return None, None
    t = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    t = t.replace("in- network", "in-network").replace("out-of- network", "out-of-network").replace("out of network", "out-of-network")
    t_lower = t.lower()

    inn = None
    oon = None

    # In-network amount often appears before the "for in-network" marker.
    if "for in-network" in t_lower or "for in network" in t_lower:
        parts = re.split(r"for in[- ]network", t, flags=re.I, maxsplit=1)
        if parts:
            inn = _first_amount_token(parts[0])

    # Out-of-network amount often appears before the "for out-of-network" marker,
    # and after the in-network marker if both appear.
    if "for out-of-network" in t_lower or "for out of network" in t_lower:
        m = re.split(r"for out[- ]of[- ]network", t, flags=re.I, maxsplit=1)
        if m:
            out_src = m[0]
            out_src = re.split(r"for in[- ]network", out_src, flags=re.I, maxsplit=1)[-1]
            oon = _first_amount_token(out_src)

    return inn, oon


def _split_in_oon(text: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not text:
        return None, None
    t = text.replace("\r", " ").replace("\n", " ")
    # Normalize separators
    t = re.sub(r"\s+", " ", t)
    inn = None
    oon = None
    # Patterns like "In Network: ... Out of Network: ..."
    m_in = re.search(r"(In\s*Network|In-Network)\s*:\s*([^;]+)", t, re.I)
    m_oon = re.search(r"(Out\s*of\s*Network|Out-of-Network)\s*:\s*([^;]+)", t, re.I)
    # Fallback for "In network $X ..." without colon
    if not m_in:
        m_in = re.search(r"(In\s*Network|In-Network)\s*([$0-9,./ ]+)", t, re.I)
    if not m_oon:
        m_oon = re.search(r"(Out\s*of\s*Network|Out-of-Network)\s*([$0-9,./ ]+)", t, re.I)
    if m_in:
        inn = m_in.group(2).strip()
    if m_oon:
        oon = m_oon.group(2).strip()
    if inn in {"/", "-"}:
        inn = None
    if oon in {"/", "-"}:
        oon = None
    if not inn and not oon:
        inn, oon = _extract_in_out_from_sentence(t)
    return inn, oon


def _extract_tables(pdf) -> list[list[list[str]]]:
    tables = []
    for page in pdf.pages:
        try:
            tables.extend(page.extract_tables() or [])
        except Exception:
            continue
    return tables


def _extract_ded_oop_from_tables(tables: list[list[list[str]]]) -> tuple[Optional[str], Optional[str]]:
    deductible = None
    oop = None
    in_net_re = re.compile(r"in[- ]?network", re.I)
    for table in tables:
        for row in table:
            if not row:
                continue
            row_text = _normalize(" ".join([c or "" for c in row]))
            if "summary of benefits and coverage" in row_text:
                continue
            if "what is the overall" in row_text and "deductible" in row_text:
                # Answers may be in a later cell (e.g., "In Network: $8,500...")
                if len(row) > 1 and row[1]:
                    deductible = row[1].strip()
                else:
                    for cell in row:
                        if not cell:
                            continue
                        cell_txt = cell.strip()
                        if in_net_re.search(cell_txt):
                            deductible = cell_txt
                            break
            if "out-of-pocket limit" in row_text and "for this plan" in row_text:
                if len(row) > 1 and row[1]:
                    oop = row[1].strip()
                else:
                    for cell in row:
                        if not cell:
                            continue
                        cell_txt = cell.strip()
                        if in_net_re.search(cell_txt):
                            oop = cell_txt
                            break
    return deductible, oop


def _extract_iop_outpatient_from_tables(tables: list[list[list[str]]]) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    inn_coi = inn_cop = oon_coi = oon_cop = None
    for table in tables:
        header = table[0] if table else []
        col_types = []
        for cell in header:
            h = _normalize(cell or "")
            if "non-ihcp" in h and "in-network" in h:
                col_types.append("inn")
            elif "non-ihcp" in h and "out-of-network" in h:
                col_types.append("oon")
            elif "out-of-network" in h or "out of network" in h:
                col_types.append("oon")
            elif "in-network" in h or "in network" in h:
                col_types.append("inn")
            elif "ihcp" in h:
                col_types.append("ihcp")
            else:
                col_types.append("")
        for row in table:
            if not row:
                continue
            # Skip single-cell header rows that repeat large blocks of text.
            if len(row) < 4:
                continue
            row_text = _normalize(" ".join([c or "" for c in row]))
            # The actual row typically has column 2 = "Outpatient services".
            col1 = _normalize(row[1] or "") if len(row) > 1 else ""
            if "outpatient services" in col1 and ("mental health" in row_text or "substance" in row_text or "behavioral" in row_text):
                # Try to find INN/OON cells by content rather than position.
                cells = [c or "" for c in row]
                oon_cell = ""
                inn_cell = ""

                # Prefer header-aligned columns (IHCP layouts).
                if col_types:
                    for idx, ctype in enumerate(col_types):
                        if idx >= len(cells):
                            continue
                        if ctype == "inn" and not inn_cell:
                            inn_cell = cells[idx]
                        if ctype == "oon" and not oon_cell:
                            oon_cell = cells[idx]
                    if not inn_cell:
                        # Fall back to non-IHCP in-network mention inside row
                        for c in cells:
                            if re.search(r"non-ihcp.*in[- ]network", c, re.I):
                                inn_cell = c
                                break

                if not oon_cell:
                    for c in cells:
                        if re.search(r"non-participating|out[- ]of[- ]network|out of network", c, re.I):
                            oon_cell = c
                            break
                # INN candidate: prioritize "intensive outpatient", then "other outpatient",
                # then "office visit", then any cost share cell.
                for c in cells:
                    if c == oon_cell:
                        continue
                    if re.search(r"intensive outpatient", c, re.I):
                        inn_cell = c
                        break
                if not inn_cell:
                    for c in cells:
                        if c == oon_cell:
                            continue
                        if re.search(r"other outpatient", c, re.I):
                            inn_cell = c
                            break
                if not inn_cell:
                    for c in cells:
                        if c == oon_cell:
                            continue
                        if re.search(r"office visit", c, re.I):
                            inn_cell = c
                            break
                if not inn_cell:
                    for c in cells:
                        if c == oon_cell:
                            continue
                        if re.search(r"\\$|copay|copayment|%\\s*coinsurance", c, re.I):
                            inn_cell = c
                            break
                inn_coi, inn_cop = _parse_cost_share(inn_cell or "")
                oon_coi, oon_cop = _parse_cost_share(oon_cell or "")
                # If OON says Not Covered (or row contains it), keep as is
                if (oon_cell or "").strip().lower().startswith("not covered") or re.search(r"not covered", row_text, re.I):
                    oon_coi = oon_cop = "Not Covered"
                return inn_coi, inn_cop, oon_coi, oon_cop
    return inn_coi, inn_cop, oon_coi, oon_cop


def parse_pdf(path: str) -> ParsedBenefits:
    # This is a baseline parser; we can harden it once we see real PDFs.
    full_text = []
    with pdfplumber.open(path) as pdf:
        tables = _extract_tables(pdf)
        for page in pdf.pages[:5]:
            text = page.extract_text() or ""
            full_text.append(text)

    text = _normalize(" ".join(full_text))

    def find(pattern: str) -> Optional[str]:
        m = re.search(pattern, text)
        return m.group(1).strip() if m else None

    ded, oop = _extract_ded_oop_from_tables(tables)
    inn_iop_coi, inn_iop_cop, oon_iop_coi, oon_iop_cop = _extract_iop_outpatient_from_tables(tables)
    # If deductible/OOP include both INN and OON in one cell, split them.
    inn_ded_split, oon_ded_split = _split_in_oon(ded)
    inn_oop_split, oon_oop_split = _split_in_oon(oop)

    return ParsedBenefits(
        inn_deductible=_normalize_value(
            inn_ded_split
            or ded
            or find(r"in-network annual deductible[^$]*?\$?([\w,.$/ ]+?) (?:out-of-network|oop|max|$)")
        ),
        oon_deductible=_normalize_value(
            oon_ded_split
            or find(r"out-of-network annual deductible[^$]*?\$?([\w,.$/ ]+?) (?:in-network|oop|max|$)")
        ),
        inn_oop_max=_normalize_value(
            inn_oop_split
            or oop
            or find(r"in-network out-of-pocket limit[^$]*?\$?([\w,.$/ ]+?) (?:out-of-network|coinsurance|$)")
        ),
        oon_oop_max=_normalize_value(
            oon_oop_split
            or find(r"out-of-network out-of-pocket limit[^$]*?\$?([\w,.$/ ]+?) (?:in-network|coinsurance|$)")
        ),
        inn_coinsurance=_normalize_value(
            inn_iop_coi
            or find(r"in-network coinsurance[^%]*?([\w,.$/% ]+?) (?:out-of-network|copay|$)")
        ),
        oon_coinsurance=_normalize_value(
            oon_iop_coi
            or find(r"out-of-network coinsurance[^%]*?([\w,.$/% ]+?) (?:in-network|copay|$)")
        ),
        inn_iop_copay=_normalize_value(
            inn_iop_cop
            or find(r"in-network[^.]*?intensive outpatient program[^$]*?\$?([\w,.$/% ]+?) (?:out-of-network|limit|$)")
        ),
        oon_iop_copay=_normalize_value(
            oon_iop_cop
            or find(r"out-of-network[^.]*?intensive outpatient program[^$]*?\$?([\w,.$/% ]+?) (?:in-network|limit|$)")
        ),
    )
