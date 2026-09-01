from pathlib import Path

from src.etl.landing import land_file


def test_land_file_uses_identifier_and_timestamp(tmp_path: Path):
    source = tmp_path / "plan.xlsx"
    source.write_bytes(b"fake-xlsx")
    dest = land_file(source, "DEMO-2026-001", tmp_path / "landing")
    assert dest.exists()
    assert dest.parent.name == "DEMO-2026-001"
    assert dest.name.endswith("_plan.xlsx")
    assert dest.read_bytes() == b"fake-xlsx"
