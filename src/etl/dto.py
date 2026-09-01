"""In-memory ingest contracts. Parsers emit these; load.py maps them to ORM."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass
class ValidationIssue:
    sheet_name: str | None
    row_num: int | None
    error_message: str
    column_name: str | None = None
    error_type: str = "VALIDATION"


@dataclass
class ProjectHeader:
    project_id: str | None = None
    project_name: str | None = None
    client_name: str | None = None
    location_label: str | None = None
    sector_code: str | None = None
    cost_stage: str | None = None
    selected_contractor: str | None = None
    data_status: str | None = None
    demolition: bool | None = None
    new_build: bool | None = None
    refurbishment: bool | None = None
    horizontal_extension: bool | None = None
    vertical_extension: bool | None = None
    basement: bool | None = None
    asbestos: bool | None = None
    contamination: bool | None = None
    occupied: bool | None = None
    base_date: date | datetime | None = None
    bcis_q_date: str | None = None
    currency: str | None = None
    programme_length_in_weeks: int | None = None
    programme_type: str | None = None
    gifa: Decimal | None = None
    spec_level: str | None = None
    site_type: str | None = None
    access_constraints: str | None = None
    complexity_rating: int | None = None
    nr_of_storeys: int | None = None
    source_sheet_name: str = "Project Information - 1"


@dataclass
class ProjectQuantity:
    quant_type_code: str | None
    quant_type_name: str | None
    qty: Decimal | None
    unit: str | None
    comment: str | None
    row_num: int
    source_sheet_name: str = "Project Information - 2"


@dataclass
class ElementQuantity:
    l2_code: str | None
    l2_name: str | None
    quant_type_code: str
    qty: Decimal | None
    unit: str | None
    comment: str | None
    row_num: int
    source_sheet_name: str = "Project Information - 3"


@dataclass
class L2Cost:
    l1_code: str | None
    l1_name: str | None
    l2_code: str | None
    l2_name: str | None
    rate: Decimal | None
    total_cost: Decimal | None
    row_num: int | None = None
    source_sheet_name: str = "SUMMARY"


@dataclass
class LineItem:
    l2_code: str | None
    l2_name: str | None
    line_id: str | None
    display_order: int
    item_description: str | None
    quantity: Decimal | None
    unit: str | None
    rate: Decimal | None
    total_cost: Decimal | None
    row_type: str
    source_sheet_name: str


@dataclass
class Adjustment:
    adj_category: str | None
    adj_sub_type: str | None
    amount: Decimal | None
    method: str | None
    rate_percent: Decimal | None
    applied_to_base: bool | None
    included_in_comparison: bool | None
    row_num: int
    source_sheet_name: str = "Adjustments"


@dataclass
class WorkbookData:
    header: ProjectHeader
    project_quants: list[ProjectQuantity] = field(default_factory=list)
    element_quants: list[ElementQuantity] = field(default_factory=list)
    l2_costs: list[L2Cost] = field(default_factory=list)
    line_items: list[LineItem] = field(default_factory=list)
    adjustments: list[Adjustment] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)
    resolved_sheets: dict[str, str] = field(default_factory=dict)


@dataclass
class ResolvedKeys:
    """Integer FKs produced by resolve_dims. load.py must not look up labels."""

    project_id: str
    sector_key: int
    location_key: int
    contractor_key: int
    quant_type_by_code: dict[str, int] = field(default_factory=dict)
    element_l2_by_code: dict[str, int] = field(default_factory=dict)
    adj_type_by_pair: dict[tuple[str, str | None], int] = field(default_factory=dict)
