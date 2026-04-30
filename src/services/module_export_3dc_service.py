from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from src.domain.module_models import ModuleDef
from src.core.rules.hardware import estimate_module_hardware_requirements
from src.core.rules.drilling_generator import generate_drilling_for_part

def export_project_to_3dc_xml(modules: List[ModuleDef], project_name: str, output_path: str | Path) -> Path:
    """
    Eksportuje listÄ™ moduĹ‚Ăłw (caĹ‚y projekt) do formatu XML .project w peĹ‚ni zgodnym z 3DConstructor 3.0 / GibLab.
    Obejmuje geonmetriÄ™ Shape oraz sekcjÄ™ Bands.
    """
    root = ET.Element("Project3dc")
    root.set("name", project_name)
    root.set("date", datetime.now().strftime("%Y.%m.%d"))
    root.set("version", "3.0")

    # 1. Dictionary
    dict_node = ET.SubElement(root, "Dictionary")
    
    # ProjectProperties
    props = ET.SubElement(dict_node, "ProjectProperties")
    ET.SubElement(props, "property", {"key": "", "name": "Customer", "value": ""})
    ET.SubElement(props, "property", {"key": "", "name": "Customer Reference", "value": ""})
    ET.SubElement(props, "property", {"key": "", "name": "Carass Colour", "value": "WHITE"})

    # Classes
    classes_node = ET.SubElement(dict_node, "Classes")
    cls_data = [
        ("0", "Not defined"), ("1", "Assembly"), ("18", "Sheet Part"), 
        ("19", "Fittings"), ("50", "Sheet Door"), ("51", "Fastener")
    ]
    for cid, cdesc in cls_data:
        ET.SubElement(classes_node, "Item", {"id": cid, "description": cdesc})

    # Units
    units_node = ET.SubElement(dict_node, "Units")
    units_data = [
        ("0", "Piece", "pcs"), ("1", "Meter", "m"), ("2", "Square meter", "m2"), ("5", "Millimetre", "mm")
    ]
    for uid, udesc, uname in units_data:
        ET.SubElement(units_node, "Item", {"id": uid, "description": udesc, "name": uname})

    # Materials
    mats_node = ET.SubElement(dict_node, "Materials")
    used_materials = set()
    for mod in modules:
        if mod.parts:
            for p in mod.parts.values():
                used_materials.add(p.material_override_key or p.material_key)
    
    mat_map = {}
    for i, mat_key in enumerate(sorted(list(filter(None, used_materials)))):
        mat_id = f"202:{100+i}"
        mat_map[mat_key] = mat_id
        thick = "18.0"
        if "10" in mat_key: thick = "10.0"
        if "3" in mat_key or "HDF" in mat_key: thick = "3.2"
        
        ET.SubElement(mats_node, "Item", {
            "id": mat_id,
            "type": "sheet",
            "code": mat_key,
            "name": mat_key,
            "thick": thick,
            "cost": "0"
        })

    band_id = "203:1"
    ET.SubElement(mats_node, "Item", {
        "id": band_id,
        "type": "band",
        "code": "PVC_1MM",
        "name": "ObrzeĹĽe 1mm",
        "thick": "1.0",
        "cost": "0.5"
    })

    # 2. ProjectStructure
    struct_node = ET.SubElement(root, "ProjectStructure")
    
    obj_id_counter = 1000
    for mod in modules:
        mod_obj = ET.SubElement(struct_node, "Obj")
        mod_obj.set("id", str(obj_id_counter))
        obj_id_counter += 1
        mod_obj.set("class", "1")
        mod_obj.set("name", mod.name or "Szafka")
        mod_obj.set("code", mod.case_id or f"M{mod.module_id}")
        mod_obj.set("dl", str(float(mod.width_mm or 0)))
        mod_obj.set("dw", str(float(mod.height_mm or 0)))
        mod_obj.set("dtt", str(float(mod.depth_mm or 0)))
        mod_obj.set("cost", "0")
        mod_obj.set("costFlag", "false")

        # Części
        if mod.parts:
            for part_id, part in mod.parts.items():
                p_obj = ET.SubElement(mod_obj, "Obj")
                p_obj.set("id", str(obj_id_counter))
                obj_id_counter += 1
                
                p_cls = "50" if "front" in part.name_pl.lower() else "18"
                p_obj.set("class", p_cls)
                p_obj.set("name", part.name_pl or part_id)
                p_obj.set("code", part_id)
                
                # Geometria (dl, dw z uwzglÄ™dnieniem usĹ‚ojenia)
                dims = part.dims_mm or {}
                w_val = float(dims.get("w", 0))
                h_val = float(dims.get("h", 0))
                t_val = float(dims.get("t", 18))
                
                grain = part.grain_direction
                if grain == "horizontal":
                    dl_val, dw_val = w_val, h_val
                else:
                    dl_val, dw_val = h_val, w_val

                p_obj.set("l", str(dl_val))
                p_obj.set("w", str(dw_val))
                p_obj.set("dtt", str(t_val))
                p_obj.set("dl", str(dl_val))
                p_obj.set("dw", str(dw_val))
                p_obj.set("dtl", str(dl_val))
                p_obj.set("dtw", str(dw_val))
                p_obj.set("quantity", "1")
                p_obj.set("unit", "0")
                p_obj.set("txt", "true" if grain != "none" else "false")
                p_obj.set("cutting", "true")
                p_obj.set("FactAngle", "true")
                
                mat_key = part.material_override_key or part.material_key
                p_obj.set("material", mat_map.get(mat_key, "202:100"))
                p_obj.set("cost", "0")

                # Oklejanie (bandL/T/R/B)
                eb = part.edge_banding or {}
                has_banding = False
                bands_node = None # BÄ™dzie stworzony jeĹ›li has_banding
                
                # Mapowanie edgeId: 1=B, 2=R, 3=T, 4=L (orientacja 3DC)
                # Dla uproszczenia (Rect): 
                # L1/L2 (dĹ‚uĹĽsze boki dl) -> bandL, bandR
                # W1/W2 (krĂłtsze boki dw) -> bandT, bandB
                
                # Zgodnie z exportem z 3DC:
                if eb.get("left"): p_obj.set("bandL", band_id); p_obj.set("bandLtype", "0"); has_banding = True
                if eb.get("right"): p_obj.set("bandR", band_id); p_obj.set("bandRtype", "0"); has_banding = True
                if eb.get("top"): p_obj.set("bandT", band_id); p_obj.set("bandTtype", "0"); has_banding = True
                if eb.get("bottom"): p_obj.set("bandB", band_id); p_obj.set("bandBtype", "0"); has_banding = True

                if has_banding:
                    bands_node = ET.SubElement(p_obj, "Bands")
                    if eb.get("bottom"): ET.SubElement(bands_node, "Band", {"id": band_id, "quantity": str(dl_val), "edgeType": "0", "edgeId": "1"})
                    if eb.get("right"): ET.SubElement(bands_node, "Band", {"id": band_id, "quantity": str(dw_val), "edgeType": "0", "edgeId": "2"})
                    if eb.get("top"): ET.SubElement(bands_node, "Band", {"id": band_id, "quantity": str(dl_val), "edgeType": "0", "edgeId": "3"})
                    if eb.get("left"): ET.SubElement(bands_node, "Band", {"id": band_id, "quantity": str(dw_val), "edgeType": "0", "edgeId": "4"})

                # Sekcja Shape (wymagana przez niektĂłre wersje GibLaba)
                shape_overall = ET.SubElement(p_obj, "ShapeOverallCS")
                side_base = ET.SubElement(shape_overall, "Side", {"id": "base", "FaceProp": "true"})
                shape_node = ET.SubElement(side_base, "Shape")
                # ProstokÄ…t 0,0 do dl,dw
                ET.SubElement(shape_node, "EdgeLine", {"id": "1", "X1": "0", "Y1": str(dw_val), "X2": str(dl_val), "Y2": str(dw_val), "Face": "true"})
                ET.SubElement(shape_node, "EdgeLine", {"id": "2", "X1": str(dl_val), "Y1": str(dw_val), "X2": str(dl_val), "Y2": "0"})
                ET.SubElement(shape_node, "EdgeLine", {"id": "3", "X1": str(dl_val), "Y1": "0", "X2": "0", "Y2": "0"})
                ET.SubElement(shape_node, "EdgeLine", {"id": "4", "X1": "0", "Y1": "0", "X2": "0", "Y2": str(dw_val)})

                # --- 3. Drilling (Nawiercenia) ---
                drills = generate_drilling_for_part(mod, part, part_id)
                if drills:
                    drills_node = ET.SubElement(side_base, "Drillings")
                    for d in drills:
                        ET.SubElement(drills_node, "Drilling", {
                            "X": f"{d.x:.5f}", "Y": f"{d.y:.5f}", "Z": f"{d.z:.5f}",
                            "vectorX": f"{d.vx:.5f}", "vectorY": f"{d.vy:.5f}", "vectorZ": f"{d.vz:.5f}",
                            "ProjMark": "0", "DrilType": "1", 
                            "depth": f"{d.depth:.5f}", "diam": f"{d.diam:.2f}"
                        })

        # 4. Hardware (Okucia/Fittings)
        hardware_list = estimate_module_hardware_requirements(mod)
        for hw in hardware_list:
            hw_obj = ET.SubElement(mod_obj, "Obj")
            hw_obj.set("id", str(obj_id_counter))
            obj_id_counter += 1
            hw_obj.set("class", "19") # class 19 = Fittings
            hw_obj.set("name", hw.category)
            hw_obj.set("code", f"{hw.manufacturer}:{hw.category}")
            hw_obj.set("quantity", str(hw.quantity))
            hw_obj.set("unit", "0") # pcs
            hw_obj.set("txt", "false")
            hw_obj.set("cost", "0")
            
            p_props = ET.SubElement(hw_obj, "Properties")
            ET.SubElement(p_props, "property", {"name": "Manufacturer", "value": hw.manufacturer})
            ET.SubElement(p_props, "property", {"name": "Note", "value": hw.note})

    # Zapis
    tree = ET.ElementTree(root)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space="  ", level=0)
    tree.write(out, encoding="utf-8", xml_declaration=True)
    return out

def export_module_to_3dc_project_xml(module: ModuleDef, output_path: str | Path) -> Path:
    return export_project_to_3dc_xml([module], module.name or "Modul", output_path)
