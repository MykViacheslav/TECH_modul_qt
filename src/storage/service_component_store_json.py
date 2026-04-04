from __future__ import annotations

from pathlib import Path
from typing import List

from src.domain.service_models import ServiceComponentDef
from src.storage.data_paths import data_dir
from src.storage.safe_json_io import read_json_file, write_json_atomic


class ServiceComponentStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "service_components.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            write_json_atomic(self._path, [], ensure_ascii=False, indent=2)

    def list_components(self) -> List[ServiceComponentDef]:
        data = read_json_file(self._path, default=[], expected_type=list)
        return [ServiceComponentDef.from_dict(item) for item in data if isinstance(item, dict)]

    def list_components_by_service(self, service_id: str) -> List[ServiceComponentDef]:
        """Return all components for a given service (cennik position)."""
        return [c for c in self.list_components() if c.service_id == service_id]

    def save_component(self, comp: ServiceComponentDef) -> None:
        components = self.list_components()
        replaced = False
        for i, c in enumerate(components):
            if c.component_id == comp.component_id:
                components[i] = comp
                replaced = True
                break
        if not replaced:
            components.append(comp)
        self._persist(components)

    def delete_component(self, component_id: str) -> None:
        components = [c for c in self.list_components() if c.component_id != component_id]
        self._persist(components)

    def delete_by_service(self, service_id: str) -> None:
        components = [c for c in self.list_components() if c.service_id != service_id]
        self._persist(components)

    def _persist(self, components: List[ServiceComponentDef]) -> None:
        data = [c.to_dict() for c in components]
        write_json_atomic(self._path, data, ensure_ascii=False, indent=2)
