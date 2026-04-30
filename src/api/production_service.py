from __future__ import annotations
import sqlite3
import pandas as pd
from typing import Dict, List, Any, Optional
from src.api.data_manager import TechModulDataManager
from src.domain.module_models import ModuleDef, PartDef
from src.core.module_parts_service import build_module_parts
from src.storage.catalog_store_json import CatalogStoreJson

class ProductionService:
    def __init__(self, data_manager: TechModulDataManager):
        self.dm = data_manager
        # Catalog is needed for build_module_parts (thicknesses, etc.)
        self.catalog = CatalogStoreJson()
        
        # 1C Legacy Rates (extracted from 'Производство мебели' audit)
        self.RATE_CUTTING = 5.0         # PLN per cut part 
        self.RATE_EDGEBAND = 4.0        # PLN per meter of edgeband
        self.RATE_ASSEMBLY = 50.0       # PLN per module assembly
        self.MARGIN_PERCENT = 0.60      # 60% default markup (Наценка)
        self.DEFAULT_MAT_PRICE = 100.0  # Default PLN/m2 if DB empty

    def get_project_module_defs(self, project_id: int) -> List[ModuleDef]:
        """Zwraća listę w pełni zbudowanych obiektów ModuleDef dla projektu."""
        modules_data = self.dm.get_project_modules(project_id)
        materials = {m["id"]: m for m in self.dm.get_materials()}
        
        module_defs = []
        for mod_row in modules_data:
            m_id = mod_row.get("material_id")
            mat_info = materials.get(m_id) if m_id else None
            mat_key = mat_info["name"] if mat_info else "PB18"
            
            # Map SQLite spec_json if exists
            spec_json = mod_row.get("spec_json", "{}")
            
            m_def = ModuleDef(
                module_id=mod_row["id"],
                name=mod_row["name"],
                width_mm=mod_row["width"],
                height_mm=mod_row["height"],
                depth_mm=mod_row["depth"],
                material_id=m_id,
                module_family=mod_row.get("module_family", "kitchen_lower"),
                visible_parts={"side_left", "side_right", "top", "bottom", "back", "front"} 
            )
            m_def.materials["carcass"] = mat_key
            m_def.materials["front"] = mat_key
            m_def.materials["back"] = "HDF3"
            
            # Build parts (adds parts to m_def.parts)
            m_def.parts = build_module_parts(m_def, self.catalog)
            module_defs.append(m_def)
            
        return module_defs

    def get_project_production_summary(self, project_id: int) -> Dict[str, Any]:
        """
        Creates a global cutting list and material/edgeband stats for the project.
        """
        modules_data = self.dm.get_project_modules(project_id)
        materials = {m["id"]: m for m in self.dm.get_materials()}
        
        all_parts = []
        material_usage = {} # key -> {name, m2, price}
        module_summary = {} # mod_id -> {name, cost, parts_count}
        
        total_labor_cost = 0.0
        total_materials_cost = 0.0
        
        module_defs = self.get_project_module_defs(project_id)
        
        for m_def in module_defs:
            mod_id = m_def.module_id
            module_summary[mod_id] = {
                "name": m_def.name,
                "cost": 0.0,
                "parts_count": 0,
                "area_m2": 0.0
            }
            total_labor_cost += self.RATE_ASSEMBLY 
            
            # 3. Fetch material info for this module
            mat_info = materials.get(m_def.material_id)
            
            # 4. Process each part
            parts_map = m_def.parts
            
            for p_key, p_def in parts_map.items():
                p_dict = p_def.to_dict()
                w, h = p_dict["dims_mm"]["w"], p_dict["dims_mm"]["h"]
                area_m2 = (w * h) / 1_000_000.0
                
                # Precise Edgebanding
                eb = p_dict.get("edge_banding", {})
                edge_m = 0.0
                edge_codes = []
                if eb.get("top"): 
                    edge_m += w / 1000.0
                    edge_codes.append("T")
                if eb.get("bottom"): 
                    edge_m += w / 1000.0
                    edge_codes.append("B")
                if eb.get("left"): 
                    edge_m += h / 1000.0
                    edge_codes.append("L")
                if eb.get("right"): 
                    edge_m += h / 1000.0
                    edge_codes.append("R")
                
                # Pricing
                mat_price_m2 = mat_info.get("price_per_m2", self.DEFAULT_MAT_PRICE) if mat_info else self.DEFAULT_MAT_PRICE
                part_mat_cost = area_m2 * mat_price_m2
                part_labor_cost = self.RATE_CUTTING + (edge_m * self.RATE_EDGEBAND)
                
                total_labor_cost += part_labor_cost
                total_materials_cost += part_mat_cost
                
                part_entry = {
                    "module_id": m_def.module_id,
                    "module_name": m_def.name,
                    "part_key": p_key,
                    "name": p_dict["name_pl"],
                    "material": p_dict["material_key"],
                    "width": w,
                    "height": h,
                    "thickness": p_dict["dims_mm"]["t"],
                    "area_m2": round(area_m2, 4),
                    "edge_m": round(edge_m, 2),
                    "edge_codes": ",".join(edge_codes),
                    "grain": p_dict.get("grain_direction", "none"),
                    "cost_pln": round(part_mat_cost + part_labor_cost, 2)
                }
                all_parts.append(part_entry)
                
                # Material Usage tracking
                m_usage_key = p_dict["material_key"]
                if m_usage_key not in material_usage:
                    material_usage[m_usage_key] = {
                        "name": m_usage_key, 
                        "total_m2": 0.0, 
                        "parts_count": 0,
                        "cost": 0.0
                    }
                
                material_usage[m_usage_key]["total_m2"] += area_m2
                material_usage[m_usage_key]["parts_count"] += 1
                material_usage[m_usage_key]["cost"] += part_mat_cost
                
                # Module-level tracking
                module_summary[mod_id]["cost"] += (part_mat_cost + part_labor_cost)
                module_summary[mod_id]["parts_count"] += 1
                module_summary[mod_id]["area_m2"] += area_m2

        # Round totals
        for m in material_usage.values():
            m["total_m2"] = round(m["total_m2"], 2)
            m["cost"] = round(m["cost"], 2)

        total_cost = total_labor_cost + total_materials_cost
        final_price = total_cost * (1.0 + self.MARGIN_PERCENT)

        return {
            "project_id": project_id,
            "parts": all_parts,
            "material_stats": list(material_usage.values()),
            "parts_count": len(all_parts),
            "pricing": {
                "materials_cost": round(total_materials_cost, 2),
                "labor_cost": round(total_labor_cost, 2),
                "total_cost": round(total_cost, 2),
                "margin_percent": self.MARGIN_PERCENT * 100,
                "final_price": round(final_price, 2)
            }
        }

    def export_cutting_list_csv(self, project_id: int) -> str:
        """Returns CSV string of the cutting list compatible with Ardis / Optimik / Optima."""
        summary = self.get_project_production_summary(project_id)
        
        ardis_rows = []
        for p in summary.get("parts", []):
            grain = p.get("grain", "none")
            w, h = p["width"], p["height"]
            
            # Logic: Length (L) is along grain. 
            # In our system: vertical grain means L is Height. Horizontal means L is Width.
            # If no grain, we keep standard L=H, W=W.
            if grain == "horizontal":
                length, width = w, h
                grain_flag = "1"
            else:
                length, width = h, w
                grain_flag = "1" if grain == "vertical" else "0"

            # Edgebanding mapping based on orientation
            # If swapped (horizontal), then top/bottom become L1/L2 and left/right become W1/W2
            codes = p.get("edge_codes", "").split(",")
            e_l1, e_l2, e_w1, e_w2 = "0", "0", "0", "0"
            
            if grain == "horizontal":
                # L is Width (w)
                if "T" in codes: e_l1 = "1"
                if "B" in codes: e_l2 = "1"
                if "L" in codes: e_w1 = "1"
                if "R" in codes: e_w2 = "1"
            else:
                # L is Height (h)
                if "L" in codes: e_l1 = "1"
                if "R" in codes: e_l2 = "1"
                if "T" in codes: e_w1 = "1"
                if "B" in codes: e_w2 = "1"

            ardis_rows.append({
                "Zlecenie": f"PRJ-{project_id}",
                "Element": p["name"],
                "Kod_Szafki": p["module_name"],
                "Material": p["material"],
                "Dlugosc_L": length,
                "Szerokosc_W": width,
                "Grubosc": p["thickness"],
                "Sztuk": 1,
                "Uslojenie": grain_flag,
                "Okl_L1": e_l1,
                "Okl_L2": e_l2,
                "Okl_W1": e_w1,
                "Okl_W2": e_w2,
                "Uwagi": p["part_key"]
            })
            
        df = pd.DataFrame(ardis_rows)
        return df.to_csv(index=False, sep=";", encoding="utf-8-sig")
