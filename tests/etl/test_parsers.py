from pathlib import Path

from src.etl.workbook import read_workbook

ELM_COURT = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "Elm_Court_Residential_Cost_Comparison_Anonymised.xlsx"
)


def test_project_info_reads_project_number():
    data = read_workbook(ELM_COURT)
    assert data.header.project_id == "DEMO-2026-001"
    assert data.header.project_name
    assert "elm court" in data.header.project_name.casefold()
    assert data.header.selected_contractor
    assert "ridgeway" in data.header.selected_contractor.casefold()


def test_project_quants_include_gifa():
    data = read_workbook(ELM_COURT)
    gifa_rows = [
        q
        for q in data.project_quants
        if q.quant_type_name and "gifa" in q.quant_type_name.casefold()
    ]
    assert gifa_rows
    assert gifa_rows[0].qty is not None
    assert data.header.gifa is not None


def test_element_quants_use_code_column():
    data = read_workbook(ELM_COURT)
    codes = {q.l2_code for q in data.element_quants if q.l2_code}
    assert any(code.startswith("0.1") or code == "0.1" for code in codes) or any(
        "." in (code or "") for code in codes
    )
    assert all(q.l2_code for q in data.element_quants if q.qty is not None)
