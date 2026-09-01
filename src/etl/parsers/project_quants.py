"""Project Information - 2: Name / Qty / Unit / Comments → project quantities."""

from __future__ import annotations

import pandas as pd

from dataclasses import dataclass, field

from src.etl.dto import ProjectQuantity, ValidationIssue
from src.etl.excel.text import clean_value, is_effectively_blank_row, normalize_text, to_decimal
from src.etl.parsers.base import ParseResult


def normalize_project_quants_sheet(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    rename_map = {}
    for col in out.columns:
        n = normalize_text(col)
        if n in {"projectquantcode", "code", "ref", "reference"}:
            rename_map[col] = "ProjectQuantCode"
        elif n in {"projectquantname", "name", "names", "projectquant", "description"}:
            rename_map[col] = "ProjectQuantName"
        elif n in {"qty", "quantity", "quant"}:
            rename_map[col] = "Qty"
        elif n in {"unit", "uom"}:
            rename_map[col] = "Unit"
        elif n in {"comment", "comments", "note", "notes"}:
            rename_map[col] = "Comment"
    out = out.rename(columns=rename_map)
    if "ProjectQuantCode" not in out.columns and "ProjectQuantName" in out.columns:
        out["ProjectQuantCode"] = [f"PQ-{i + 1:03d}" for i in range(len(out))]
    return out


def extract_gifa(quants: list[ProjectQuantity]):
    for item in quants:
        label = normalize_text(item.quant_type_name or item.quant_type_code)
        if not label:
            continue
        if label in {"gifa", "grossinternalfloorarea", "grossinternalarea"} or "gifa" in label:
            if item.qty is not None:
                return item.qty
    return None


@dataclass
class ProjectQuantParseResult(ParseResult):
    rows: list[ProjectQuantity] = field(default_factory=list)


class ProjectQuantParser:
    def parse(self, df: pd.DataFrame, source_sheet_name: str) -> ProjectQuantParseResult:
        result = ProjectQuantParseResult(rows=[])
        normalized = normalize_project_quants_sheet(df)
        if normalized is None or normalized.empty:
            return result
        if "ProjectQuantName" not in normalized.columns:
            result.issues.append(
                ValidationIssue(
                    sheet_name=source_sheet_name,
                    row_num=None,
                    column_name="ProjectQuantName",
                    error_type="MISSING_COLUMN",
                    error_message=f"Missing required column 'Name' in sheet '{source_sheet_name}'",
                )
            )
            return result

        for idx, row in normalized.iterrows():
            if is_effectively_blank_row(row):
                continue
            name = clean_value(row.get("ProjectQuantName"))
            code = clean_value(row.get("ProjectQuantCode"))
            qty_raw = row.get("Qty") if "Qty" in normalized.columns else None
            qty = to_decimal(qty_raw)
            if clean_value(qty_raw) is not None and qty is None:
                result.issues.append(
                    ValidationIssue(
                        sheet_name=source_sheet_name,
                        row_num=int(idx) + 2,
                        column_name="Qty",
                        error_type="INVALID_NUMBER",
                        error_message=f"Invalid Qty value: {qty_raw}",
                    )
                )
            result.rows.append(
                ProjectQuantity(
                    quant_type_code=str(code).strip() if code is not None else None,
                    quant_type_name=str(name).strip() if name is not None else None,
                    qty=qty,
                    unit=_str(row.get("Unit") if "Unit" in normalized.columns else None),
                    comment=_str(row.get("Comment") if "Comment" in normalized.columns else None),
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
