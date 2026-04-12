from __future__ import annotations

from datetime import datetime
from pathlib import Path
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


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return float(default)


def _to_str(value: Any) -> str:
    return str(value or "").strip()


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def build_service_quote_project_model(
    payload: dict[str, Any],
    *,
    source_path: str = "",
    pricing_policy: str = "",
    policy_multiplier: float = 1.0,
) -> ProjectModel:
    payload = dict(payload or {})
    quote_id = _to_str(payload.get("quote_id", ""))
    client = _to_str(payload.get("client", ""))
    service_id = _to_str(payload.get("service_id", ""))
    service_name = _to_str(payload.get("service_name", ""))
    entry_date = _to_str(payload.get("entry_date", ""))
    start_date = _to_str(payload.get("date_start", ""))
    end_date = _to_str(payload.get("date_end", ""))
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        rows = []

    net_total = _to_float(payload.get("net_total", payload.get("total", 0.0)))
    brutto_total = _to_float(payload.get("brutto_total", 0.0))

    quote_lines: list[ProjectQuoteLine] = []
    service_lines: list[ProjectServiceLine] = []
    material_total = 0.0
    labor_total = 0.0

    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        material_name = _to_str(row.get("material_name", ""))
        work_name = _to_str(row.get("work_name", ""))
        row_id = _to_str(row.get("row_id", "")) or f"ROW{idx + 1:03d}"
        qty = _to_float(row.get("qty", 1.0), 1.0)
        if qty <= 0.0:
            qty = 1.0
        material_price = _to_float(row.get("material_price", 0.0))
        work_price = _to_float(row.get("work_price", 0.0))
        row_net = _to_float(row.get("row_sum_netto", 0.0))
        row_brutto = _to_float(row.get("row_sum_brutto", 0.0))
        vat = _to_float(row.get("vat", 23.0))
        formatki = row.get("formatki", [])
        if not isinstance(formatki, list):
            formatki = []

        row_material_total = material_price * qty
        row_labor_total = work_price * qty
        material_total += row_material_total
        labor_total += row_labor_total

        material_ref = material_name or service_name or "usluga"
        work_ref = work_name or service_name or "usluga"
        position_name = " / ".join(part for part in [material_ref, work_ref] if part)
        note_bits = [
            f"RAL:{_to_str(row.get('ral', ''))}",
            f"NCS:{_to_str(row.get('ncs', ''))}",
            f"Model:{_to_str(row.get('model', ''))}",
        ]
        note = " | ".join(bit for bit in note_bits if not bit.endswith(":"))

        quote_lines.append(
            ProjectQuoteLine(
                line_id=row_id,
                source_kind="service_quote",
                source_ref=quote_id,
                group=service_name or "Uslugi",
                module_name=client or service_name,
                position_name=position_name or row_id,
                qty=qty,
                unit="szt",
                material_name=material_ref,
                cost_material=row_material_total,
                cost_labor=row_labor_total,
                line_total=row_net,
                status="OK",
                accuracy="saved",
                note=note or f"VAT:{vat:.2f}%",
            )
        )
        service_lines.append(
            ProjectServiceLine(
                service_id=_to_str(row.get("work_id", "")) or service_id or row_id,
                service_name=work_ref or service_name,
                source_kind="service_quote",
                source_ref=row_id,
                qty=qty,
                unit="szt",
                amount=row_net,
                status="OK",
                note=f"Formatki: {len(formatki)}",
            )
        )

    model = ProjectModel(
        project_id=quote_id or f"service_{client or 'quote'}",
        project_name=service_name or "Usluga",
        project_type="service_quote",
        status=str(payload.get("status", "active") or "active"),
        created_at=_to_str(payload.get("entry_date", "")) or _now_text(),
        updated_at=_to_str(payload.get("updated_at", "")) or _now_text(),
        source="usluga_quotes",
        header=ProjectHeader(
            project_name=service_name or "Usluga",
            client_name=client,
            order_code=quote_id,
            order_name=service_name or "Usluga",
            status=str(payload.get("status", "active") or "active"),
            source_kind="usluga_quotes",
            source_path=source_path,
            created_at=_to_str(payload.get("entry_date", "")) or _now_text(),
            updated_at=_to_str(payload.get("updated_at", "")) or _now_text(),
        ),
        quote_context=ProjectQuoteContext(
            mode="services",
            pricing_policy=pricing_policy,
            margin_percent=0.0,
            vat_percent=23.0,
            transport_flat=0.0,
            montage_flat=0.0,
            labor_cost=labor_total,
            policy_multiplier=policy_multiplier,
        ),
        quote_lines=quote_lines,
        services=service_lines,
        pricing_snapshot=ProjectPricingSnapshot(
            technical_total=material_total + labor_total,
            material_value=material_total,
            services_total=material_total + labor_total,
            extras_total=0.0,
            base_total=net_total,
            sale_total=net_total,
            brutto_total=brutto_total,
            profit_total=max(0.0, net_total - (material_total + labor_total)),
            computed_at=_now_text(),
        ),
        import_3d=ProjectImport3D(),
        mapping=ProjectMapping(),
        audit=ProjectAudit(
            built_from=["usluga_quotes.json"],
            built_at=_now_text(),
            source_versions=["tab_uslugi"],
            adapter_name="ServiceProjectAdapter",
            notes="Read-only snapshot for service workflow.",
        ),
    )
    return model
