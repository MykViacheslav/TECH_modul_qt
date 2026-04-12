from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from src.app.app_settings import load_drawing_settings
from src.core.costing.module_costs import ModuleCostBreakdown
from src.domain.assembly_models import FurnitureAssemblyDef
from src.domain.assembly_resolution_service import ResolvedAssemblyItem, resolve_assembly_items
from src.domain.project_model import (
    ProjectAssembly,
    ProjectAudit,
    ProjectHeader,
    ProjectModel,
    ProjectPricingSnapshot,
    ProjectQuoteContext,
    ProjectQuoteLine,
    ProjectServiceLine,
)


def _to_str(value: Any) -> str:
    return str(value or "").strip()


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _slug(text: str, fallback: str = "assembly") -> str:
    raw = re.sub(r"[^A-Za-z0-9]+", "_", str(text or "").strip()).strip("_").lower()
    return raw or fallback


def _cabinet_group(item: ResolvedAssemblyItem) -> str:
    kind = _to_str(getattr(item.module, "cabinet_kind", "") or "").strip().lower()
    if kind == "upper":
        return "Fronty"
    if kind == "lower":
        return "Korpus"
    return "Korpus"


def _resolved_item_to_quote_line(
    assembly: FurnitureAssemblyDef,
    item: ResolvedAssemblyItem,
    index: int,
) -> ProjectQuoteLine:
    breakdown: ModuleCostBreakdown = item.cost_breakdown
    source_ref = _to_str(getattr(item.item, "source_name", "")) or _to_str(getattr(item.item, "instance_name", ""))
    if not source_ref:
        source_ref = f"{_slug(assembly.name)}-{index + 1:03d}"
    note = f"x={float(item.x_mm):.0f} | y={float(item.y_mm):.0f}"
    return ProjectQuoteLine(
        line_id=f"{_slug(assembly.assembly_id or assembly.name)}-{index + 1:03d}",
        source_kind="assembly_module",
        source_ref=source_ref,
        group=_cabinet_group(item),
        module_name=item.display_name,
        position_name=_to_str(getattr(item.module, "name", "")) or item.display_name,
        qty=1.0,
        unit="kpl",
        length_mm=float(item.width_mm),
        width_mm=float(item.height_mm),
        thickness_mm=float(item.depth_mm),
        material_name=_to_str(getattr(item.module, "material_profile_key", "")) or _to_str(assembly.material_profile_key),
        edgeband_desc="",
        cost_material=float(breakdown.material_total_pln),
        cost_edgeband=float(breakdown.edgeband_total_pln),
        cost_labor=0.0,
        cost_extra=float(breakdown.hardware_total_pln),
        line_total=float(breakdown.grand_total_pln),
        status="OK",
        accuracy="calculated",
        note=note,
    )


def build_assembly_project_model(
    assembly: FurnitureAssemblyDef,
    catalog: Any,
    wall_store: Any,
    *,
    technical_total: float,
    base_total: float,
    sale_total: float,
    profit_total: float,
    labor_cost: float = 0.0,
    transport_cost: float = 0.0,
    montage_cost: float = 0.0,
    pricing_policy: str = "",
    policy_multiplier: float = 1.0,
    source_path: str = "",
) -> ProjectModel:
    built_at = _now_text()
    wall_name = _to_str(getattr(assembly, "wall_name", ""))
    linked_wall = wall_store.get(wall_name) if wall_name else None
    resolved_items = resolve_assembly_items(
        assembly,
        catalog,
        auto_double_front_width_mm=float(load_drawing_settings().auto_double_front_width_mm or 600.0),
        linked_wall=linked_wall,
    )

    quote_lines = [_resolved_item_to_quote_line(assembly, item, idx) for idx, item in enumerate(resolved_items)]
    service_lines = []
    if labor_cost > 0.0:
        service_lines.append(
            ProjectServiceLine(
                service_id=f"{_slug(assembly.name)}-LAB",
                service_name="Robocizna",
                source_kind="assembly_extra",
                source_ref=_slug(assembly.name),
                qty=1.0,
                unit="zl",
                amount=float(labor_cost),
                status="OK",
                note="Koszt robocizny z kompletu",
            )
        )
    if transport_cost > 0.0:
        service_lines.append(
            ProjectServiceLine(
                service_id=f"{_slug(assembly.name)}-TRN",
                service_name="Transport",
                source_kind="assembly_extra",
                source_ref=_slug(assembly.name),
                qty=1.0,
                unit="zl",
                amount=float(transport_cost),
                status="OK",
                note="Koszt transportu z kompletu",
            )
        )
    if montage_cost > 0.0:
        service_lines.append(
            ProjectServiceLine(
                service_id=f"{_slug(assembly.name)}-MON",
                service_name="Montaz",
                source_kind="assembly_extra",
                source_ref=_slug(assembly.name),
                qty=1.0,
                unit="zl",
                amount=float(montage_cost),
                status="OK",
                note="Koszt montazu z kompletu",
            )
        )

    material_total = sum(float(item.cost_breakdown.material_total_pln) for item in resolved_items)
    extras_total = float(labor_cost) + float(transport_cost) + float(montage_cost)
    project_name = _to_str(assembly.name) or "Komplet"
    assembly_id = _to_str(assembly.assembly_id) or _slug(project_name)

    return ProjectModel(
        project_id=f"assembly_{assembly_id}",
        project_name=project_name,
        project_type="assemblies_quote",
        status="active",
        created_at=built_at,
        updated_at=built_at,
        source="assembly_store_json",
        header=ProjectHeader(
            project_name=project_name,
            client_name=_to_str(assembly.client_name),
            order_code=_to_str(assembly.order_name),
            order_name=_to_str(assembly.order_name),
            status="active",
            source_kind="assembly_store_json",
            source_path=source_path,
            created_at=built_at,
            updated_at=built_at,
        ),
        quote_context=ProjectQuoteContext(
            mode="assemblies",
            pricing_policy=pricing_policy,
            margin_percent=float(assembly.margin_percent),
            vat_percent=23.0,
            transport_flat=float(transport_cost),
            montage_flat=float(montage_cost),
            labor_cost=float(labor_cost),
            policy_multiplier=policy_multiplier,
        ),
        assemblies=[
            ProjectAssembly(
                assembly_id=assembly_id,
                name=project_name,
                order_name=_to_str(assembly.order_name),
                client_name=_to_str(assembly.client_name),
                wall_name=_to_str(assembly.wall_name),
                width_mm=float(assembly.width_mm),
                height_mm=float(assembly.height_mm),
                depth_mm=float(assembly.depth_mm),
                gap_mm=float(assembly.gap_mm),
                material_profile_key=_to_str(assembly.material_profile_key),
                labor_cost_pln=float(labor_cost),
                transport_cost_pln=float(transport_cost),
                montage_cost_pln=float(montage_cost),
                margin_percent=float(assembly.margin_percent),
                items=[item.item.to_dict() for item in resolved_items if hasattr(item.item, "to_dict")],
            )
        ],
        quote_lines=quote_lines,
        services=service_lines,
        pricing_snapshot=ProjectPricingSnapshot(
            technical_total=float(technical_total),
            material_value=float(material_total),
            services_total=float(extras_total),
            extras_total=float(extras_total),
            base_total=float(base_total),
            sale_total=float(sale_total),
            brutto_total=float(sale_total),
            profit_total=float(profit_total),
            computed_at=built_at,
        ),
        audit=ProjectAudit(
            built_from=[
                "assembly_store_json",
                "order_store_json",
                "assembly_resolution_service",
                "catalog_store_json",
                "wall_store_json",
            ],
            built_at=built_at,
            source_versions=[
                "tab_wycena",
                "resolve_assembly_items",
            ],
            adapter_name="AssemblyProjectAdapter",
            notes="Read-only snapshot for the system quote workflow.",
        ),
    )
