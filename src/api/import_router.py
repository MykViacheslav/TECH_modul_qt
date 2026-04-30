from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict, Any
import os
import tempfile
import subprocess
from src.services.constructor_3dc_quote_import_service import parse_3dc_project_for_quote_import
from .data_manager import data_manager

router = APIRouter(prefix="/import-3d", tags=["import"])

@router.post("/parse")
async def parse_project_file(file: UploadFile = File(...)):
    """Wgrywa plik .project i zwraca dane do zmapowania."""
    if not file.filename.endswith(".project"):
        raise HTTPException(status_code=400, detail="Tylko pliki .project są obsługiwane.")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".project") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Permanent storage
    storage_dir = os.path.join(os.getcwd(), "src", "storage", "projects")
    os.makedirs(storage_dir, exist_ok=True)
    permanent_path = os.path.join(storage_dir, file.filename)
    
    with open(permanent_path, "wb") as f:
        f.write(content)

    try:
        import_data = parse_3dc_project_for_quote_import(permanent_path)
        
        # Przygotuj dane dla frontendu
        rows = []
        for row in import_data.control_rows:
            rows.append({
                "section": row.section,
                "code": row.code,
                "name": row.name,
                "qty": row.qty,
                "length_mm": row.length_mm,
                "width_mm": row.width_mm,
                "thickness_mm": row.thickness_mm,
                "material_original": row.material_import,
                "status": row.status,
                "source_id": row.source_id,
                "unit_cost": row.unit_cost,
                "cnc_data": row.cnc_data,
                "edges": row.edges,
                "technology_summary": row.technology_summary,
            })

        modules_out = []
        if import_data.modules:
            for m in import_data.modules:
                modules_out.append({
                    "name": m.name,
                    "code": m.code,
                    "width": m.width_mm,
                    "height": m.height_mm,
                    "depth": m.depth_mm,
                    "x": m.x_pos,
                    "y": m.y_pos,
                    "z": m.z_pos
                })
            
        return {
            "summary": {
                "name": import_data.summary.project_name,
                "module": import_data.summary.module_name,
                "area_m2": import_data.summary.total_area_m2,
                "edge_mb": import_data.summary.total_edgeband_mb,
                "parts_count": import_data.summary.formatki_count + import_data.summary.fronty_count,
                "file_path": permanent_path
            },
            "rows": rows,
            "modules": modules_out
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd parsowania: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/finalize")
async def finalize_import(payload: Dict[str, Any]):
    """Tworzy projekt w bazie na podstawie zmapowanych danych."""
    title = payload.get("title", "Import 3D")
    client_name = payload.get("client_name", "Klient z Importu")
    rows = payload.get("rows", [])
    file_path = payload.get("file_path")
    
    # 1. Stwórz projekt
    project_id = data_manager.create_project(title, client_name)
    
    # 2. Synchronizacja GitLab (jeĹ›li mamy plik)
    git_status = "Skipped"
    if file_path and os.path.exists(file_path):
        from src.services.gitlab_sync_service import git_sync_project_file
        sync_res = git_sync_project_file(file_path, f"Import projektu 3D: {title}")
        if sync_res["status"] == "ok":
            git_status = "Synced to GitLab"
        else:
            git_status = f"Git Error: {sync_res['message']}"

    # 3. Dodaj moduĹ‚y (szafki)
    added_count = 0
    for row in rows:
        # InteresujÄ… nas gĹ‚Ăłwnie Formatki i Fronty jako fizyczne elementy
        if row.get("section") not in {"Formatka", "Front"}:
            continue
            
        material_name = row.get("material_mapped") or row.get("material_original")
        material_id = None
        
        if material_name:
            mat = data_manager.get_material_by_name(material_name)
            if mat:
                material_id = mat["id"]
        
        # Dodaj moduĹ‚
        data_manager.add_project_module(
            project_id=project_id,
            name=row.get("name", "Bez nazwy"),
            width=int(row.get("width_mm", 0)),
            height=int(row.get("height_mm", 0)),
            depth=int(row.get("thickness_mm", 0)), # W tym przypadku gĹ‚Ä™bokoĹ›Ä‡ to gruboĹ›Ä‡ formatki/moduĹ‚u
            material_id=material_id
        )
        added_count += 1
        
    return {
        "status": "success", 
        "project_id": project_id, 
        "modules_added": added_count,
        "gitlab": git_status
    }
