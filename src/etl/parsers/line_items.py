"""Numbered NRM tabs → L3 line items for the selected contractor."""

from __future__ import annotations

import pandas as pd

from dataclasses import dataclass, field

from src.etl.dto import LineItem, ValidationIssue
from src.etl.excel.contractor import (
    find_contiguous_metric_blocks,
    find_l3_metric_header_row,
    select_metric_block_for_contractor,
)
from src.etl.excel.text import clean_value, infer_l3_row_type, is_effectively_blank_row, to_decimal
from src.etl.parsers.base import ParseResult


def normalize_l3_sheet(
    raw_df: pd.DataFrame,
    l2_code: str | None,
    l2_name: str | None,
    selected_contractor: str | None,
) -> pd.DataFrame:
    header_idx = find_l3_metric_header_row(raw_df)
    if header_idx is None:
        raise ValueError("Could not detect L3 metric header row (Qty/Unit/Rate/Total).")

    header_row = raw_df.iloc[header_idx].tolist()
    data_df = raw_df.iloc[header_idx + 1 :].copy()
    if data_df.empty:
        return pd.DataFrame(
            columns=["L2Code", "L2Name", "ItemDescription", "Quantity", "Unit", "Rate", "TotalCost"]
        )

    blocks = find_contiguous_metric_blocks(header_row, ("qty", "unit", "rate", "total"))
    selected_block = select_metric_block_for_contractor(
        raw_df, header_idx, blocks, selected_contractor
    )
    if selected_block is None:
        raise ValueError("Could not resolve first Qty/Unit/Rate/Total block in L3 sheet.")
    qty_col, unit_col, rate_col, total_col = selected_block
    item_col = 1 if data_df.shape[1] > 1 else 0

    out = pd.DataFrame()
    out["L2Code"] = l2_code
    out["L2Name"] = l2_name
    out["ItemDescription"] = data_df.iloc[:, item_col]
    out["Quantity"] = data_df.iloc[:, qty_col]
    out["Unit"] = data_df.iloc[:, unit_col]
    out["Rate"] = data_df.iloc[:, rate_col]
    out["TotalCost"] = data_df.iloc[:, total_col]
    out["RowType"] = out.apply(
        lambda r: infer_l3_row_type(
            r.get("Quantity"), r.get("Unit"), r.get("Rate"), r.get("TotalCost")
        ),
        axis=1,
    )
    return out.dropna(how="all")


@dataclass
class LineItemParseResult(ParseResult):
    rows: list[LineItem] = field(default_factory=list)


class LineItemParser:
    def parse(
        self,
        raw_df: pd.DataFrame,
        source_sheet_name: str,
        l2_code: str | None,
        l2_name: str | None,
        selected_contractor: str | None,
        display_order_start: int = 1,
    ) -> LineItemParseResult:
        result = LineItemParseResult(rows=[])
        try:
            normalized = normalize_l3_sheet(
                raw_df, l2_code, l2_name, selected_contractor
            )
        except ValueError as exc:
            result.issues.append(
                ValidationIssue(
                    sheet_name=source_sheet_name,
                    row_num=None,
                    error_message=str(exc),
                    error_type="L3_LAYOUT",
                )
            )
            return result

        order = display_order_start
        for _, row in normalized.iterrows():
            if is_effectively_blank_row(row):
                continue
            desc = clean_value(row.get("ItemDescription"))
            row_type = str(clean_value(row.get("RowType")) or "HEADING").upper()
            result.rows.append(
                LineItem(
                    l2_code=l2_code,
                    l2_name=l2_name,
                    line_id=None,
                    display_order=order,
                    item_description=str(desc).strip() if desc is not None else None,
                    quantity=to_decimal(row.get("Quantity")),
                    unit=_str(row.get("Unit")),
                    rate=to_decimal(row.get("Rate")),
                    total_cost=to_decimal(row.get("TotalCost")),
                    row_type=row_type,
                    source_sheet_name=source_sheet_name,
                )
            )
            order += 1
        return result


def _str(value) -> str | None:
    cv = clean_value(value)
    if cv is None:
        return None
    return str(cv).strip()
