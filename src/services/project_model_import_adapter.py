from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from src.domain.project_model import (
    ProjectAudit,
    ProjectHeader,
    ProjectImport3D,
    ProjectMapping,
    ProjectModel,
    ProjectPricingSnapshot,
    ProjectQuoteContext,
    ProjectQuoteLine,
    ProjectServiceLine,
)
from src.services.constructor_3dc_quote_import_service import (
    Constructor3dcQuoteImportData,
)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return float(default)


def _to_str(value: Any) -> str:
    return str(value or "").strip()


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _slug(text: str, fallback: str = "import_3d") -> str:
    raw = re.sub(r"[^A-Za-z0-9]+", "_", str(text or "").strip()).strip("_").lower()
    return raw or fallback


def _source_kind_from_section(section: str) -> str:
    if section == "Formatka":
        return "import_3d_formatka"
    if section == "Front":
        return "import_3d_front"
    if section == "Okucie":
        return "import_3d_okucie"
    if section == "Lacznik":
        return "import_3d_lacznik"
    if section == "Operacja":
        return "import_3d_operacja"
    return "import_3d"


def _group_from_section(section: str) -> str:
    if section == "Formatka":
        return "Korpus"
    if section == "Front":
        return "Fronty"
    if section == "Okucie":
        return "Okucia"
    if section == "Lacznik":
        return "Laczniki"
    if section == "Operacja":
        return "Operacje"
    return "Inne"


def build_import_3d_project_model(
    import_data: Constructor3dcQuoteImportData,
    pricing_rows: list[dict[str, Any]],
    mapping_payload: dict[str, dict[str, str]] | None = None,
    *,
    source_path: str = "",
    pricing_policy: str = "",
    policy_multiplier: float = 1.0,
) -> ProjectModel:
    if import_data is None:
        raise ValueError("import_data is required")
    mapping_payload = dict(mapping_payload or {})

    summary = import_data.summary
    project_name = _to_str(summary.project_name) or _to_str(summary.module_name) or "Import 3D"
    project_id = f"import3d_{_slug(project_name)}"
    built_at = _now_text()

    quote_lines: list[ProjectQuoteLine] = []
    service_lines: list[ProjectServiceLine] = []
    total_material = 0.0
    total_edge = 0.0
    total_labor = 0.0
    total_extra = 0.0

    for idx, row in enumerate(pricing_rows):
        if not isinstance(row, dict):
            continue

        section = _to_str(row.get("section", ""))
        group = _to_str(row.get("group", "")) or _group_from_section(section)
        position_name = _to_str(row.get("name", "")) or f"Pozycja {idx + 1}"
        source_ref = _to_str(row.get("note", "")) or f"IMP{idx + 1:03d}"
        source_text = _to_str(row.get("source", "")) or f"Import 3D / {project_name}"
        qty = _to_float(row.get("qty", 1.0), 1.0)
        if qty <= 0.0:
            qty = 1.0

        material_cost = _to_float(row.get("material_cost", 0.0))
        edge_cost = _to_float(row.get("edge_cost", 0.0))
        labor_cost = _to_float(row.get("labor_cost", 0.0))
        extra_cost = _to_float(row.get("extra_cost", 0.0))
        line_total = _to_float(row.get("sum", 0.0))
        if line_total <= 0.0:
            line_total = material_cost + edge_cost + labor_cost + extra_cost

        total_material += material_cost
        total_edge += edge_cost
        total_labor += labor_cost
        total_extra += extra_cost

        quote_lines.append(
            ProjectQuoteLine(
                line_id=f"{project_id}-{idx + 1:03d}",
                source_kind=_source_kind_from_section(section),
                source_ref=source_ref,
                group=group,
                module_name=_to_str(summary.module_name) or project_name,
                position_name=position_name,
                qty=qty,
                unit="szt",
                length_mm=_to_float(row.get("length", 0.0)),
                width_mm=_to_float(row.get("width", 0.0)),
                thickness_mm=_to_float(row.get("thickness", 0.0)),
                material_name=_to_str(row.get("material", "")),
                edgeband_desc="",
                cost_material=material_cost,
                cost_edgeband=edge_cost,
                cost_labor=labor_cost,
                cost_extra=extra_cost,
                line_total=line_total,
                status=_to_str(row.get("status", "")) or "OK",
                accuracy="snapshot",
                note=source_ref,
            )
        )

        if group in {"Okucia", "Laczniki", "Operacje"}:
            service_lines.append(
                ProjectServiceLine(
                    service_id=f"{project_id}-SRV-{idx + 1:03d}",
                    service_name=position_name,
                    source_kind="import_3d",
                    source_ref=source_ref,
                    qty=qty,
                    unit="szt",
                    amount=line_total,
                    status=_to_str(row.get("status", "")) or "OK",
                    note=source_text,
                )
            )

    control_rows = [dict(row) for row in (import_data.control_rows or []) if isinstance(row, dict)]
    mapping_status = _to_str(summary.import_status)
    model = ProjectModel(
        project_id=project_id,
        project_name=project_name,
        project_type="import_3d",
        status="active",
        created_at=built_at,
        updated_at=built_at,
        source="constructor_3d_project",
        header=ProjectHeader(
            project_name=project_name,
            client_name="",
            order_code=_to_str(summary.project_name) or project_id,
            order_name=_to_str(summary.module_name) or project_name,
            status="active",
            source_kind="constructor_3d_project",
            source_path=source_path,
            created_at=built_at,
            updated_at=built_at,
        ),
        quote_context=ProjectQuoteContext(
            mode="import_3d",
            pricing_policy=pricing_policy,
            margin_percent=0.0,
            vat_percent=23.0,
            transport_flat=0.0,
            montage_flat=0.0,
            labor_cost=total_labor,
            policy_multiplier=policy_multiplier,
        ),
        quote_lines=quote_lines,
        services=service_lines,
        import_3d=ProjectImport3D(
            project_path=source_path,
            project_name=summary.project_name,
            project_date=summary.project_date,
            project_version=summary.project_version,
            module_name=summary.module_name,
            module_length_mm=summary.module_length_mm,
            module_width_mm=summary.module_width_mm,
            module_height_mm=summary.module_height_mm,
            formatki_count=summary.formatki_count,
            fronty_count=summary.fronty_count,
            okucia_count=summary.okucia_count,
            laczniki_count=summary.laczniki_count,
            operations_count=summary.operations_count,
            total_area_m2=summary.total_area_m2,
            total_edgeband_mb=summary.total_edgeband_mb,
            import_status=summary.import_status,
            control_rows=control_rows,
        ),
        mapping=ProjectMapping(
            material_map=dict(mapping_payload.get("material_map", {}) or {}),
            edgeband_map=dict(mapping_payload.get("edgeband_map", {}) or {}),
            hardware_map=dict(mapping_payload.get("hardware_map", {}) or {}),
            operation_map=dict(mapping_payload.get("operation_map", {}) or {}),
            mapping_status=mapping_status,
            last_saved_at="",
        ),
        pricing_snapshot=ProjectPricingSnapshot(
            technical_total=total_material + total_edge + total_labor + total_extra,
            material_value=total_material,
            services_total=total_labor + total_extra,
            extras_total=total_extra,
            base_total=total_material + total_edge + total_labor + total_extra,
            sale_total=total_material + total_edge + total_labor + total_extra,
            brutto_total=total_material + total_edge + total_labor + total_extra,
            profit_total=0.0,
            computed_at=built_at,
        ),
        audit=ProjectAudit(
            built_from=[
                "constructor_3dc_project",
                "constructor_3dc_mapping.json",
            ],
            built_at=built_at,
            source_versions=[
                "constructor_3dc_quote_import_service",
                "dialog_import_3dc",
            ],
            adapter_name="Import3DProjectAdapter",
            notes="Read-only snapshot from Import 3D workflow.",
        ),
    )
    return model
