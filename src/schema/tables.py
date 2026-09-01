"""SQLAlchemy ORM models for the cost-plan star schema.

Python attributes use snake_case. SQL column names match the Azure SQL
schema (mixed camelCase / PascalCase) via the first argument to
``mapped_column``.

Conventions:
- Surrogate keys are ``INT IDENTITY(1,1)`` unless noted.
- ``BIT``: 1 is True, 0 is False. Active flags default to 1.
- Foreign keys are indexed unless they are already the leading column of
  a primary key or unique constraint.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    Date,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
    BigInteger,
)
from sqlalchemy.dialects.mssql import BIT, DATETIME2
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base shared by every table in this module."""

    pass


# ---------------------------------------------------------------------------
# Core project dimensions
# ---------------------------------------------------------------------------


class DimSector(Base):
    """Lookup of project sectors (e.g. residential, education)."""

    __tablename__ = "DimSector"
    __table_args__ = (UniqueConstraint("sectorCode", name="UQ_DimSector_sectorCode"),)

    sector_key: Mapped[int] = mapped_column(
        "sectorKey",
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    sector_code: Mapped[str] = mapped_column("sectorCode", String(50), nullable=False)
    sector_name: Mapped[str] = mapped_column("sectorName", String(200), nullable=False)
    sort_order: Mapped[int | None] = mapped_column("sortOrder", Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        "isActive",
        BIT,
        nullable=False,
        server_default=text("1"),
    )


class DimLocation(Base):
    """Geographic location used for location-factor lookups."""

    __tablename__ = "DimLocation"
    __table_args__ = (UniqueConstraint("DisplayLabel", name="UQ_DimLocation_DisplayLabel"),)

    location_key: Mapped[int] = mapped_column(
        "locationKey",
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    country: Mapped[str] = mapped_column("country", String(100), nullable=False)
    region: Mapped[str | None] = mapped_column("region", String(150), nullable=True)
    # Unique when present; SQL Server still allows multiple NULLs.
    display_label: Mapped[str | None] = mapped_column(
        "DisplayLabel", String(150), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        "isActive",
        BIT,
        nullable=False,
        server_default=text("1"),
    )


class DimProject(Base):
    """Project master record: identity, location/sector, and site characteristics."""

    __tablename__ = "DimProject"
    __table_args__ = (UniqueConstraint("projectID", name="UQ_DimProject_projectID"),)

    project_key: Mapped[int] = mapped_column(
        "projectKey",
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    project_number: Mapped[str] = mapped_column("projectID", String(50), nullable=False)
    project_name: Mapped[str] = mapped_column("projectName", String(250), nullable=False)

    location_key: Mapped[int] = mapped_column(
        "LocationKey",
        Integer,
        ForeignKey("DimLocation.locationKey"),
        nullable=False,
        index=True,
    )
    sector_key: Mapped[int] = mapped_column(
        "SectorKey",
        Integer,
        ForeignKey("DimSector.sectorKey"),
        nullable=False,
        index=True,
    )
    demolition: Mapped[bool | None] = mapped_column("Demolition", BIT, nullable=True)
    site_type: Mapped[str | None] = mapped_column("siteType", String(100), nullable=True)
    new_build: Mapped[bool | None] = mapped_column("newBuild", BIT, nullable=True)
    refurbishment: Mapped[bool | None] = mapped_column("Refurbishment", BIT, nullable=True)
    horizontal_extension: Mapped[bool | None] = mapped_column(
        "horizontalExtension", BIT, nullable=True
    )
    vertical_extension: Mapped[bool | None] = mapped_column(
        "verticalExtension", BIT, nullable=True
    )
    nr_of_storeys: Mapped[int | None] = mapped_column("NrOfStoreys", Integer, nullable=True)
    spec_level: Mapped[str | None] = mapped_column("SpecLevel", String(50), nullable=True)
    total_height_ground_to_roof: Mapped[Decimal | None] = mapped_column(
        "totalHeightGroundToRoof",
        Numeric(18, 4),
        nullable=True,
    )
    basement: Mapped[bool | None] = mapped_column("Basement", BIT, nullable=True)
    basement_area: Mapped[Decimal | None] = mapped_column(
        "BasementArea", Numeric(18, 4), nullable=True
    )
    basement_height: Mapped[Decimal | None] = mapped_column(
        "BasementHeight", Numeric(18, 4), nullable=True
    )
    asbestos: Mapped[bool | None] = mapped_column("Asbestos", BIT, nullable=True)
    contamination: Mapped[bool | None] = mapped_column("Contamination", BIT, nullable=True)
    ground_conditions: Mapped[str | None] = mapped_column(
        "groundConditions", String(100), nullable=True
    )
    complexity_rating: Mapped[int | None] = mapped_column(
        "ComplexityRating", Integer, nullable=True
    )
    access_constraints: Mapped[str | None] = mapped_column(
        "accessConstraints", String(500), nullable=True
    )
    occupied: Mapped[bool | None] = mapped_column("occupied", BIT, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt",
        DATETIME2(0),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        "updatedAt", DATETIME2(0), nullable=True
    )


class DimContractor(Base):
    """Contractor submitting a cost set against a project."""

    __tablename__ = "DimContractor"
    __table_args__ = (
        UniqueConstraint("contractorName", name="UQ_DimContractor_contractorName"),
    )

    contractor_key: Mapped[int] = mapped_column(
        "contractorKey",
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    contractor_name: Mapped[str] = mapped_column(
        "contractorName", String(250), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        "IsActive",
        BIT,
        nullable=False,
        server_default=text("1"),
    )
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt",
        DATETIME2(0),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        "UpdatedAt", DATETIME2(0), nullable=True
    )


class DimCostSet(Base):
    """One cost submission for a project, contractor, and cost stage.

    Re-uploads of the same source file are keyed by ``SourceCostSetIdentifier``.
    ``isCurrent`` marks the active submission for that combination.
    """

    __tablename__ = "DimCostSet"
    __table_args__ = (
        UniqueConstraint(
            "SourceCostSetIdentifier", name="UQ_DimCostSet_SourceCostSetIdentifier"
        ),
    )

    cost_set_key: Mapped[int] = mapped_column(
        "CostSetKey",
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    project_key: Mapped[int] = mapped_column(
        "projectKey",
        Integer,
        ForeignKey("DimProject.projectKey"),
        nullable=False,
        index=True,
    )
    cost_stage: Mapped[str | None] = mapped_column(
        "CostStage", String(50), nullable=True
    )
    # Idempotency key so the same source file is not ingested twice.
    source_cost_set_identifier: Mapped[str] = mapped_column(
        "SourceCostSetIdentifier", String(120), nullable=False
    )
    contractor_key: Mapped[int] = mapped_column(
        "contractorKey",
        Integer,
        ForeignKey("DimContractor.contractorKey"),
        nullable=False,
        index=True,
    )
    # When True, this contractor's figures feed the benchmark.
    is_selected_contractor: Mapped[bool] = mapped_column(
        "isSelectedContractor",
        BIT,
        nullable=False,
        server_default=text("1"),
    )
    data_status: Mapped[str] = mapped_column("dataStatus", String(20), nullable=False)
    # Used at query time to pick the matching inflation index period.
    base_date: Mapped[date | None] = mapped_column("baseDate", Date, nullable=True)
    currency: Mapped[str] = mapped_column("Currency", CHAR(3), nullable=False)
    programme_length_in_weeks: Mapped[int | None] = mapped_column(
        "programmeLengthInWeeks", Integer, nullable=True
    )
    programme_type: Mapped[str | None] = mapped_column(
        "programmeType", String(50), nullable=True
    )
    # High-frequency metric kept as a dedicated column rather than EAV.
    gifa: Mapped[Decimal | None] = mapped_column("GIFA", Numeric(18, 4), nullable=True)
    bcis_q_date: Mapped[date | None] = mapped_column("BCISQDate", Date, nullable=True)
    prelims_included: Mapped[bool | None] = mapped_column(
        "prelimsIncluded", BIT, nullable=True
    )
    prof_fees_included: Mapped[bool | None] = mapped_column(
        "profFeesIncluded", BIT, nullable=True
    )
    source_file: Mapped[str | None] = mapped_column(
        "sourceFile", String(260), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        "uploadedAt",
        DATETIME2(0),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )
    is_current: Mapped[bool] = mapped_column(
        "isCurrent",
        BIT,
        nullable=False,
        server_default=text("1"),
    )


# ---------------------------------------------------------------------------
# Element classification and quantity rules
# ---------------------------------------------------------------------------


class DimQuantType(Base):
    """Quantity type, e.g. M2, GIFA, KEYS.

    ``Element`` is organisational only ('Element' or 'Project') and is not
    enforced as a check constraint.
    """

    __tablename__ = "DimQuantType"
    __table_args__ = (
        UniqueConstraint("QuantTypeCode", name="UQ_DimQuantType_QuantTypeCode"),
    )

    quant_type_key: Mapped[int] = mapped_column(
        "QuantTypeKey",
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    quant_type_code: Mapped[str] = mapped_column(
        "QuantTypeCode", String(50), nullable=False
    )
    quant_type_name: Mapped[str] = mapped_column(
        "QuantTypeName", String(200), nullable=False
    )
    default_unit: Mapped[str | None] = mapped_column(
        "DefaultUnit", String(50), nullable=True
    )
    scope: Mapped[str | None] = mapped_column("Element", String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        "IsActive",
        BIT,
        nullable=False,
        server_default=text("1"),
    )
    sort_order: Mapped[int | None] = mapped_column("SortOrder", Integer, nullable=True)


class DimElementSystem(Base):
    """Element breakdown standard, e.g. NRM or AIQS."""

    __tablename__ = "DimElementSystem"
    __table_args__ = (
        UniqueConstraint("SystemName", name="UQ_DimElementSystem_SystemName"),
    )

    element_system_key: Mapped[int] = mapped_column(
        "ElementSystemKey",
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    system_name: Mapped[str] = mapped_column("SystemName", String(100), nullable=False)
    country: Mapped[str | None] = mapped_column("Country", String(50), nullable=True)
    country_code: Mapped[str] = mapped_column("CountryCode", CHAR(2), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        "IsActive",
        BIT,
        nullable=False,
        server_default=text("1"),
    )


class DimElementL2(Base):
    """Level-2 element within an element system (L1 parent + L2 child codes)."""

    __tablename__ = "DimElementL2"

    element_l2_key: Mapped[int] = mapped_column(
        "elementL2key",
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    element_system_key: Mapped[int] = mapped_column(
        "ElementSystemKey",
        Integer,
        ForeignKey("DimElementSystem.ElementSystemKey"),
        nullable=False,
        index=True,
    )
    default_quant_type_key: Mapped[int | None] = mapped_column(
        "DefaultQuantTypeKey",
        Integer,
        ForeignKey("DimQuantType.QuantTypeKey"),
        nullable=True,
        index=True,
    )
    l1_code: Mapped[str] = mapped_column("L1Code", String(50), nullable=False)
    l1_name: Mapped[str] = mapped_column("L1Name", String(200), nullable=False)
    l2_code: Mapped[str] = mapped_column("L2Code", String(50), nullable=False)
    l2_name: Mapped[str] = mapped_column("L2Name", String(200), nullable=False)
    country_code: Mapped[str] = mapped_column("CountryCode", CHAR(2), nullable=False)
    sort_order: Mapped[int | None] = mapped_column("SortOrder", Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        "IsActive",
        BIT,
        nullable=False,
        server_default=text("1"),
    )


class DimElementQuantRule(Base):
    """Which quantity types are valid for a given L2 element.

    Composite PK: one row per (element, quantity type). ``QuantTypeKey`` is
    indexed separately because it is the second PK column.
    """

    __tablename__ = "DimElementQuantRule"

    element_l2_key: Mapped[int] = mapped_column(
        "ElementL2Key",
        Integer,
        ForeignKey("DimElementL2.elementL2key"),
        primary_key=True,
    )
    quant_type_key: Mapped[int] = mapped_column(
        "QuantTypeKey",
        Integer,
        ForeignKey("DimQuantType.QuantTypeKey"),
        primary_key=True,
        index=True,
    )
    unit: Mapped[str | None] = mapped_column("Unit", String(50), nullable=True)
    rule_description: Mapped[str | None] = mapped_column(
        "RuleDescription", String(500), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        "IsActive",
        BIT,
        nullable=False,
        server_default=text("1"),
    )
    sort_order: Mapped[int | None] = mapped_column("SortOrder", Integer, nullable=True)
    country_code: Mapped[str] = mapped_column("CountryCode", CHAR(2), nullable=False)


class DimSectorQuantRule(Base):
    """Which quantity types are valid for a given sector.

    Composite PK: one row per (sector, quantity type).
    """

    __tablename__ = "DimSectorQuantRule"

    sector_key: Mapped[int] = mapped_column(
        "SectorKey",
        Integer,
        ForeignKey("DimSector.sectorKey"),
        primary_key=True,
    )
    quant_type_key: Mapped[int] = mapped_column(
        "QuantTypeKey",
        Integer,
        ForeignKey("DimQuantType.QuantTypeKey"),
        primary_key=True,
        index=True,
    )
    unit: Mapped[str | None] = mapped_column("Unit", String(50), nullable=True)
    rule_description: Mapped[str | None] = mapped_column(
        "RuleDescription", String(500), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        "IsActive",
        BIT,
        nullable=False,
        server_default=text("1"),
    )
    sort_order: Mapped[int | None] = mapped_column("SortOrder", Integer, nullable=True)


# ---------------------------------------------------------------------------
# Inflation, location factors, and adjustment types
# ---------------------------------------------------------------------------


class DimAdjustmentType(Base):
    """Category/subtype of a cost adjustment (prelims, risk, inflation, etc.)."""

    __tablename__ = "DimAdjustmentType"
    __table_args__ = (
        UniqueConstraint(
            "adjCategory",
            "adjSubType",
            name="UQ_DimAdjustmentType_adjCategory_adjSubType",
        ),
    )

    adj_type_key: Mapped[int] = mapped_column(
        "adjTypeKey",
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    adj_category: Mapped[str] = mapped_column("adjCategory", String(100), nullable=False)
    adj_sub_type: Mapped[str | None] = mapped_column(
        "adjSubType", String(150), nullable=True
    )


class DimTPI(Base):
    """Tender Price Index series used to inflate/deflate costs.

    ``Frequency`` is typically 'Quarterly'.
    """

    __tablename__ = "DimTPI"
    __table_args__ = (UniqueConstraint("TPICode", name="UQ_DimTPI_TPICode"),)

    tpi_key: Mapped[int] = mapped_column(
        "TPIKey",
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    tpi_code: Mapped[str] = mapped_column("TPICode", String(50), nullable=False)
    tpi_name: Mapped[str] = mapped_column("TPIName", String(200), nullable=False)
    provider: Mapped[str | None] = mapped_column("Provider", String(100), nullable=True)
    country_code: Mapped[str] = mapped_column("CountryCode", CHAR(2), nullable=False)
    frequency: Mapped[str] = mapped_column("Frequency", String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        "IsActive",
        BIT,
        nullable=False,
        server_default=text("1"),
    )


class DimIndexValue(Base):
    """Published index value for a TPI series on a given date.

    ``IndexDate`` is the quarter-end date. Unique on (TPIKey, IndexDate),
    which also indexes the TPI foreign key.
    """

    __tablename__ = "DimIndexValue"
    __table_args__ = (
        UniqueConstraint("TPIKey", "IndexDate", name="UQ_DimIndexValue_TPIKey_IndexDate"),
    )

    index_value_key: Mapped[int] = mapped_column(
        "IndexValueKey",
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    tpi_key: Mapped[int] = mapped_column(
        "TPIKey",
        Integer,
        ForeignKey("DimTPI.TPIKey"),
        nullable=False,
    )
    index_date: Mapped[date] = mapped_column("IndexDate", Date, nullable=False)
    index_value: Mapped[Decimal] = mapped_column(
        "IndexValue", Numeric(12, 4), nullable=False
    )


class DimLocationFactor(Base):
    """Location-factor series (provider, country, and base location)."""

    __tablename__ = "DimLocationFactor"
    __table_args__ = (
        UniqueConstraint(
            "LocationFactorCode", name="UQ_DimLocationFactor_LocationFactorCode"
        ),
    )

    location_factor_key: Mapped[int] = mapped_column(
        "LocationFactorKey",
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    location_factor_code: Mapped[str] = mapped_column(
        "LocationFactorCode", String(50), nullable=False
    )
    location_factor_name: Mapped[str] = mapped_column(
        "LocationFactorName", String(200), nullable=False
    )
    provider: Mapped[str] = mapped_column("Provider", String(100), nullable=False)
    country_code: Mapped[str] = mapped_column("CountryCode", CHAR(2), nullable=False)
    base_location_label: Mapped[str | None] = mapped_column(
        "BaseLocationLabel", String(100), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        "IsActive",
        BIT,
        nullable=False,
        server_default=text("1"),
    )


class DimLocationFactorValue(Base):
    """Factor value for a location within a dated effective range."""

    __tablename__ = "DimLocationFactorValue"

    location_factor_value_key: Mapped[int] = mapped_column(
        "LocationFactorValueKey",
        Integer,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    location_factor_key: Mapped[int] = mapped_column(
        "LocationFactorKey",
        Integer,
        ForeignKey("DimLocationFactor.LocationFactorKey"),
        nullable=False,
        index=True,
    )
    location_key: Mapped[int] = mapped_column(
        "LocationKey",
        Integer,
        ForeignKey("DimLocation.locationKey"),
        nullable=False,
        index=True,
    )
    factor_value: Mapped[Decimal] = mapped_column(
        "FactorValue", Numeric(10, 4), nullable=False
    )
    effective_from_date: Mapped[date] = mapped_column(
        "EffectiveFromDate", Date, nullable=False
    )
    effective_to_date: Mapped[date | None] = mapped_column(
        "EffectiveToDate", Date, nullable=True
    )


# ---------------------------------------------------------------------------
# Fact tables (measures keyed by cost set)
# ---------------------------------------------------------------------------


class FactElementCostL2(Base):
    """Rolled-up L2 element cost for a cost set.

    Composite PK: one total per (cost set, L2 element).
    """

    __tablename__ = "FactElementCostL2"

    cost_set_key: Mapped[int] = mapped_column(
        "CostSetKey",
        Integer,
        ForeignKey("DimCostSet.CostSetKey"),
        primary_key=True,
    )
    element_l2_key: Mapped[int] = mapped_column(
        "elementL2key",
        Integer,
        ForeignKey("DimElementL2.elementL2key"),
        primary_key=True,
        index=True,
    )
    total_cost: Mapped[Decimal] = mapped_column(
        "TotalCost", Numeric(18, 2), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt",
        DATETIME2(0),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )
    comment: Mapped[str | None] = mapped_column("Comment", String(500), nullable=True)


class FactLineItemL3(Base):
    """Individual L3 line item under an L2 element within a cost set."""

    __tablename__ = "factLineItem_L3"

    line_item_key: Mapped[int] = mapped_column(
        "LineItemKey",
        BigInteger,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    cost_set_key: Mapped[int] = mapped_column(
        "CostSetKey",
        Integer,
        ForeignKey("DimCostSet.CostSetKey"),
        nullable=False,
        index=True,
    )
    element_l2_key: Mapped[int] = mapped_column(
        "elementL2key",
        Integer,
        ForeignKey("DimElementL2.elementL2key"),
        nullable=False,
        index=True,
    )
    line_id: Mapped[str | None] = mapped_column("LineID", String(50), nullable=True)
    display_order: Mapped[int] = mapped_column("DisplayOrder", Integer, nullable=False)
    item_description: Mapped[str | None] = mapped_column(
        "itemDescription", String(500), nullable=True
    )
    quantity: Mapped[Decimal | None] = mapped_column(
        "Quantity", Numeric(18, 4), nullable=True
    )
    unit: Mapped[str | None] = mapped_column("Unit", String(50), nullable=True)
    rate: Mapped[Decimal | None] = mapped_column("Rate", Numeric(18, 4), nullable=True)
    total_cost: Mapped[Decimal | None] = mapped_column(
        "totalCost", Numeric(18, 2), nullable=True
    )
    row_type: Mapped[str] = mapped_column("RowType", String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt",
        DATETIME2(0),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )


class FactCostSetSummary(Base):
    """Headline totals for a cost set (one row per submission)."""

    __tablename__ = "FactCostSetSummary"

    cost_set_key: Mapped[int] = mapped_column(
        "CostSetKey",
        Integer,
        ForeignKey("DimCostSet.CostSetKey"),
        primary_key=True,
    )
    measured_works_total: Mapped[Decimal | None] = mapped_column(
        "measuredWorksTotal", Numeric(18, 2), nullable=True
    )
    building_works_estimate: Mapped[Decimal | None] = mapped_column(
        "buildingWorksEstimate", Numeric(18, 2), nullable=True
    )
    total_incl_risk: Mapped[Decimal | None] = mapped_column(
        "totalInclRisk", Numeric(18, 2), nullable=True
    )
    total_incl_inflation: Mapped[Decimal | None] = mapped_column(
        "totalInclInflation", Numeric(18, 2), nullable=True
    )
    grand_total: Mapped[Decimal | None] = mapped_column(
        "grandTotal", Numeric(18, 2), nullable=True
    )


class FactCostAdjustment(Base):
    """Adjustment applied to a cost set (amount and/or rate).

    Composite PK: one row per (cost set, adjustment type).
    """

    __tablename__ = "FactCostAdjustment"

    cost_set_key: Mapped[int] = mapped_column(
        "CostSetKey",
        Integer,
        ForeignKey("DimCostSet.CostSetKey"),
        primary_key=True,
    )
    adjustment_type_key: Mapped[int] = mapped_column(
        "adjustmentTypeKey",
        Integer,
        ForeignKey("DimAdjustmentType.adjTypeKey"),
        primary_key=True,
        index=True,
    )
    amount: Mapped[Decimal | None] = mapped_column(
        "Amount", Numeric(18, 2), nullable=True
    )
    method: Mapped[str | None] = mapped_column("Method", String(20), nullable=True)
    rate_percent: Mapped[Decimal | None] = mapped_column(
        "RatePercent", Numeric(9, 4), nullable=True
    )
    applied_to_base: Mapped[bool] = mapped_column(
        "appliedToBase",
        BIT,
        nullable=False,
        server_default=text("1"),
    )
    included_in_comparison: Mapped[bool] = mapped_column(
        "includedInComparison",
        BIT,
        nullable=False,
        server_default=text("1"),
    )


class FactCostSetProjectQuant(Base):
    """Project-level quantity for a cost set (GIFA, keys, etc.).

    Composite PK: one quantity per (cost set, quantity type).
    """

    __tablename__ = "FactCostSetProjectQuant"

    cost_set_key: Mapped[int] = mapped_column(
        "CostSetKey",
        Integer,
        ForeignKey("DimCostSet.CostSetKey"),
        primary_key=True,
    )
    quant_type_key: Mapped[int] = mapped_column(
        "QuantTypeKey",
        Integer,
        ForeignKey("DimQuantType.QuantTypeKey"),
        primary_key=True,
        index=True,
    )
    qty: Mapped[Decimal] = mapped_column("qty", Numeric(18, 2), nullable=False)
    unit: Mapped[str] = mapped_column("unit", String(20), nullable=False)
    comment: Mapped[str | None] = mapped_column("comment", String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt",
        DATETIME2(0),
        nullable=False,
        server_default=func.sysutcdatetime(),
    )


class FactElementQuantL2(Base):
    """L2 element quantity for a cost set.

    Composite PK: one quantity per (cost set, L2 element, quantity type).
    """

    __tablename__ = "FactElementQuantL2"

    cost_set_key: Mapped[int] = mapped_column(
        "CostSetKey",
        Integer,
        ForeignKey("DimCostSet.CostSetKey"),
        primary_key=True,
    )
    element_l2_key: Mapped[int] = mapped_column(
        "elementL2key",
        Integer,
        ForeignKey("DimElementL2.elementL2key"),
        primary_key=True,
    )
    quant_type_key: Mapped[int] = mapped_column(
        "QuantTypeKey",
        Integer,
        ForeignKey("DimQuantType.QuantTypeKey"),
        primary_key=True,
        index=True,
    )
    qty: Mapped[Decimal] = mapped_column("qty", Numeric(18, 4), nullable=False)
    unit: Mapped[str | None] = mapped_column("Unit", String(50), nullable=True)
    comment: Mapped[str | None] = mapped_column("comment", String(500), nullable=True)

