from __future__ import annotations

from dataclasses import dataclass

from src.api.data_manager import TechModulDataManager
from src.domain.module_models import ModuleDef


@dataclass
class SqliteProjectModuleRepository:
    data_manager: TechModulDataManager
    project_id: int = 1

    def get_by_id(self, module_id: str) -> ModuleDef | None:
        wanted = str(module_id or "").strip()
        if not wanted:
            return None
        rows = self.data_manager.get_project_modules(int(self.project_id))
        for row in rows:
            if str(row.get("id", "")).strip() == wanted:
                return self._row_to_module(row)
        return None

    def get_by_name(self, name: str) -> ModuleDef | None:
        wanted = str(name or "").strip()
        if not wanted:
            return None
        rows = self.data_manager.get_project_modules(int(self.project_id))
        for row in rows:
            if str(row.get("name", "")).strip() == wanted:
                return self._row_to_module(row)
        return None

    def save(self, module: ModuleDef) -> None:
        module_id = int(str(getattr(module, "module_id", "") or "0") or 0)
        if module_id <= 0:
            return
        
        # 1. Sync legacy columns for basic visibility
        self.data_manager.update_module_dimension(module_id, "width", int(float(module.width_mm)))
        self.data_manager.update_module_dimension(module_id, "height", int(float(module.height_mm)))
        self.data_manager.update_module_dimension(module_id, "depth", int(float(module.depth_mm)))
        if module.material_id is not None:
             # Legacy mapping if method exists, else we rely on JSON
             try:
                self.data_manager.update_module_material(module_id, int(module.material_id))
             except:
                pass
        
        # 2. Save EVERYTHING to spec_json
        import json
        full_spec = module.to_dict()
        self.data_manager.update_module_spec(module_id, json.dumps(full_spec))

    @staticmethod
    def _row_to_module(row: dict) -> ModuleDef:
        import json
        raw_json = row.get("spec_json") or "{}"
        try:
            data = json.loads(raw_json)
        except:
            data = {}
            
        # Overwrite with current DB columns to stay in sync
        data["module_id"] = str(row.get("id", "") or "")
        data["id"] = data["module_id"]
        data["name"] = str(row.get("name", "") or "")
        data["width_mm"] = float(row.get("width", 0.0) or 0.0)
        data["height_mm"] = float(row.get("height", 0.0) or 0.0)
        data["depth_mm"] = float(row.get("depth", 0.0) or 0.0)
        data["material_id"] = row.get("material_id")
        
        return ModuleDef.from_dict(data)

