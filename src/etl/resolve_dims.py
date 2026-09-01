"""Map workbook labels to dimension keys. Lookup-only; no get-or-create."""

from __future__ import annotations

from typing import Protocol

from src.etl.dto import ResolvedKeys, ValidationIssue, WorkbookData
from src.etl.excel.text import normalize_text


class DimLookup(Protocol):
    def sector_key(self, code_or_name: str) -> int | None: ...
    def location_key(self, label: str) -> int | None: ...
    def contractor_key(self, name: str) -> int | None: ...
    def element_l2_key(self, l2_code: str) -> int | None: ...
    def quant_type_key(self, code_or_name: str) -> int | None: ...
    def adjustment_type_key(
        self, category: str, sub_type: str | None
    ) -> int | None: ...


class FakeDimLookup:
    """In-memory maps for unit tests (no SQL Server)."""

    def __init__(
        self,
        *,
        sectors: dict[str, int] | None = None,
        locations: dict[str, int] | None = None,
        contractors: dict[str, int] | None = None,
        element_l2: dict[str, int] | None = None,
        quant_types: dict[str, int] | None = None,
        adj_types: dict[tuple[str, str | None], int] | None = None,
    ) -> None:
        self._sectors = {normalize_text(k): v for k, v in (sectors or {}).items()}
        self._locations = {normalize_text(k): v for k, v in (locations or {}).items()}
        self._contractors = {normalize_text(k): v for k, v in (contractors or {}).items()}
        self._element_l2 = {normalize_text(k): v for k, v in (element_l2 or {}).items()}
        self._quant_types = {normalize_text(k): v for k, v in (quant_types or {}).items()}
        self._adj_types = {
            (normalize_text(cat), normalize_text(sub) if sub else None): key
            for (cat, sub), key in (adj_types or {}).items()
        }

    def sector_key(self, code_or_name: str) -> int | None:
        return self._sectors.get(normalize_text(code_or_name))

    def location_key(self, label: str) -> int | None:
        return self._locations.get(normalize_text(label))

    def contractor_key(self, name: str) -> int | None:
        return self._contractors.get(normalize_text(name))

    def element_l2_key(self, l2_code: str) -> int | None:
        return self._element_l2.get(normalize_text(l2_code))

    def quant_type_key(self, code_or_name: str) -> int | None:
        return self._quant_types.get(normalize_text(code_or_name))

    def adjustment_type_key(self, category: str, sub_type: str | None) -> int | None:
        return self._adj_types.get(
            (normalize_text(category), normalize_text(sub_type) if sub_type else None)
        )


def resolve_dims(
    data: WorkbookData, lookup: DimLookup
) -> tuple[ResolvedKeys | None, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    header = data.header
    sheet = header.source_sheet_name

    sector_key = lookup.sector_key(header.sector_code or "") if header.sector_code else None
    if sector_key is None:
        issues.append(
            ValidationIssue(
                sheet_name=sheet,
                row_num=None,
                column_name="SectorCode",
                error_type="UNKNOWN_DIM",
                error_message=f"Unknown sector '{header.sector_code}'",
            )
        )

    location_key = (
        lookup.location_key(header.location_label) if header.location_label else None
    )
    if location_key is None:
        issues.append(
            ValidationIssue(
                sheet_name=sheet,
                row_num=None,
                column_name="LocationLabel",
                error_type="UNKNOWN_DIM",
                error_message=f"Unknown location '{header.location_label}'",
            )
        )

    contractor_key = (
        lookup.contractor_key(header.selected_contractor)
        if header.selected_contractor
        else None
    )
    if contractor_key is None:
        issues.append(
            ValidationIssue(
                sheet_name=sheet,
                row_num=None,
                column_name="SelectedContractor",
                error_type="UNKNOWN_DIM",
                error_message=f"Unknown contractor '{header.selected_contractor}'",
            )
        )

    quant_type_by_code: dict[str, int] = {}
    for quant in data.project_quants:
        label = quant.quant_type_code or quant.quant_type_name
        if not label:
            continue
        key = lookup.quant_type_key(label)
        if key is None and quant.quant_type_name:
            key = lookup.quant_type_key(quant.quant_type_name)
        if key is None:
            issues.append(
                ValidationIssue(
                    sheet_name=quant.source_sheet_name,
                    row_num=quant.row_num,
                    column_name="ProjectQuantName",
                    error_type="UNKNOWN_DIM",
                    error_message=f"Unknown quantity type '{label}'",
                )
            )
        else:
            quant_type_by_code[normalize_text(label)] = key

    for quant in data.element_quants:
        q_label = quant.quant_type_code
        q_key = lookup.quant_type_key(q_label)
        if q_key is None and q_label != "DEFAULT":
            issues.append(
                ValidationIssue(
                    sheet_name=quant.source_sheet_name,
                    row_num=quant.row_num,
                    column_name="QuantTypeCode",
                    error_type="UNKNOWN_DIM",
                    error_message=f"Unknown quantity type '{q_label}'",
                )
            )
        elif q_key is not None:
            quant_type_by_code[normalize_text(q_label)] = q_key

    element_l2_by_code: dict[str, int] = {}
    l2_codes = {c.l2_code for c in data.l2_costs if c.l2_code}
    l2_codes.update(q.l2_code for q in data.element_quants if q.l2_code)
    l2_codes.update(i.l2_code for i in data.line_items if i.l2_code)
    for code in sorted(l2_codes):
        key = lookup.element_l2_key(code)
        if key is None:
            issues.append(
                ValidationIssue(
                    sheet_name="SUMMARY",
                    row_num=None,
                    column_name="L2Code",
                    error_type="UNKNOWN_DIM",
                    error_message=f"Unknown L2 element code '{code}'",
                )
            )
        else:
            element_l2_by_code[normalize_text(code)] = key

    adj_type_by_pair: dict[tuple[str, str | None], int] = {}
    for adj in data.adjustments:
        if not adj.adj_category:
            continue
        key = lookup.adjustment_type_key(adj.adj_category, adj.adj_sub_type)
        if key is None:
            issues.append(
                ValidationIssue(
                    sheet_name=adj.source_sheet_name,
                    row_num=adj.row_num,
                    column_name="AdjCategory",
                    error_type="UNKNOWN_DIM",
                    error_message=(
                        f"Unknown adjustment type '{adj.adj_category}' / '{adj.adj_sub_type}'"
                    ),
                )
            )
        else:
            adj_type_by_pair[(adj.adj_category, adj.adj_sub_type)] = key

    if issues or not header.project_id:
        return None, issues

    assert sector_key is not None
    assert location_key is not None
    assert contractor_key is not None
    return (
        ResolvedKeys(
            project_id=header.project_id,
            sector_key=sector_key,
            location_key=location_key,
            contractor_key=contractor_key,
            quant_type_by_code=quant_type_by_code,
            element_l2_by_code=element_l2_by_code,
            adj_type_by_pair=adj_type_by_pair,
        ),
        [],
    )


class SqlAlchemyDimLookup:
    """Production lookup against seeded gold dimensions."""

    def __init__(self, session) -> None:
        from src.schema.tables import (
            DimAdjustmentType,
            DimContractor,
            DimElementL2,
            DimLocation,
            DimQuantType,
            DimSector,
        )

        self._session = session
        self._DimSector = DimSector
        self._DimLocation = DimLocation
        self._DimContractor = DimContractor
        self._DimElementL2 = DimElementL2
        self._DimQuantType = DimQuantType
        self._DimAdjustmentType = DimAdjustmentType

    def _match(self, stored: str | None, wanted: str) -> bool:
        return bool(stored) and normalize_text(stored) == normalize_text(wanted)

    def sector_key(self, code_or_name: str) -> int | None:
        for row in self._session.query(self._DimSector).all():
            if self._match(row.sector_code, code_or_name) or self._match(
                row.sector_name, code_or_name
            ):
                return row.sector_key
        return None

    def location_key(self, label: str) -> int | None:
        for row in self._session.query(self._DimLocation).all():
            if (
                self._match(row.display_label, label)
                or self._match(row.region, label)
                or self._match(row.country, label)
            ):
                return row.location_key
        return None

    def contractor_key(self, name: str) -> int | None:
        for row in self._session.query(self._DimContractor).all():
            if self._match(row.contractor_name, name):
                return row.contractor_key
        return None

    def element_l2_key(self, l2_code: str) -> int | None:
        for row in self._session.query(self._DimElementL2).all():
            if self._match(row.l2_code, l2_code):
                return row.element_l2_key
        return None

    def quant_type_key(self, code_or_name: str) -> int | None:
        for row in self._session.query(self._DimQuantType).all():
            if self._match(row.quant_type_code, code_or_name) or self._match(
                row.quant_type_name, code_or_name
            ):
                return row.quant_type_key
        return None

    def adjustment_type_key(self, category: str, sub_type: str | None) -> int | None:
        for row in self._session.query(self._DimAdjustmentType).all():
            if self._match(row.adj_category, category) and (
                (sub_type is None and row.adj_sub_type is None)
                or self._match(row.adj_sub_type, sub_type or "")
            ):
                return row.adj_type_key
        return None
