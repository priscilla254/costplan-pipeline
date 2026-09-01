"""Open a workbook and run the sheet-type parser registry."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.etl.classify import (
    REQUIRED_BASE_SHEETS,
    SHEET_ALIASES,
    classify_l3_sheets,
    parse_l3_sheet_title,
    resolve_sheet_name,
)
from src.etl.dto import ProjectHeader, ValidationIssue, WorkbookData
from src.etl.excel.contractor import detect_selected_contractor_from_workbook
from src.etl.parsers.adjustments import AdjustmentsParser
from src.etl.parsers.element_quants import ElementQuantParser
from src.etl.parsers.line_items import LineItemParser
from src.etl.parsers.project_info import ProjectInfoParser
from src.etl.parsers.project_quants import ProjectQuantParser, extract_gifa
from src.etl.parsers.summary import SummaryParser


def read_workbook(path: str | Path, process_adjustments: bool = False) -> WorkbookData:
    xls = pd.ExcelFile(path, engine="openpyxl")
    data = WorkbookData(header=ProjectHeader())
    issues: list[ValidationIssue] = []

    required = list(REQUIRED_BASE_SHEETS)
    if process_adjustments:
        required.append("Adjustments")

    resolved: dict[str, str] = {}
    missing: list[str] = []
    for canonical in required:
        actual = resolve_sheet_name(canonical, xls.sheet_names)
        if actual is None:
            missing.append(canonical)
        else:
            resolved[canonical] = actual
    data.resolved_sheets = resolved

    if missing:
        alias_hint = {name: SHEET_ALIASES.get(name, [name]) for name in missing}
        issues.append(
            ValidationIssue(
                sheet_name=None,
                row_num=None,
                error_type="MISSING_SHEET",
                error_message=f"Missing required sheets: {missing}. Accepted names: {alias_hint}",
            )
        )
        data.issues = issues
        return data

    pi_sheet = resolved["ProjectInformation"]
    pi_df = pd.read_excel(xls, sheet_name=pi_sheet, engine="openpyxl")
    pi_df.columns = [str(c).strip() for c in pi_df.columns]
    pi_result = ProjectInfoParser().parse(pi_df, pi_sheet)
    issues.extend(pi_result.issues)
    if pi_result.header is not None:
        data.header = pi_result.header

    selected = data.header.selected_contractor
    if not selected:
        selected = detect_selected_contractor_from_workbook(xls)
        data.header.selected_contractor = selected

    pq_sheet = resolved["ProjectQuants"]
    pq_df = pd.read_excel(xls, sheet_name=pq_sheet, engine="openpyxl")
    pq_df.columns = [str(c).strip() for c in pq_df.columns]
    pq_result = ProjectQuantParser().parse(pq_df, pq_sheet)
    issues.extend(pq_result.issues)
    data.project_quants = pq_result.rows
    if data.header.gifa is None:
        data.header.gifa = extract_gifa(data.project_quants)

    eq_sheet = resolved["ElementQuants_L2"]
    eq_df = pd.read_excel(xls, sheet_name=eq_sheet, engine="openpyxl")
    eq_df.columns = [str(c).strip() for c in eq_df.columns]
    eq_result = ElementQuantParser().parse(eq_df, eq_sheet)
    issues.extend(eq_result.issues)
    data.element_quants = eq_result.rows

    summary_sheet = resolved["SUMMARY"]
    summary_raw = pd.read_excel(
        xls, sheet_name=summary_sheet, engine="openpyxl", header=None
    )
    summary_result = SummaryParser().parse(summary_raw, summary_sheet, selected)
    issues.extend(summary_result.issues)
    data.l2_costs = summary_result.rows

    line_parser = LineItemParser()
    for actual_name, decoded_name in classify_l3_sheets(xls.sheet_names):
        l2_code, l2_name = parse_l3_sheet_title(decoded_name)
        raw = pd.read_excel(
            xls, sheet_name=actual_name, engine="openpyxl", header=None
        )
        li_result = line_parser.parse(
            raw, actual_name, l2_code, l2_name, selected
        )
        if li_result.issues and not li_result.rows:
            continue
        issues.extend(li_result.issues)
        data.line_items.extend(li_result.rows)

    if process_adjustments and "Adjustments" in resolved:
        adj_sheet = resolved["Adjustments"]
        adj_df = pd.read_excel(xls, sheet_name=adj_sheet, engine="openpyxl")
        adj_df.columns = [str(c).strip() for c in adj_df.columns]
        adj_result = AdjustmentsParser().parse(adj_df, adj_sheet)
        issues.extend(adj_result.issues)
        data.adjustments = adj_result.rows

    data.issues = issues
    return data
