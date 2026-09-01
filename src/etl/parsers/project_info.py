"""Project Information - 1: labelled form → ProjectHeader."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.etl.dto import ProjectHeader, ValidationIssue
from src.etl.excel.text import clean_value, normalize_text, to_bit, to_decimal, to_int
from src.etl.parsers.base import ParseResult


def _canonical_project_info_field(key_text: str) -> list[str]:
    text = (key_text or "").strip()
    if not text:
        return []

    key_map = {
        "projectid": "project_id",
        "projectnumber": "project_id",
        "projectno": "project_id",
        "projectref": "project_id",
        "projectname": "project_name",
        "clientname": "client_name",
        "location": "location_label",
        "locationlabel": "location_label",
        "region": "location_label",
        "sector": "sector_code",
        "sectorcode": "sector_code",
        "coststage": "cost_stage",
        "contractorname": "selected_contractor",
        "selectedcontractor": "selected_contractor",
        "datastatus": "data_status",
        "demolition": "demolition",
        "newbuild": "new_build",
        "refurbishment": "refurbishment",
        "horizontalextension": "horizontal_extension",
        "verticalextension": "vertical_extension",
        "basement": "basement",
        "asbestos": "asbestos",
        "occupied": "occupied",
        "contamination": "contamination",
        "basedate": "base_date",
        "bcisqdate": "bcis_q_date",
        "currency": "currency",
        "programmelengthinweeks": "programme_length_in_weeks",
        "programmeweeks": "programme_length_in_weeks",
        "programmetype": "programme_type",
        "gifa": "gifa",
        "speclevel": "spec_level",
        "sitetype": "site_type",
        "accessconstraints": "access_constraints",
        "complexityrating": "complexity_rating",
        "nrofstoreys": "nr_of_storeys",
        "numberofstoreys": "nr_of_storeys",
    }

    n = normalize_text(text)
    fields: list[str] = []
    exact = key_map.get(n)
    if exact:
        fields.append(exact)
    if "selectedcontractor" in n and "selected_contractor" not in fields:
        fields.append("selected_contractor")
    return fields


def normalize_project_information_sheet(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    if "ProjectID" in df.columns and "ProjectName" in df.columns:
        return df

    cols = list(df.columns)
    if len(cols) < 2:
        return df
    key_col, val_col = cols[0], cols[1]

    out: dict[str, object] = {}
    for _, row in df.iterrows():
        k = clean_value(row.get(key_col))
        v = clean_value(row.get(val_col))
        if k is None:
            continue
        for canonical in _canonical_project_info_field(str(k).strip()):
            if v is not None or canonical not in out:
                out[canonical] = v
    return pd.DataFrame([out]) if out else df


def _header_from_row(row: pd.Series, source_sheet_name: str) -> ProjectHeader:
    def g(*names):
        for name in names:
            if name in row.index:
                return row.get(name)
        return None

    data = {str(c): row.get(c) for c in row.index}
    # Wide layout still uses Excel names
    project_id = clean_value(data.get("project_id") or data.get("ProjectID") or g("project_id"))
    project_name = clean_value(data.get("project_name") or data.get("ProjectName"))
    return ProjectHeader(
        project_id=str(project_id).strip() if project_id is not None else None,
        project_name=str(project_name).strip() if project_name is not None else None,
        client_name=_str(data.get("client_name") or data.get("ClientName")),
        location_label=_str(data.get("location_label") or data.get("LocationLabel") or data.get("Region")),
        sector_code=_str(data.get("sector_code") or data.get("SectorCode")),
        cost_stage=_str(data.get("cost_stage") or data.get("CostStage")),
        selected_contractor=_str(
            data.get("selected_contractor") or data.get("SelectedContractor")
        ),
        data_status=_str(data.get("data_status") or data.get("DataStatus")),
        demolition=to_bit(data.get("demolition") if "demolition" in data else data.get("Demolition")),
        new_build=to_bit(data.get("new_build") if "new_build" in data else data.get("NewBuild")),
        refurbishment=to_bit(
            data.get("refurbishment") if "refurbishment" in data else data.get("Refurbishment")
        ),
        horizontal_extension=to_bit(
            data.get("horizontal_extension")
            if "horizontal_extension" in data
            else data.get("HorizontalExtension")
        ),
        vertical_extension=to_bit(
            data.get("vertical_extension")
            if "vertical_extension" in data
            else data.get("VerticalExtension")
        ),
        basement=to_bit(data.get("basement") if "basement" in data else data.get("Basement")),
        asbestos=to_bit(data.get("asbestos") if "asbestos" in data else data.get("Asbestos")),
        contamination=to_bit(
            data.get("contamination") if "contamination" in data else data.get("Contamination")
        ),
        occupied=to_bit(data.get("occupied") if "occupied" in data else data.get("Occupied")),
        base_date=clean_value(data.get("base_date") or data.get("BaseDate")),
        bcis_q_date=_str(data.get("bcis_q_date") or data.get("BCIS Q Date") or data.get("BCISQDate")),
        currency=_str(data.get("currency") or data.get("Currency")),
        programme_length_in_weeks=to_int(
            data.get("programme_length_in_weeks")
            if "programme_length_in_weeks" in data
            else data.get("ProgrammeLengthInWeeks") or data.get("Programme (weeks)")
        ),
        programme_type=_str(data.get("programme_type") or data.get("ProgrammeType")),
        gifa=to_decimal(data.get("gifa") if "gifa" in data else data.get("GIFA")),
        spec_level=_str(data.get("spec_level") or data.get("SpecLevel") or data.get("Spec Level")),
        site_type=_str(data.get("site_type") or data.get("SiteType") or data.get("Site Type")),
        access_constraints=_str(
            data.get("access_constraints")
            or data.get("AccessConstraints")
            or data.get("Access Constraints")
        ),
        complexity_rating=to_int(
            data.get("complexity_rating")
            or data.get("ComplexityRating")
            or data.get("Complexity Rating")
        ),
        nr_of_storeys=to_int(
            data.get("nr_of_storeys") or data.get("NrOfStoreys") or data.get("Nr of Storeys")
        ),
        source_sheet_name=source_sheet_name,
    )


def _str(value) -> str | None:
    cv = clean_value(value)
    if cv is None:
        return None
    return str(cv).strip()


@dataclass
class ProjectInfoParseResult(ParseResult):
    header: ProjectHeader | None = None


class ProjectInfoParser:
    def parse(self, df: pd.DataFrame, source_sheet_name: str) -> ProjectInfoParseResult:
        result = ProjectInfoParseResult()
        normalized = normalize_project_information_sheet(df)
        if normalized is None or normalized.empty:
            result.issues.append(
                ValidationIssue(
                    sheet_name=source_sheet_name,
                    row_num=None,
                    error_message="Project information sheet is empty",
                    error_type="ROW_COUNT",
                )
            )
            return result

        populated = normalized.dropna(how="all")
        if len(populated) != 1:
            result.issues.append(
                ValidationIssue(
                    sheet_name=source_sheet_name,
                    row_num=None,
                    error_message=f"{source_sheet_name} should contain exactly 1 populated row",
                    error_type="ROW_COUNT",
                )
            )
        row = populated.iloc[0]
        result.header = _header_from_row(row, source_sheet_name)
        return result
