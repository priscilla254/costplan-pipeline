# costplan-pipeline

ETL for cost-plan workbooks. Excel files are parsed into in-memory DTOs, validated, resolved against reference dimensions, and loaded into a SQL Server star schema. The same schema is intended to move to a cloud database later.

Parsers never import ORM models. Gold load happens only after validation and dimension lookup succeed.

## How ingest works

```text
.xlsx
  → copy to data/landing/{identifier}/{UTC}_{filename}
  → IngestionLog RECEIVED
  → parse sheets → validate → resolve dim keys
  → load gold (one transaction)
  → COMMITTED  or  FAILED + StagingValidationError rows
```

Workbook tabs are classified by alias (`Project Information - 1`, NRM L3 sheets, and so on). Required base sheets are project information, project quants, L2 element quants, and summary. Adjustments are off unless `PROCESS_ADJUSTMENTS=true`.

`DimCostSet` grain is project + contractor + cost stage. A re-upload of the same grain sets the previous row `isCurrent = 0` and inserts a new current row. `SourceCostSetIdentifier` is the lineage string `projectId|normalizedContractor|normalizedCostStage`.

Sectors, locations, contractors, L2 elements, and quant types are **lookup-only**. Ingest will not create them. Seed those tables before loading a workbook.

## Layout

| Path | Role |
| --- | --- |
| `src/etl/` | Classify, parse, validate, resolve, land, load |
| `src/schema/tables.py` | SQLAlchemy 2.0 star schema |
| `src/schema/migrations/` | Alembic (`script_location` in `alembic.ini`) |
| `src/core/config.py` | Settings from `.env` |
| `tests/etl/` | Parser, validate, resolve, landing tests (no SQL) |
| `tests/data/` | Sample workbooks |

## Setup

Python 3.12+, [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) if you will connect to SQL Server.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

```text
SQL_SERVER_CONNECTION_STRING=mssql+pyodbc://SERVER/DATABASE?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes
LANDING_DIR=data/landing
PROCESS_ADJUSTMENTS=false
```

Named instance example (`SERVER\INSTANCE`): encode the backslash as `%5C`.

```text
mssql+pyodbc://HOST%5CINSTANCE/DATABASE?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes
```

If `Get-OdbcDriver` lists Driver 17 instead of 18, change the `driver=` query parameter to match. `.env` is gitignored; do not commit credentials.

## Tests

Parser and dimension tests do not need a database:

```powershell
pytest tests/etl
```

Fixture workbook: `tests/data/Elm_Court_Residential_Cost_Comparison_Anonymised.xlsx`.

## Apply schema (when SQL Server is reachable)

Alembic reads `SQL_SERVER_CONNECTION_STRING`. There are no revisions under `src/schema/migrations/versions/` until you generate one.

```powershell
alembic revision --autogenerate -m "Initial star schema"
alembic upgrade head
```

Seed reference dimensions (sector, location, contractor, NRM L2, quant type) so labels in the workbook match rows in those tables.

## Ingest a workbook

Requires a live SQL Server with schema and seeded dims:

```powershell
python -m src.etl.run path\to\workbook.xlsx
```

Prints `COMMITTED` or `FAILED` and the `ingestionKey`. Landed copies go under `data/landing/` (gitignored).
