"""Project Information - 3: Code / Element / Qty / Unit → L2 element quantities."""

from __future__ import annotations

import pandas as pd

from dataclasses import dataclass, field

from src.etl.dto import ElementQuantity, ValidationIssue
from src.etl.excel.text import (
    clean_value,
    format_code_text,
    is_effectively_blank_row,
    normalize_text,
    to_decimal,
)
from src.etl.parsers.base import ParseResult


def _rename_element_quant_columns(frame: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for col in frame.columns:
        n = normalize_text(col)
        if n in {"l2code", "code", "ref", "reference"}:
            rename_map[col] = "L2Code"
        elif n in {"elementalquants", "element", "name", "l2name"}:
            rename_map[col] = "L2Name"
        elif n in {"quant", "quantity", "qty"}:
            rename_map[col] = "Qty"
        elif n in {"unit", "uom"}:
            rename_map[col] = "Unit"
        elif n in {"comment", "comments", "note", "notes"}:
            rename_map[col] = "Comment"
        elif n in {"quanttype", "quanttypecode"}:
            rename_map[col] = "QuantTypeCode"
    return frame.rename(columns=rename_map)


def normalize_element_quants_sheet(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    out = _rename_element_quant_columns(df.copy())
    if "L2Code" not in out.columns:
        probe = df.copy()
        probe.columns = [str(c).strip() for c in probe.columns]
        header_idx = None
        for i in range(min(15, len(probe))):
            tokens = {normalize_text(v) for v in probe.iloc[i].tolist()}
            has_code = "code" in tokens or "l2code" in tokens or "ref" in tokens
            has_element = "element" in tokens or "l2name" in tokens or "name" in tokens
            has_qty = "qty" in tokens or "quantity" in tokens or "quant" in tokens
            if has_code and (has_element or has_qty):
                header_idx = i
                break
        if header_idx is not None:
            header_vals = [
                str(clean_value(v)).strip() if clean_value(v) is not None else f"col_{idx}"
                for idx, v in enumerate(probe.iloc[header_idx].tolist())
            ]
            body = probe.iloc[header_idx + 1 :].copy()
            body.columns = header_vals
            body = body.reset_index(drop=True)
            out = _rename_element_quant_columns(body)

    if "L2Code" in out.columns:
        out["L2Code"] = out["L2Code"].map(format_code_text)
    if "QuantTypeCode" not in out.columns:
        out["QuantTypeCode"] = "DEFAULT"
    return out


@dataclass
class ElementQuantParseResult(ParseResult):
    rows: list[ElementQuantity] = field(default_factory=list)


class ElementQuantParser:
    def parse(self, df: pd.DataFrame, source_sheet_name: str) -> ElementQuantParseResult:
        result = ElementQuantParseResult(rows=[])
        normalized = normalize_element_quants_sheet(df)
        if normalized is None or normalized.empty:
            return result
        if "L2Code" not in normalized.columns:
            result.issues.append(
                ValidationIssue(
                    sheet_name=source_sheet_name,
                    row_num=None,
                    column_name="L2Code",
                    error_type="MISSING_COLUMN",
                    error_message=f"Missing required column 'Code' in sheet '{source_sheet_name}'",
                )
            )
            return result

        for idx, row in normalized.iterrows():
            if is_effectively_blank_row(row):
                continue
            l2_code = clean_value(row.get("L2Code"))
            if l2_code is None:
                continue
            qty_raw = row.get("Qty") if "Qty" in normalized.columns else None
            qty = to_decimal(qty_raw)
            result.rows.append(
                ElementQuantity(
                    l2_code=str(l2_code).strip(),
                    l2_name=_str(row.get("L2Name") if "L2Name" in normalized.columns else None),
                    quant_type_code=str(
                        clean_value(row.get("QuantTypeCode")) or "DEFAULT"
                    ).strip(),
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
