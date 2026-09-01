from decimal import Decimal

from src.etl.dto import ElementQuantity, ProjectHeader, ProjectQuantity, WorkbookData
from src.etl.resolve_dims import FakeDimLookup, resolve_dims


def _workbook(**overrides) -> WorkbookData:
    header = ProjectHeader(
        project_id="DEMO-2026-001",
        project_name="Elm Court",
        location_label="London",
        sector_code="Residential",
        cost_stage="Cost plan",
        selected_contractor="Ridgeway Construction",
        currency="GBP",
    )
    data = WorkbookData(header=header)
    for key, value in overrides.items():
        setattr(data, key, value)
    return data


LOOKUP = FakeDimLookup(
    sectors={"Residential": 1, "RES": 1},
    locations={"London": 2},
    contractors={"Ridgeway Construction": 3},
    element_l2={"1.1": 10},
    quant_types={"GIFA": 20, "gifa": 20},
)


def test_resolve_sector_name_and_code():
    keys, issues = resolve_dims(_workbook(), LOOKUP)
    assert not issues
    assert keys is not None
    assert keys.sector_key == 1
    assert keys.location_key == 2
    assert keys.contractor_key == 3


def test_unknown_contractor():
    data = _workbook()
    data.header.selected_contractor = "Unknown Ltd"
    keys, issues = resolve_dims(data, LOOKUP)
    assert keys is None
    assert any(i.error_type == "UNKNOWN_DIM" and "contractor" in i.error_message.casefold() for i in issues)


def test_unknown_l2():
    data = _workbook()
    data.element_quants = [
        ElementQuantity(
            l2_code="99.9",
            l2_name="Missing",
            quant_type_code="GIFA",
            qty=Decimal("1"),
            unit="m2",
            comment=None,
            row_num=2,
        )
    ]
    keys, issues = resolve_dims(data, LOOKUP)
    assert keys is None
    assert any("99.9" in i.error_message for i in issues)


def test_unknown_quant_type():
    data = _workbook()
    data.project_quants = [
        ProjectQuantity(
            quant_type_code="KEYS",
            quant_type_name="Keys",
            qty=Decimal("10"),
            unit="nr",
            comment=None,
            row_num=3,
        )
    ]
    keys, issues = resolve_dims(data, LOOKUP)
    assert keys is None
    assert any("KEYS" in i.error_message or "Keys" in i.error_message for i in issues)
