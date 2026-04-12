from __future__ import annotations

import csv
from html import escape
from pathlib import Path

from src.core.orders_map_service import MapOrderPoint


def build_trip_card_rows(points: list[MapOrderPoint]) -> list[dict]:
    ordered = sorted(points, key=lambda x: (int(x.trip_order or 0), str(x.client_name or "")))
    rows: list[dict] = []
    for idx, p in enumerate(ordered, 1):
        rows.append(
            {
                "order_no": idx,
                "project_name": p.project_name,
                "client_name": p.client_name,
                "contact_name": p.contact_name,
                "contact_phone": p.contact_phone,
                "city": p.city,
                "full_address": p.full_address,
                "visit_type": p.visit_type,
                "visit_status": p.visit_status,
                "work_scope": p.work_scope,
                "items_to_take": p.items_to_take,
                "crew_notes": p.crew_notes,
                "trip_order": int(p.trip_order or idx),
            }
        )
    return rows


def export_trip_card_to_csv(points: list[MapOrderPoint], path: str, trip_meta: dict | None = None) -> None:
    target = Path(str(path or "").strip())
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = build_trip_card_rows(points)
    columns = [
        "order_no",
        "project_name",
        "client_name",
        "contact_name",
        "contact_phone",
        "city",
        "full_address",
        "visit_type",
        "visit_status",
        "work_scope",
        "items_to_take",
        "crew_notes",
        "trip_order",
    ]
    with target.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def export_trip_card_to_html(points: list[MapOrderPoint], path: str, trip_meta: dict | None = None) -> None:
    target = Path(str(path or "").strip())
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = build_trip_card_rows(points)
    meta = trip_meta or {}
    title = str(meta.get("title", "Karta wyjazdu")).strip() or "Karta wyjazdu"
    date_text = str(meta.get("date", "") or "").strip()
    crew_text = str(meta.get("crew", "") or "").strip()

    head = f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<title>{escape(title)}</title>
<style>
body{{font-family:Arial,sans-serif;margin:20px;color:#111}}
h1{{margin:0 0 6px 0;font-size:20px}}
.meta{{margin-bottom:12px;color:#333;font-size:13px}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th,td{{border:1px solid #cbd5e1;padding:6px;vertical-align:top}}
th{{background:#f1f5f9;text-align:left}}
</style>
</head>
<body>
<h1>{escape(title)}</h1>
<div class="meta">Data: {escape(date_text)} | Ekipa: {escape(crew_text)}</div>
<table>
<thead><tr>
<th>Lp.</th><th>Projekt</th><th>Klient</th><th>Kontakt</th><th>Telefon</th>
<th>Miasto</th><th>Adres</th><th>Typ</th><th>Status</th><th>Zakres robot</th><th>Co zabrac</th><th>Uwagi</th>
</tr></thead><tbody>
"""
    body_rows = []
    for r in rows:
        body_rows.append(
            "<tr>"
            f"<td>{int(r.get('order_no', 0))}</td>"
            f"<td>{escape(str(r.get('project_name', '') or ''))}</td>"
            f"<td>{escape(str(r.get('client_name', '') or ''))}</td>"
            f"<td>{escape(str(r.get('contact_name', '') or ''))}</td>"
            f"<td>{escape(str(r.get('contact_phone', '') or ''))}</td>"
            f"<td>{escape(str(r.get('city', '') or ''))}</td>"
            f"<td>{escape(str(r.get('full_address', '') or ''))}</td>"
            f"<td>{escape(str(r.get('visit_type', '') or ''))}</td>"
            f"<td>{escape(str(r.get('visit_status', '') or ''))}</td>"
            f"<td>{escape(str(r.get('work_scope', '') or ''))}</td>"
            f"<td>{escape(str(r.get('items_to_take', '') or ''))}</td>"
            f"<td>{escape(str(r.get('crew_notes', '') or ''))}</td>"
            "</tr>"
        )
    tail = "</tbody></table></body></html>\n"
    target.write_text(head + "\n".join(body_rows) + tail, encoding="utf-8")
