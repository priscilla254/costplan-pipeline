import pandas as pd

from src.etl.excel.text import infer_l3_row_type
from src.etl.parsers.line_items import LineItemParser, normalize_l3_sheet
from src.etl.parsers.summary import SummaryParser


def test_infer_item_vs_heading():
    assert infer_l3_row_type(10, "m2", 50, 500) == "ITEM"
    assert infer_l3_row_type(None, None, None, None) == "HEADING"


def test_line_item_parser_picks_qty_unit_rate_total_block():
    raw = pd.DataFrame(
        [
            ["Return to contents", None, None, None, None],
            ["Item", "Qty", "Unit", "Rate", "Total"],
            ["Excavate", 10, "m3", 25, 250],
            ["Notes only", None, None, None, None],
        ]
    )
    result = LineItemParser().parse(
        raw,
        source_sheet_name="1.1 Substructure",
        l2_code="1.1",
        l2_name="Substructure",
        selected_contractor=None,
    )
    assert not result.issues
    types = {row.row_type for row in result.rows}
    assert "ITEM" in types
    assert "HEADING" in types
    item = next(r for r in result.rows if r.row_type == "ITEM")
    assert item.quantity == 10
    assert item.total_cost == 250


def test_normalize_l3_sheet_skips_nav_row():
    raw = pd.DataFrame(
        [
            ["Return to contents", None, None, None, None],
            ["Desc", "Qty", "Unit", "Rate", "Total"],
            ["Concrete", 2, "m3", 100, 200],
        ]
    )
    out = normalize_l3_sheet(raw, "1.1", "Substructure", None)
    assert "Quantity" in out.columns
    assert len(out) == 1


def test_summary_parser_uses_selected_contractor_block():
    raw = pd.DataFrame(
        [
            ["Code", "Element", "Ridgeway Construction", None, "Other Co", None],
            [None, None, "Rate", "Total", "Rate", "Total"],
            ["1.0", "Substructure", None, None, None, None],
            ["1.1", "Foundations", 10, 1000, 99, 9999],
        ]
    )
    result = SummaryParser().parse(raw, "SUMMARY", "Ridgeway Construction")
    assert result.rows
    row = result.rows[0]
    assert row.l2_code == "1.1"
    assert row.total_cost == 1000
