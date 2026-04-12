from __future__ import annotations

from datetime import datetime
from typing import Any

from src.domain.project_model import (
    ProjectAudit,
    ProjectHeader,
    ProjectModel,
    ProjectPricingSnapshot,
    ProjectQuoteContext,
    ProjectQuoteLine,
    ProjectServiceLine,
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


def build_quick_quote_project_model(
    entry: dict[str, Any],
    quick_totals: dict[str, Any],
    *,
    quick_adjustment: dict[str, Any] | None = None,
    archive_path: str = "",
    pricing_policy: str = "",
    policy_multiplier: float = 1.0,
) -> ProjectModel:
    entry = dict(entry or {})
    quick_totals = dict(quick_totals or {})
    quick_adjustment = dict(quick_adjustment or {})

    quote_id = _to_str(entry.get("id", ""))
    title = _to_str(entry.get("title", "")) or "Szybka wycena"
    client = _to_str(entry.get("client", ""))
    order_code = _to_str(entry.get("order_code", ""))
    vat = _to_float(entry.get("vat", 23.0))
    margin = _to_float(entry.get("margin", 0.0))

    material_value = _to_float(quick_totals.get("material_value", 0.0))
    transport = _to_float(quick_totals.get("transport", 0.0))
    hours = _to_float(quick_totals.get("hours", 0.0))
    montage = _to_float(quick_totals.get("montage", 0.0))
    extras_total = _to_float(quick_totals.get("extras_total", 0.0))
    labor_cost = _to_float(quick_totals.get("labor_cost", 0.0))
    base_total = _to_float(quick_totals.get("base_total", 0.0))
    netto = _to_float(quick_totals.get("netto", 0.0))
    brutto = _to_float(quick_totals.get("brutto", 0.0))
    profit_total = max(0.0, netto - base_total)
    rate_source = _to_str(quick_totals.get("rate_source", ""))

    quote_lines: list[ProjectQuoteLine] = [
        ProjectQuoteLine(
            line_id=f"{quote_id or 'QUICK'}-MAT",
            source_kind="quick_quote",
            source_ref=quote_id,
            group="Wycena",
            module_name=title,
            position_name="Wartosc materialow",
            qty=1.0,
            unit="kpl",
            cost_material=material_value,
            line_total=material_value,
            status="OK",
            accuracy="snapshot",
            note="Baza szybkiej wyceny",
        ),
        ProjectQuoteLine(
            line_id=f"{quote_id or 'QUICK'}-TRN",
            source_kind="quick_quote",
            source_ref=quote_id,
            group="Koszty dodatkowe",
            module_name=title,
            position_name="Transport",
            qty=1.0,
            unit="usl",
            cost_extra=transport,
            line_total=transport,
            status="OK",
            accuracy="snapshot",
            note="Koszt transportu z szybkiej wyceny",
        ),
        ProjectQuoteLine(
            line_id=f"{quote_id or 'QUICK'}-LAB",
            source_kind="quick_quote",
            source_ref=quote_id,
            group="Koszty dodatkowe",
            module_name=title,
            position_name="Robocizna",
            qty=hours,
            unit="h",
            cost_labor=labor_cost,
            line_total=labor_cost,
            status="OK",
            accuracy="snapshot",
            note=f"Stawka zrodla: {rate_source or 'wydatki'}",
        ),
        ProjectQuoteLine(
            line_id=f"{quote_id or 'QUICK'}-MON",
            source_kind="quick_quote",
            source_ref=quote_id,
            group="Koszty dodatkowe",
            module_name=title,
            position_name="Montaz",
            qty=1.0,
            unit="usl",
            cost_extra=montage,
            line_total=montage,
            status="OK",
            accuracy="snapshot",
            note="Koszt montazu z szybkiej wyceny",
        ),
    ]

    service_lines: list[ProjectServiceLine] = []
    extras_rows = quick_adjustment.get("extras", []) or []
    if isinstance(extras_rows, list):
        for idx, extra in enumerate(extras_rows):
            if not isinstance(extra, dict):
                continue
            desc = _to_str(extra.get("desc", "")) or "Usluga dodatkowa"
            amount = _to_float(extra.get("amount", 0.0))
            if amount <= 0.0 and not desc:
                continue
            line_id = f"{quote_id or 'QUICK'}-EXT-{idx + 1:02d}"
            quote_lines.append(
                ProjectQuoteLine(
                    line_id=line_id,
                    source_kind="quick_extra",
                    source_ref=line_id,
                    group="Uslugi dodatkowe",
                    module_name=title,
                    position_name=desc,
                    qty=1.0,
                    unit="zl",
                    cost_extra=amount,
                    line_total=amount,
                    status="OK",
                    accuracy="snapshot",
                    note="Dodatkowa pozycja z szybkiej wyceny",
                )
            )
            service_lines.append(
                ProjectServiceLine(
                    service_id=line_id,
                    service_name=desc,
                    source_kind="quick_extra",
                    source_ref=line_id,
                    qty=1.0,
                    unit="zl",
                    amount=amount,
                    status="OK",
                    note="Dodatkowa pozycja z szybkiej wyceny",
                )
            )

    model = ProjectModel(
        project_id=quote_id or f"quick_{title}",
        project_name=title,
        project_type="quick_quote",
        status="active",
        created_at=_to_str(entry.get("created_at", "")),
        updated_at=_now_text(),
        source="quick_quote_archive",
        header=ProjectHeader(
            project_name=title,
            client_name=client,
            order_code=order_code,
            order_name=title,
            status="active",
            source_kind="quick_quote_archive",
            source_path=archive_path,
            created_at=_to_str(entry.get("created_at", "")),
            updated_at=_now_text(),
        ),
        quote_context=ProjectQuoteContext(
            mode="quick",
            pricing_policy=pricing_policy,
            margin_percent=margin,
            vat_percent=vat,
            transport_flat=transport,
            montage_flat=montage,
            labor_cost=labor_cost,
            policy_multiplier=policy_multiplier,
        ),
        quote_lines=quote_lines,
        services=service_lines,
        pricing_snapshot=ProjectPricingSnapshot(
            technical_total=material_value,
            material_value=material_value,
            services_total=extras_total,
            extras_total=extras_total,
            base_total=base_total,
            sale_total=netto,
            brutto_total=brutto,
            profit_total=profit_total,
            computed_at=_now_text(),
        ),
        audit=ProjectAudit(
            built_from=[
                "quick_quote_archive",
                "quick_quote_adjustments",
            ],
            built_at=_now_text(),
            source_versions=[
                "tab_baza_szybkich_wycen",
                "tab_wycena",
            ],
            adapter_name="QuickQuoteProjectAdapter",
            notes="Read-only snapshot for the first ProjectModel integration step.",
        ),
    )
    return model
