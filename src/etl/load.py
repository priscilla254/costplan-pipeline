"""Write gold rows from resolved keys. Does not look up labels."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from src.etl.dto import ResolvedKeys, WorkbookData
from src.etl.excel.text import cost_set_identifier, normalize_text
from src.schema.tables import (
    DimCostSet,
    DimProject,
    FactCostAdjustment,
    FactCostSetProjectQuant,
    FactElementCostL2,
    FactElementQuantL2,
    FactLineItemL3,
    IngestionLog,
)


def _as_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def load_gold(
    session: Session,
    data: WorkbookData,
    keys: ResolvedKeys,
    ingestion: IngestionLog,
    source_file_name: str,
) -> DimCostSet:
    header = data.header
    project_id = keys.project_id
    identifier = cost_set_identifier(
        project_id,
        header.selected_contractor or "",
        header.cost_stage,
    )

    project = (
        session.query(DimProject)
        .filter(DimProject.project_number == project_id)
        .one_or_none()
    )
    if project is None:
        project = DimProject(
            project_number=project_id,
            project_name=header.project_name or project_id,
            location_key=keys.location_key,
            sector_key=keys.sector_key,
            demolition=header.demolition,
            site_type=header.site_type,
            new_build=header.new_build,
            refurbishment=header.refurbishment,
            horizontal_extension=header.horizontal_extension,
            vertical_extension=header.vertical_extension,
            nr_of_storeys=header.nr_of_storeys,
            spec_level=header.spec_level,
            basement=header.basement,
            asbestos=header.asbestos,
            contamination=header.contamination,
            complexity_rating=header.complexity_rating,
            access_constraints=header.access_constraints,
            occupied=header.occupied,
        )
        session.add(project)
        session.flush()
    else:
        project.project_name = header.project_name or project.project_name
        project.location_key = keys.location_key
        project.sector_key = keys.sector_key

    prior = (
        session.query(DimCostSet)
        .filter(
            DimCostSet.project_key == project.project_key,
            DimCostSet.contractor_key == keys.contractor_key,
            DimCostSet.cost_stage == header.cost_stage,
            DimCostSet.is_current.is_(True),
        )
        .one_or_none()
    )
    if prior is not None:
        prior.is_current = False

    currency = (header.currency or "GBP")[:3]
    cost_set = DimCostSet(
        project_key=project.project_key,
        cost_stage=header.cost_stage,
        source_cost_set_identifier=identifier,
        contractor_key=keys.contractor_key,
        is_selected_contractor=True,
        data_status=header.data_status or "Loaded",
        base_date=_as_date(header.base_date),
        currency=currency,
        programme_length_in_weeks=header.programme_length_in_weeks,
        programme_type=header.programme_type,
        gifa=header.gifa,
        prelims_included=None,
        prof_fees_included=None,
        source_file=source_file_name[:260],
        is_current=True,
    )
    session.add(cost_set)
    session.flush()

    seen_l2: set[int] = set()
    for cost in data.l2_costs:
        if not cost.l2_code or cost.total_cost is None:
            continue
        l2_key = keys.element_l2_by_code.get(normalize_text(cost.l2_code))
        if l2_key is None or l2_key in seen_l2:
            continue
        seen_l2.add(l2_key)
        session.add(
            FactElementCostL2(
                cost_set_key=cost_set.cost_set_key,
                element_l2_key=l2_key,
                total_cost=cost.total_cost.quantize(Decimal("0.01")),
            )
        )

    for item in data.line_items:
        if not item.l2_code:
            continue
        l2_key = keys.element_l2_by_code.get(normalize_text(item.l2_code))
        if l2_key is None:
            continue
        session.add(
            FactLineItemL3(
                cost_set_key=cost_set.cost_set_key,
                element_l2_key=l2_key,
                display_order=item.display_order,
                item_description=item.item_description,
                quantity=item.quantity,
                unit=item.unit,
                rate=item.rate,
                total_cost=item.total_cost,
                row_type=item.row_type,
            )
        )

    seen_project_quants: set[int] = set()
    for quant in data.project_quants:
        if quant.qty is None:
            continue
        label = quant.quant_type_code or quant.quant_type_name
        if not label:
            continue
        q_key = keys.quant_type_by_code.get(normalize_text(label))
        if q_key is None and quant.quant_type_name:
            q_key = keys.quant_type_by_code.get(normalize_text(quant.quant_type_name))
        if q_key is None or q_key in seen_project_quants:
            continue
        seen_project_quants.add(q_key)
        unit = (quant.unit or "nr")[:20]
        session.add(
            FactCostSetProjectQuant(
                cost_set_key=cost_set.cost_set_key,
                quant_type_key=q_key,
                qty=quant.qty,
                unit=unit,
                comment=quant.comment,
            )
        )

    for quant in data.element_quants:
        if not quant.l2_code or quant.qty is None:
            continue
        l2_key = keys.element_l2_by_code.get(normalize_text(quant.l2_code))
        q_key = keys.quant_type_by_code.get(normalize_text(quant.quant_type_code))
        if l2_key is None or q_key is None:
            continue
        session.add(
            FactElementQuantL2(
                cost_set_key=cost_set.cost_set_key,
                element_l2_key=l2_key,
                quant_type_key=q_key,
                qty=quant.qty,
                unit=quant.unit,
                comment=quant.comment,
            )
        )

    for adj in data.adjustments:
        adj_key = keys.adj_type_by_pair.get((adj.adj_category, adj.adj_sub_type))
        if adj_key is None:
            continue
        session.add(
            FactCostAdjustment(
                cost_set_key=cost_set.cost_set_key,
                adjustment_type_key=adj_key,
                amount=adj.amount,
                method=adj.method,
                rate_percent=adj.rate_percent,
                applied_to_base=adj.applied_to_base if adj.applied_to_base is not None else True,
                included_in_comparison=(
                    adj.included_in_comparison
                    if adj.included_in_comparison is not None
                    else True
                ),
            )
        )

    ingestion.source_cost_set_identifier = identifier
    ingestion.cost_set_key = cost_set.cost_set_key
    ingestion.status = "COMMITTED"
    ingestion.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    return cost_set
