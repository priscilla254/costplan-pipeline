"""Selected-contractor detection and Qty/Unit/Rate/Total column blocks."""

from __future__ import annotations

import pandas as pd

from src.etl.excel.text import clean_value, normalize_text


def detect_selected_contractor_from_sheet_row(raw_df: pd.DataFrame) -> str | None:
    if raw_df is None or raw_df.empty:
        return None

    first_row_values = None
    for _, row in raw_df.iterrows():
        vals = [clean_value(v) for v in row.tolist()]
        if any(v is not None for v in vals):
            first_row_values = vals
            break
    if not first_row_values:
        return None

    text_values = [str(v).strip() for v in first_row_values if v is not None]
    if not text_values:
        return None

    for text in text_values:
        low = text.lower()
        if "selected contractor" in low and ":" in text:
            candidate = text.split(":", 1)[1].strip()
            if candidate:
                return candidate

    for i, text in enumerate(text_values):
        low = text.lower()
        if "selected contractor" in low or low == "contractor" or "contractor name" in low:
            for j in range(i + 1, len(text_values)):
                candidate = text_values[j].strip()
                if candidate:
                    return candidate
    return None


def detect_selected_contractor_from_workbook(xls: pd.ExcelFile) -> str | None:
    for sheet in xls.sheet_names:
        try:
            raw_df = pd.read_excel(
                xls,
                sheet_name=sheet,
                engine="openpyxl",
                header=None,
                nrows=5,
            )
        except Exception:
            continue
        contractor = detect_selected_contractor_from_sheet_row(raw_df)
        if contractor:
            return contractor
    return None


def find_l3_metric_header_row(raw_df: pd.DataFrame) -> int | None:
    for idx in range(len(raw_df)):
        row_values = [normalize_text(v) for v in raw_df.iloc[idx].tolist()]
        if not row_values:
            continue
        qty_count = sum(1 for v in row_values if v in {"qty", "quantity"})
        unit_count = sum(1 for v in row_values if v in {"unit", "uom"})
        rate_count = sum(1 for v in row_values if v == "rate")
        total_count = sum(
            1 for v in row_values if v in {"total", "totalcost", "amount", "value"}
        )
        if qty_count >= 1 and unit_count >= 1 and rate_count >= 1 and total_count >= 1:
            return idx
    return None


def find_contiguous_metric_blocks(
    header_row: list,
    expected_tokens: tuple[str, ...],
) -> list[tuple[int, ...]]:
    tokens = [normalize_text(v) for v in header_row]
    blocks: list[tuple[int, ...]] = []
    exp_len = len(expected_tokens)
    for i in range(0, len(tokens) - exp_len + 1):
        if tuple(tokens[i : i + exp_len]) == expected_tokens:
            blocks.append(tuple(range(i, i + exp_len)))
    return blocks


def select_metric_block_for_contractor(
    raw_df: pd.DataFrame,
    metric_row_idx: int,
    blocks: list[tuple[int, ...]],
    selected_contractor: str | None,
) -> tuple[int, ...] | None:
    if not blocks:
        return None
    if not selected_contractor:
        return blocks[0]

    contractor_key = normalize_text(selected_contractor)
    if not contractor_key:
        return blocks[0]

    for block in blocks:
        start_col = block[0]
        for r in range(max(0, metric_row_idx - 5), metric_row_idx):
            row_vals = raw_df.iloc[r].tolist()
            left = max(0, start_col - 3)
            right = min(len(row_vals), start_col + 5)
            probe = " ".join(
                str(v) for v in row_vals[left:right] if clean_value(v) is not None
            )
            if contractor_key in normalize_text(probe):
                return block

    contractor_positions: list[int] = []
    for r in range(max(0, metric_row_idx - 8), metric_row_idx):
        row_vals = raw_df.iloc[r].tolist()
        for c, value in enumerate(row_vals):
            cv = clean_value(value)
            if cv is None:
                continue
            if contractor_key in normalize_text(cv):
                contractor_positions.append(c)
    if contractor_positions:
        target_col = int(sum(contractor_positions) / len(contractor_positions))
        return min(blocks, key=lambda b: abs(((b[0] + b[-1]) / 2) - target_col))

    if len(blocks) > 1:
        return None
    return blocks[0]


def forward_fill_header_labels(values: list) -> list[str | None]:
    labels: list[str | None] = []
    current: str | None = None
    for value in values:
        cv = clean_value(value)
        if cv is not None:
            current = str(cv).strip()
        labels.append(current)
    return labels


def select_summary_block_from_header_row(
    header_row: list,
    blocks: list[tuple[int, int]],
    selected_contractor: str | None,
) -> tuple[int, int] | None:
    if not blocks:
        return None
    if not selected_contractor:
        return blocks[0]

    contractor_key = normalize_text(selected_contractor)
    if not contractor_key:
        return blocks[0]

    ff_labels = forward_fill_header_labels(header_row)

    for block in blocks:
        start_col, end_col = block[0], block[-1]
        primary_labels = []
        if start_col < len(ff_labels):
            primary_labels.append(ff_labels[start_col])
        if end_col < len(ff_labels):
            primary_labels.append(ff_labels[end_col])
        if any(label and contractor_key in normalize_text(label) for label in primary_labels):
            return block

    for block in blocks:
        start_col, end_col = block[0], block[-1]
        left = max(0, start_col - 1)
        right = min(len(ff_labels), end_col + 2)
        window_labels = [ff_labels[c] for c in range(left, right)]
        if any(label and contractor_key in normalize_text(label) for label in window_labels):
            return block

    contractor_positions: list[int] = []
    for c, value in enumerate(header_row):
        cv = clean_value(value)
        if cv is None:
            continue
        if contractor_key in normalize_text(cv):
            contractor_positions.append(c)
    if contractor_positions:
        target_col = int(sum(contractor_positions) / len(contractor_positions))
        return min(blocks, key=lambda b: abs(((b[0] + b[-1]) / 2) - target_col))

    if len(blocks) > 1:
        return None
    return blocks[0]
