from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from src.core.orders_map_service import MapOrderPoint


def export_map_points_to_csv(points: list[MapOrderPoint], path: str) -> None:
    target = Path(str(path or "").strip())
    target.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "Name",
        "Description",
        "Address",
        "City",
        "Phone",
        "ContactName",
        "VisitType",
        "VisitStatus",
        "Crew",
        "WorkScope",
        "ItemsToTake",
        "Project",
        "Client",
        "LastVisitAt",
        "NextVisitAt",
    ]
    with target.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for p in points:
            writer.writerow(
                {
                    "Name": p.project_name or p.client_name or p.id,
                    "Description": p.work_scope or p.crew_notes or "",
                    "Address": p.full_address,
                    "City": p.city,
                    "Phone": p.contact_phone,
                    "ContactName": p.contact_name,
                    "VisitType": p.visit_type,
                    "VisitStatus": p.visit_status,
                    "Crew": p.crew,
                    "WorkScope": p.work_scope,
                    "ItemsToTake": p.items_to_take,
                    "Project": p.project_name,
                    "Client": p.client_name,
                    "LastVisitAt": p.last_visit_at,
                    "NextVisitAt": p.next_visit_at,
                }
            )
