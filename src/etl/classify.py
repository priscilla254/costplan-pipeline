"""Map Excel tab names to canonical sheet types."""

from __future__ import annotations

import re

from src.etl.excel.text import unescape_html_text

REQUIRED_BASE_SHEETS = [
    "ProjectInformation",
    "ProjectQuants",
    "ElementQuants_L2",
    "SUMMARY",
]

SHEET_ALIASES: dict[str, list[str]] = {
    "ProjectInformation": [
        "ProjectInformation",
        "Project Information - 1",
        "Project Information -1",
        "Project Information",
    ],
    "ProjectQuants": ["ProjectQuants", "Project Information - 2"],
    "ElementQuants_L2": ["ElementQuants_L2", "Project Information - 3"],
    "SUMMARY": ["SUMMARY", "Summary"],
    "Adjustments": ["Adjustments"],
}

L3_SHEET_NAME_PATTERN = re.compile(r"^\s*([A-Za-z]*\d+(?:\.\d+)*)\s+(.+?)\s*$")


def workbook_sheet_lookup(sheet_names) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for name in sheet_names:
        actual = str(name)
        decoded = unescape_html_text(actual).strip()
        for key in {
            actual,
            decoded,
            actual.strip(),
            decoded.casefold(),
            actual.strip().casefold(),
        }:
            if key and key not in lookup:
                lookup[key] = actual
    return lookup


def resolve_sheet_name(canonical_name: str, sheet_names) -> str | None:
    lookup = workbook_sheet_lookup(sheet_names)
    candidates = SHEET_ALIASES.get(canonical_name, [canonical_name])
    for candidate in candidates:
        for key in (
            candidate,
            candidate.strip(),
            candidate.casefold(),
            candidate.strip().casefold(),
        ):
            if key in lookup:
                return lookup[key]
    return None


def all_base_sheet_keys() -> set[str]:
    names: set[str] = set(REQUIRED_BASE_SHEETS)
    for canonical, aliases in SHEET_ALIASES.items():
        names.add(canonical)
        names.update(aliases)
    return {n.strip().casefold() for n in names}


def classify_l3_sheets(sheet_names) -> list[tuple[str, str]]:
    """Return (actual_name, decoded_name) for numbered NRM L3 tabs."""
    resolved: dict[str, str] = {}
    for canonical in list(SHEET_ALIASES):
        actual = resolve_sheet_name(canonical, sheet_names)
        if actual is not None:
            resolved[canonical] = actual
    resolved_actual = {v.strip().casefold() for v in resolved.values()}
    base_keys = all_base_sheet_keys()
    l3_sheets: list[tuple[str, str]] = []
    for sheet in sheet_names:
        actual_name = str(sheet)
        decoded_name = unescape_html_text(sheet).strip()
        if (
            actual_name.strip().casefold() in resolved_actual
            or decoded_name.casefold() in base_keys
            or actual_name.strip().casefold() in base_keys
        ):
            continue
        if L3_SHEET_NAME_PATTERN.match(decoded_name):
            l3_sheets.append((actual_name, decoded_name))
    return l3_sheets


def parse_l3_sheet_title(decoded_name: str) -> tuple[str | None, str | None]:
    match = L3_SHEET_NAME_PATTERN.match(decoded_name)
    if not match:
        return None, None
    return match.group(1).strip(), unescape_html_text(match.group(2)).strip()
