from src.etl.classify import (
    classify_l3_sheets,
    parse_l3_sheet_title,
    resolve_sheet_name,
)


def test_elm_court_sheet_aliases():
    names = [
        "Project Information - 1",
        "Project Information - 2",
        "Project Information - 3",
        "SUMMARY",
        "1.1 Substructure",
        "2.3 Roof",
        "Hidden Data",
    ]
    assert resolve_sheet_name("ProjectInformation", names) == "Project Information - 1"
    assert resolve_sheet_name("ProjectQuants", names) == "Project Information - 2"
    assert resolve_sheet_name("ElementQuants_L2", names) == "Project Information - 3"
    assert resolve_sheet_name("SUMMARY", names) == "SUMMARY"


def test_classify_l3_tabs():
    names = [
        "Project Information - 1",
        "SUMMARY",
        "1.1 Substructure",
        "2.3 Roof",
        "Hidden Data",
    ]
    l3 = classify_l3_sheets(names)
    decoded = {decoded for _, decoded in l3}
    assert "1.1 Substructure" in decoded
    assert "2.3 Roof" in decoded
    assert "Hidden Data" not in decoded
    assert "SUMMARY" not in decoded


def test_parse_l3_title():
    code, name = parse_l3_sheet_title("1.1 Substructure")
    assert code == "1.1"
    assert name == "Substructure"
