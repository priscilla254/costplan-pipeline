"""String, number, and bit coercion used by every sheet parser."""

from __future__ import annotations

import html
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pandas as pd


def unescape_html_text(value) -> str:
    text = str(value)
    previous = None
    current = text
    for _ in range(3):
        if current == previous:
            break
        previous = current
        current = html.unescape(current)
    return current


def normalize_text(value) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "", unescape_html_text(value).strip().lower())


def cost_set_identifier(
    project_id: str, contractor_name: str, cost_stage: str | None
) -> str:
    """Stable grain for the current DimCostSet: project + contractor + stage."""
    stage = normalize_text(cost_stage) or "_"
    return f"{project_id.strip()}|{normalize_text(contractor_name)}|{stage}"[:250]


def clean_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        value = value.strip()
        return value if value != "" else None
    return value


def to_int(value) -> int | None:
    value = clean_value(value)
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def to_decimal(value) -> Decimal | None:
    value = clean_value(value)
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def to_bit(value) -> bool | None:
    value = clean_value(value)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def is_effectively_blank_row(row: pd.Series) -> bool:
    for value in row.values:
        if clean_value(value) is not None:
            return False
    return True


def format_code_text(value) -> str | None:
    cv = clean_value(value)
    if cv is None:
        return None
    text = str(cv).strip()
    try:
        d = Decimal(text)
    except Exception:
        return text
    return format(d.normalize(), "f")


def infer_l3_row_type(quantity, unit, rate, total_cost) -> str:
    has_qty = to_decimal(quantity) is not None
    has_unit = clean_value(unit) is not None
    has_rate = to_decimal(rate) is not None
    has_total = to_decimal(total_cost) is not None
    return "ITEM" if (has_qty and has_unit and has_rate and has_total) else "HEADING"
