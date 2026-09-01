"""CLI: land file, parse, validate, resolve dims, load gold."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.etl.dto import ValidationIssue
from src.etl.landing import land_file
from src.etl.load import load_gold
from src.etl.resolve_dims import SqlAlchemyDimLookup, resolve_dims
from src.etl.validate import validate_workbook
from src.etl.workbook import read_workbook
from src.schema.tables import IngestionLog, StagingValidationError


def _write_failures(
    session: Session, ingestion: IngestionLog, issues: list[ValidationIssue]
) -> None:
    for issue in issues:
        session.add(
            StagingValidationError(
                ingestion_key=ingestion.ingestion_key,
                sheet_name=issue.sheet_name,
                row_num=issue.row_num,
                error_message=issue.error_message[:1000],
            )
        )
    ingestion.status = "FAILED"
    ingestion.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)


def process_file(
    source_path: str | Path,
    session: Session,
    landing_dir: str,
    process_adjustments: bool = False,
) -> IngestionLog:
    source = Path(source_path)
    identifier = source.stem[:120]
    landed = land_file(source, identifier, landing_dir)

    ingestion = IngestionLog(
        source_cost_set_identifier=identifier,
        source_file_path=str(landed),
        status="RECEIVED",
    )
    session.add(ingestion)
    session.commit()

    data = read_workbook(landed, process_adjustments=process_adjustments)
    issues = validate_workbook(data)
    if issues:
        _write_failures(session, ingestion, issues)
        session.commit()
        return ingestion

    lookup = SqlAlchemyDimLookup(session)
    keys, dim_issues = resolve_dims(data, lookup)
    if dim_issues or keys is None:
        _write_failures(session, ingestion, dim_issues)
        session.commit()
        return ingestion

    ingestion_key = ingestion.ingestion_key
    try:
        load_gold(session, data, keys, ingestion, source.name)
        session.commit()
    except Exception:
        session.rollback()
        ingestion = session.get(IngestionLog, ingestion_key)
        if ingestion is not None:
            _write_failures(
                session,
                ingestion,
                [
                    ValidationIssue(
                        sheet_name=None,
                        row_num=None,
                        error_type="EXCEPTION",
                        error_message="Gold load failed; transaction rolled back",
                    )
                ],
            )
            session.commit()
        raise
    return ingestion


def main(argv: list[str] | None = None) -> int:
    from src.core.config import settings

    parser = argparse.ArgumentParser(description="Ingest a cost-plan workbook")
    parser.add_argument("xlsx_path", help="Path to the Excel workbook")
    args = parser.parse_args(argv)

    engine = create_engine(settings.sql_server_connection_string)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        ingestion = process_file(
            args.xlsx_path,
            session,
            landing_dir=settings.landing_dir,
            process_adjustments=settings.process_adjustments,
        )
        print(f"{ingestion.status}: ingestionKey={ingestion.ingestion_key}")
        return 0 if ingestion.status == "COMMITTED" else 1


if __name__ == "__main__":
    sys.exit(main())
