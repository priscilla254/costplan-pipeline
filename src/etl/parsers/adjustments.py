"""Optional Adjustments sheet."""

from __future__ import annotations

import pandas as pd

from dataclasses import dataclass, field

from src.etl.dto import Adjustment
from src.etl.excel.text import clean_value, is_effectively_blank_row, normalize_text, to_bit, to_decimal
from src.etl.parsers.base import ParseResult


def normalize_adjustments_sheet(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    rename_map = {}
    for col in out.columns:
        n = normalize_text(col)
        if n in {"adjcategory", "category"}:
            rename_map[col] = "AdjCategory"
        elif n in {"adjsubtype", "subtype"}:
            rename_map[col] = "AdjSubType"
        elif n in {"amount", "value", "total"}:
            rename_map[col] = "Amount"
        elif n == "method":
            rename_map[col] = "Method"
        elif n in {"ratepercent", "percent", "rate"}:
            rename_map[col] = "RatePercent"
        elif n == "appliedtobase":
            rename_map[col] = "AppliedToBase"
        elif n == "includedincomparison":
            rename_map[col] = "IncludedInComparison"
    return out.rename(columns=rename_map)


@dataclass
class AdjustmentsParseResult(ParseResult):
    rows: list[Adjustment] = field(default_factory=list)


class AdjustmentsParser:
    def parse(self, df: pd.DataFrame, source_sheet_name: str) -> AdjustmentsParseResult:
        result = AdjustmentsParseResult(rows=[])
        normalized = normalize_adjustments_sheet(df)
        if normalized is None or normalized.empty:
            return result
        for idx, row in normalized.iterrows():
            if is_effectively_blank_row(row):
                continue
            category = clean_value(row.get("AdjCategory"))
            if category is None:
                continue
            result.rows.append(
                Adjustment(
                    adj_category=str(category).strip(),
                    adj_sub_type=_str(row.get("AdjSubType")),
                    amount=to_decimal(row.get("Amount")),
                    method=_str(row.get("Method")),
                    rate_percent=to_decimal(row.get("RatePercent")),
                    applied_to_base=to_bit(row.get("AppliedToBase")),
                    included_in_comparison=to_bit(row.get("IncludedInComparison")),
                    row_num=int(idx) + 2,
                    source_sheet_name=source_sheet_name,
                )
            )
        return result


def _str(value) -> str | None:
    cv = clean_value(value)
    if cv is None:
        return None
    return str(cv).strip()
