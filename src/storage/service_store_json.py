from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from src.domain.service_models import ServiceDef, new_service_id
from src.storage.data_paths import data_dir


class ServiceStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "services.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")

    def list_services(self) -> List[ServiceDef]:
        try:
            text = self._path.read_text(encoding="utf-8")
            data = json.loads(text) if text.strip() else []
            return [ServiceDef.from_dict(item) for item in data if isinstance(item, dict)]
        except Exception:
            return []

    def save_service(self, svc: ServiceDef) -> None:
        services = self.list_services()
        replaced = False
        for i, s in enumerate(services):
            if s.service_id == svc.service_id:
                services[i] = svc
                replaced = True
                break
        if not replaced:
            services.append(svc)
        self._persist(services)

    def delete_service(self, service_id: str) -> None:
        services = [s for s in self.list_services() if s.service_id != service_id]
        self._persist(services)

    def import_from_csv(self, csv_path: str) -> List[ServiceDef]:
        imported = []
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row.get("name"):
                        continue
                    svc = ServiceDef.from_dict({
                        "service_id": row.get("service_id", "") or new_service_id(),
                        "name": row.get("name", ""),
                        "price": float(row.get("price", 0) or 0),
                        "duration_min": int(row.get("duration_min", 0) or 0),
                        "category": row.get("category", ""),
                        "description": row.get("description", ""),
                        "deadline": row.get("deadline", ""),
                    })
                    self.save_service(svc)
                    imported.append(svc)
        except Exception:
            pass
        return imported

    def export_to_csv(self, csv_path: str) -> None:
        services = self.list_services()
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            fieldnames = ["service_id", "name", "price", "duration_min", "category", "description", "deadline"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for svc in services:
                writer.writerow({
                    "service_id": svc.service_id,
                    "name": svc.name,
                    "price": svc.price,
                    "duration_min": svc.duration_min,
                    "category": svc.category,
                    "description": svc.description,
                    "deadline": svc.deadline,
                })

    def _persist(self, services: List[ServiceDef]) -> None:
        data = [s.to_dict() for s in services]
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
