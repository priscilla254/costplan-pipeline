from src.etl.excel.text import cost_set_identifier


def test_cost_set_identifier_normalizes_contractor_and_stage():
    assert (
        cost_set_identifier("DEMO-2026-001", "Ridgeway Construction", "Cost plan")
        == "DEMO-2026-001|ridgewayconstruction|costplan"
    )


def test_cost_set_identifier_missing_stage_uses_placeholder():
    assert cost_set_identifier("P1", "Acme", None) == "P1|acme|_"


def test_same_contractor_spelling_collapses():
    a = cost_set_identifier("P1", "Ridgeway Construction", "Tender")
    b = cost_set_identifier("P1", "ridgeway construction", "tender")
    assert a == b
