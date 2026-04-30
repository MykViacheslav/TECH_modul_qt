import json
import os
from typing import Dict, Any, List
from src.domain.module_models import ModuleDef, PartDef
from src.core.rules.drilling_generator import generate_drilling_for_part

def get_suggested_export_filename(module: ModuleDef) -> str:
    """Generates a production-friendly filename based on module name and ID."""
    name = str(module.name or "Modul").strip().replace(" ", "_")
    # Clean up filename
    safe_name = "".join([c if c.isalnum() or c == "_" else "" for c in name])
    
    # Try to find a short ID (last 4 chars of UUID or just use '1')
    m_id = str(module.module_id or "1")
    short_id = m_id[-4:] if "-" in m_id else m_id[:4]
    
    return f"ZLECENIE_{safe_name}_{short_id}.project"

def export_module_to_giblab_project(module: ModuleDef, output_path: str) -> str:
    """
    Exports a single module design to the .project format used by GibLab/PlanPol CNC centers.
    """
    project_data = {
        "version": "2.1",
        "header": {
            "project_name": module.name or "Nowy Modul",
            "exporter": "TechModul ERP v2.0",
            "units": "mm"
        },
        "cabinet": {
            "width": float(module.width_mm),
            "height": float(module.height_mm),
            "depth": float(module.depth_mm),
            "parts": []
        }
    }

    # Process each part in the module
    for part_key, part in (module.parts or {}).items():
        w = float((part.dims_mm or {}).get("w", 0))
        h = float((part.dims_mm or {}).get("h", 0))
        t = float((part.dims_mm or {}).get("t", 18))
        
        # Determine grain (0=none/cross, 1=along length)
        # In GibLab, Length is usually the dimension ALONG the grain.
        grain_dir = str(part.grain_direction or "").strip().lower()
        
        # Basic dimensions
        p_len, p_wid = h, w
        if grain_dir == "horizontal":
            p_len, p_wid = w, h
        
        grain_flag = 0 if grain_dir == "none" else 1

        # Edgebanding (GibLab typically expects L1, L2, W1, W2)
        eb = part.edge_banding or {}
        edge_codes = {
            "l1": 1 if eb.get("left") else 0,
            "l2": 1 if eb.get("right") else 0,
            "w1": 1 if eb.get("top") else 0,
            "w2": 1 if eb.get("bottom") else 0
        }

        # Generate Drills for the part
        drills = generate_drilling_for_part(module, part, part_key)
        gib_drills = []
        for d in drills:
            gib_drills.append({
                "x": float(d.x),
                "y": float(d.y),
                "d": float(d.diam),
                "z": float(d.depth),
                "side": 1 if d.vz > 0 else 0, # Top face or Bottom face
                "mark": d.mark
            })

        part_entry = {
            "id": part.id,
            "name": part.name_pl or part_key,
            "material": str(part.material_key or "PB18"),
            "dim_l": p_len,
            "dim_w": p_wid,
            "dim_t": t,
            "grain": grain_flag,
            "edge": edge_codes,
            "cnc_ops": {
                "drills": gib_drills
            },
            # Metadata for UI
            "tags": {
                "part_type": part_key.split("__")[0],
                "part_original_key": part_key
            }
        }
        project_data["cabinet"]["parts"].append(part_entry)

    # Save to file
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=4, ensure_ascii=False)
        return output_path
    except Exception as e:
        return f"ERROR: {str(e)}"

def export_project_to_giblab_bundle(project_id: int, module_defs: List[ModuleDef], target_dir: str) -> List[str]:
    """
    Exports all modules in a project as individual .project files in a target directory.
    """
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        
    paths = []
    for m in module_defs:
        # Sanitize name for filename
        safe_name = "".join([c if c.isalnum() else "_" for c in m.name])
        filename = f"PRJ{project_id}_{m.module_id}_{safe_name}.project"
        path = os.path.join(target_dir, filename)
        result = export_module_to_giblab_project(m, path)
        paths.append(result)
        
    return paths
