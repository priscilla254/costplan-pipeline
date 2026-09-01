"""Shape and type checks on parsed DTOs. No database writes."""

from __future__ import annotations

from src.etl.dto import ValidationIssue, WorkbookData

REQUIRED_HEADER_FIELDS = (
    ("project_id", "ProjectID"),
    ("project_name", "ProjectName"),
    ("location_label", "LocationLabel"),
    ("sector_code", "SectorCode"),
    ("cost_stage", "CostStage"),
    ("selected_contractor", "SelectedContractor"),
)

ALLOWED_ROW_TYPES = {"ITEM", "HEADING", "SUBTOTAL"}


def validate_workbook(data: WorkbookData) -> list[ValidationIssue]:
    issues = list(data.issues)
    sheet = data.header.source_sheet_name

    for attr, column in REQUIRED_HEADER_FIELDS:
        if not getattr(data.header, attr, None):
            issues.append(
                ValidationIssue(
                    sheet_name=sheet,
                    row_num=None,
                    column_name=column,
                    error_type="MISSING_VALUE",
                    error_message=f"Missing required value '{column}' in sheet '{sheet}'",
                )
            )

    if data.header.currency and len(str(data.header.currency).strip()) != 3:
        issues.append(
            ValidationIssue(
                sheet_name=sheet,
                row_num=None,
                column_name="Currency",
                error_type="DOMAIN",
                error_message="Currency must be a 3-letter code",
            )
        )

    for item in data.line_items:
        if item.row_type not in ALLOWED_ROW_TYPES:
            issues.append(
                ValidationIssue(
                    sheet_name=item.source_sheet_name,
                    row_num=item.display_order,
                    column_name="RowType",
                    error_type="DOMAIN",
                    error_message=(
                        f"Invalid RowType '{item.row_type}'. Allowed: ITEM, HEADING, SUBTOTAL"
                    ),
                )
            )

    return issues
