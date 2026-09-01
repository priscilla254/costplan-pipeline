from src.etl.dto import ProjectHeader, WorkbookData
from src.etl.validate import validate_workbook


def test_validate_requires_header_fields():
    data = WorkbookData(header=ProjectHeader(source_sheet_name="PI-1"))
    issues = validate_workbook(data)
    columns = {i.column_name for i in issues}
    assert "ProjectID" in columns
    assert "SelectedContractor" in columns
