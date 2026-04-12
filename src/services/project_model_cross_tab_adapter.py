"""
Adapter Cross-Tab: Łącza modele z 5 obszarów w jeden ProjectModel

Konsoliduje dane z:
1. Szybka wycena (quick_quote)
2. Usługi (service_order)
3. Import 3D (.project XML)
4. Wycena projektu (assembly)
5. GiB Lab (rozkrój)

Rezultat: Jeden ProjectModel z ALL quote_lines + ALL services
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.domain.project_model import (
    ProjectModel, ProjectHeader, ProjectQuoteContext, ProjectQuoteLine,
    ProjectServiceLine, ProjectImport3D, ProjectMapping, ProjectGibLabResult,
    ProjectPricingSnapshot, ProjectAudit
)


def merge_project_models(
    models: list[ProjectModel] | None = None,
    *,
    client_name: str = "",
    order_code: str = "",
    project_name: str = "Ujednolicona wycena",
    margin_percent: float = 10.0,
    vat_percent: float = 23.0,
    merge_reason: str = "cross_tab_merge"
) -> ProjectModel:
    """
    Łączy wiele ProjectModel w jeden (e.g. quick + services + import_3d)

    Args:
        models: Lista modeli do scalenia
        client_name: Nazwa klienta (dla headera)
        order_code: Kod zamówienia
        project_name: Nazwa projektu
        margin_percent: Marża (%)
        vat_percent: VAT (%)
        merge_reason: Powód scalenia

    Returns:
        ProjectModel - scalony model ze wszystkimi danymi
    """
    models = models or []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # === AGREGACJA DANYCH ===

    # Quote lines - z wszystkich modeli
    all_quote_lines: list[ProjectQuoteLine] = []
    for model in models:
        if model.quote_lines:
            all_quote_lines.extend(model.quote_lines)

    # Services - z wszystkich modeli
    all_services: list[ProjectServiceLine] = []
    for model in models:
        if model.services:
            all_services.extend(model.services)

    # Import 3D - bierz pierwszy (jeśli istnieje)
    import_3d = ProjectImport3D()
    for model in models:
        if model.import_3d and model.import_3d.project_path:
            import_3d = model.import_3d
            break

    # Mapping - bierz pierwszy (jeśli istnieje)
    mapping = ProjectMapping()
    for model in models:
        if model.mapping and model.mapping.material_map:
            mapping = model.mapping
            break

    # GiB Lab - bierz pierwszy (jeśli istnieje)
    giblab_result = ProjectGibLabResult()
    for model in models:
        if model.giblab_result and model.giblab_result.result_path:
            giblab_result = model.giblab_result
            break

    # === OBLICZANIE PRICING SNAPSHOT ===

    material_value = sum(line.cost_material or 0.0 for line in all_quote_lines)
    services_total = sum(line.cost_labor or 0.0 for line in all_quote_lines)
    extras_total = sum(line.cost_extra or 0.0 for line in all_quote_lines)

    # Services dodatkowe
    for svc in all_services:
        if svc.amount:
            services_total += svc.amount

    base_total = material_value + services_total + extras_total

    sale_total = base_total * (1.0 + margin_percent / 100.0)
    brutto_total = sale_total * (1.0 + vat_percent / 100.0)
    profit_total = sale_total - base_total

    pricing_snapshot = ProjectPricingSnapshot(
        technical_total=material_value,
        material_value=material_value,
        services_total=services_total,
        extras_total=extras_total,
        base_total=base_total,
        sale_total=sale_total,
        brutto_total=brutto_total,
        profit_total=profit_total,
        computed_at=now
    )

    # === AUDIT TRAIL ===

    source_list = []
    source_versions = []
    for model in models:
        if model.source:
            source_list.append(model.source)
        if model.audit and model.audit.built_from:
            source_versions.extend(model.audit.built_from)

    audit = ProjectAudit(
        built_from=list(set(source_list)),  # Unique
        built_at=now,
        source_versions=list(set(source_versions)),  # Unique
        adapter_name="merge_project_models()",
        notes=f"Cross-tab merge: {len(models)} models, {merge_reason}"
    )

    # === FINAL MODEL ===

    model = ProjectModel(
        project_id=f"merged_{order_code or 'cross_tab'}",
        project_name=project_name,
        project_type="cross_tab_merge",
        status="active",
        created_at=now,
        updated_at=now,
        source="cross_tab_adapter",

        header=ProjectHeader(
            project_name=project_name,
            client_name=client_name,
            order_code=order_code,
            source_kind="cross_tab",
            source_path="N/A",
            created_at=now,
            updated_at=now
        ),

        quote_context=ProjectQuoteContext(
            mode="cross_tab",
            margin_percent=margin_percent,
            vat_percent=vat_percent
        ),

        quote_lines=all_quote_lines,
        services=all_services,
        import_3d=import_3d,
        mapping=mapping,
        giblab_result=giblab_result,
        pricing_snapshot=pricing_snapshot,
        audit=audit
    )

    return model


def get_quick_quote_summary(model: ProjectModel) -> dict[str, Any]:
    """Wyciąga streszczenie szybkiej wyceny z merged model."""
    snapshot = model.pricing_snapshot
    return {
        "client": model.header.client_name,
        "order": model.header.order_code,
        "material": snapshot.material_value,
        "services": snapshot.services_total,
        "extras": snapshot.extras_total,
        "base_total": snapshot.base_total,
        "netto": snapshot.sale_total,
        "brutto": snapshot.brutto_total,
        "profit": snapshot.profit_total,
    }


def get_import_3d_summary(model: ProjectModel) -> dict[str, Any]:
    """Wyciąga streszczenie importu 3D z merged model."""
    imp3d = model.import_3d
    return {
        "project": imp3d.project_name,
        "date": imp3d.project_date,
        "module": imp3d.module_name,
        "length_mm": imp3d.module_length_mm,
        "width_mm": imp3d.module_width_mm,
        "height_mm": imp3d.module_height_mm,
        "total_area_m2": imp3d.total_area_m2,
        "total_edgeband_mb": imp3d.total_edgeband_mb,
        "formatki_count": imp3d.formatki_count,
        "fronty_count": imp3d.fronty_count,
        "okucia_count": imp3d.okucia_count,
    }


def get_giblab_summary(model: ProjectModel) -> dict[str, Any]:
    """Wyciąga streszczenie GiB Lab z merged model."""
    giblab = model.giblab_result
    return {
        "real_area_m2": giblab.real_area_m2,
        "real_sheets_count": giblab.real_sheets_count,
        "utilization_pct": giblab.difference_vs_theory.get("utilization_pct", 0.0),
        "scrap_m2": giblab.scrap_m2,
    } if giblab.result_path else {}


def get_assembly_summary(model: ProjectModel) -> dict[str, Any]:
    """Wyciąga streszczenie assembly z merged model."""
    if not model.assemblies:
        return {}

    assy = model.assemblies[0]
    return {
        "name": assy.name,
        "width_mm": assy.width_mm,
        "height_mm": assy.height_mm,
        "depth_mm": assy.depth_mm,
        "material_profile": assy.material_profile_key,
        "transport": assy.transport_cost_pln,
        "montage": assy.montage_cost_pln,
    }


def get_services_summary(model: ProjectModel) -> dict[str, Any]:
    """Wyciąga streszczenie usług z merged model."""
    if not model.services:
        return {}

    total = sum(svc.amount or 0.0 for svc in model.services)
    count = len(model.services)

    return {
        "count": count,
        "total": total,
        "services": [
            {
                "name": svc.service_name,
                "qty": svc.qty,
                "unit": svc.unit,
                "amount": svc.amount
            }
            for svc in model.services
        ]
    }
