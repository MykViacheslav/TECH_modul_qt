from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from src.domain.project_model import ProjectGibLabResult, ProjectModel


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value or "").strip().replace(",", "."))
    except Exception:
        return float(default)


def build_giblab_result_from_project_file(
    result_path: str | Path,
    theory_rows: list[dict[str, Any]] | None = None,
) -> ProjectGibLabResult:
    path = Path(result_path)
    if not path.exists():
        raise FileNotFoundError(f"Nie znaleziono wyniku GiB Lab: {path}")

    root = ET.parse(path).getroot()
    material_amount = 0.0
    parts_amount = 0.0
    waste_amount = 0.0

    for elem in root.iter():
        for key, raw in elem.attrib.items():
            token = str(key or "").strip().lower()
            val = _to_float(raw, 0.0)
            if val == 0.0:
                continue
            if "cmaterialamountp" in token:
                material_amount += val
            elif "cpartsamountp" in token:
                parts_amount += val
            elif "cwasteamountp" in token:
                waste_amount += val

    if material_amount <= 0.0 and parts_amount <= 0.0 and waste_amount <= 0.0:
        raise ValueError(
            "Nie znaleziono jawnych pol cMaterialAmountP / cPartsAmountP / cWasteAmountP."
        )

    theory_material = 0.0
    if isinstance(theory_rows, list):
        for row in theory_rows:
            if not isinstance(row, dict):
                continue
            theory_material += _to_float(row.get("material_cost", 0.0), 0.0)

    utilization = 0.0
    if material_amount > 0.0:
        utilization = max(0.0, min(100.0, (parts_amount / material_amount) * 100.0))

    return ProjectGibLabResult(
        result_path=str(path),
        result_kind="giblab_project",
        real_sheets_count=int(round(material_amount)) if material_amount > 0.0 else 0,
        real_area_m2=float(parts_amount),
        real_edgeband_mb=0.0,
        scrap_m2=float(waste_amount),
        leftovers=[],
        difference_vs_theory={
            "material_total": float(material_amount - theory_material),
            "theory_material_total": float(theory_material),
            "utilization_pct": float(utilization),
            "parts_amount": float(parts_amount),
            "waste_amount": float(waste_amount),
        },
    )


def attach_giblab_result(project_model: ProjectModel, result: ProjectGibLabResult) -> ProjectModel:
    project_model.giblab_result = result
    return project_model
