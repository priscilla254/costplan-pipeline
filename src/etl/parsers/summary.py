"""SUMMARY sheet → L2 element costs for the selected contractor."""

from __future__ import annotations

import pandas as pd

from dataclasses import dataclass, field

from src.etl.dto import L2Cost, ValidationIssue
from src.etl.excel.contractor import (
    select_metric_block_for_contractor,
    select_summary_block_from_header_row,
)
from src.etl.excel.text import clean_value, format_code_text, normalize_text, to_decimal
from src.etl.parsers.base import ParseResult


def _split_l1_l2_code(ref_value) -> tuple[str | None, str | None]:
    code = format_code_text(ref_value)
    if code is None:
        return None, None
    if "." not in code:
        return code, None
    major, minor = code.split(".", 1)
    if minor.strip("0") == "":
        return f"{major}.0", None
    return f"{major}.0", code


def normalize_summary_sheet(
    raw_df: pd.DataFrame, selected_contractor: str | None
) -> pd.DataFrame:
    header_idx = None
    for i in range(min(10, len(raw_df))):
        row_tokens = [normalize_text(v) for v in raw_df.iloc[i].tolist()]
        has_code_col = any(t in {"ref", "reference", "code"} for t in row_tokens)
        has_name_col = any(t in {"element", "name", "l2name"} for t in row_tokens)
        if has_code_col and has_name_col:
            header_idx = i
            break
    if header_idx is None:
        return pd.DataFrame()

    header_row = raw_df.iloc[header_idx].tolist()
    data_df = raw_df.iloc[header_idx + 1 :].copy()
    if data_df.empty:
        return pd.DataFrame()

    ref_col = name_col = rate_col = total_col = None
    selected_block = None
    for c, value in enumerate(header_row):
        token = normalize_text(value)
        if ref_col is None and token in {"ref", "reference", "code"}:
            ref_col = c
        elif name_col is None and token in {"element", "name", "l2name"}:
            name_col = c
        elif rate_col is None and token == "rate":
            rate_col = c
        elif total_col is None and token in {
            "averagetender",
            "total",
            "totalcost",
            "amount",
            "value",
            "cost",
        }:
            total_col = c

    contractor_metric_row_idx = None
    detected_blocks: list[tuple[int, int]] = []
    max_pairs = -1
    for i in range(header_idx, min(header_idx + 14, len(raw_df))):
        row_tokens = [normalize_text(v) for v in raw_df.iloc[i].tolist()]
        row_blocks: list[tuple[int, int]] = []
        for c in range(0, len(row_tokens) - 1):
            if row_tokens[c] == "rate" and row_tokens[c + 1] in {
                "total",
                "totalcost",
                "amount",
                "value",
            }:
                row_blocks.append((c, c + 1))
        if len(row_blocks) > max_pairs:
            max_pairs = len(row_blocks)
            contractor_metric_row_idx = i
            detected_blocks = row_blocks

    if contractor_metric_row_idx is not None:
        blocks = detected_blocks
        selected_block = select_summary_block_from_header_row(
            header_row, blocks, selected_contractor
        )
        if selected_block is None:
            selected_block = select_metric_block_for_contractor(
                raw_df, contractor_metric_row_idx, blocks, selected_contractor
            )
        data_df = raw_df.iloc[contractor_metric_row_idx + 1 :].copy()
        if selected_block is not None:
            rate_col, total_col = selected_block
        elif len(blocks) > 1 and selected_contractor:
            rate_col = None
            total_col = None

    out = pd.DataFrame()
    ref_series = data_df.iloc[:, ref_col] if ref_col is not None else data_df.iloc[:, 0]
    name_series = data_df.iloc[:, name_col] if name_col is not None else data_df.iloc[:, 1]

    l1_codes = []
    l1_names = []
    l2_codes = []
    l2_names = []
    current_l1_code = None
    current_l1_name = None
    for ref_val, name_val in zip(ref_series.tolist(), name_series.tolist()):
        l1_code, l2_code = _split_l1_l2_code(ref_val)
        name_clean = clean_value(name_val)
        if l2_code is None:
            current_l1_code = l1_code
            current_l1_name = name_clean
            l1_codes.append(l1_code)
            l1_names.append(name_clean)
            l2_codes.append(None)
            l2_names.append(None)
        else:
            l1_codes.append(current_l1_code or l1_code)
            l1_names.append(current_l1_name)
            l2_codes.append(l2_code)
            l2_names.append(name_clean)

    out["L1Code"] = l1_codes
    out["L1Name"] = l1_names
    out["L2Code"] = l2_codes
    out["L2Name"] = l2_names
    out["__SummarySourceExcelRow"] = data_df.index + 1

    if rate_col is not None and total_col is not None:
        rate_values = []
        total_values = []
        for src_idx in data_df.index.tolist():
            if 0 <= int(src_idx) < len(raw_df):
                rate_values.append(raw_df.iat[int(src_idx), rate_col])
                total_values.append(raw_df.iat[int(src_idx), total_col])
            else:
                rate_values.append(None)
                total_values.append(None)
        out["Rate"] = rate_values
        out["TotalCost"] = total_values
    else:
        out["Rate"] = None
        out["TotalCost"] = None

    l1_mask = out["L2Code"].isna()
    out.loc[l1_mask, "Rate"] = None
    out.loc[l1_mask, "TotalCost"] = None
    out = out[out["L2Code"].notna()].copy()
    return out.dropna(how="all")


@dataclass
class SummaryParseResult(ParseResult):
    rows: list[L2Cost] = field(default_factory=list)


class SummaryParser:
    def parse(
        self,
        raw_df: pd.DataFrame,
        source_sheet_name: str,
        selected_contractor: str | None,
    ) -> SummaryParseResult:
        result = SummaryParseResult(rows=[])
        normalized = normalize_summary_sheet(raw_df, selected_contractor)
        if selected_contractor and normalized.empty:
            result.issues.append(
                ValidationIssue(
                    sheet_name=source_sheet_name,
                    row_num=None,
                    error_message=(
                        f"Could not resolve Rate/Total columns for contractor "
                        f"'{selected_contractor}' on '{source_sheet_name}'"
                    ),
                    error_type="CONTRACTOR_BLOCK",
                )
            )
        for _, row in normalized.iterrows():
            total = to_decimal(row.get("TotalCost"))
            if total is None:
                continue
            excel_row = row.get("__SummarySourceExcelRow")
            result.rows.append(
                L2Cost(
                    l1_code=_str(row.get("L1Code")),
                    l1_name=_str(row.get("L1Name")),
                    l2_code=_str(row.get("L2Code")),
                    l2_name=_str(row.get("L2Name")),
                    rate=to_decimal(row.get("Rate")),
                    total_cost=total,
                    row_num=int(excel_row) if excel_row is not None and pd.notna(excel_row) else None,
                    source_sheet_name=source_sheet_name,
                )
            )
        return result


def _str(value) -> str | None:
    cv = clean_value(value)
    if cv is None:
        return None
    return str(cv).strip()
