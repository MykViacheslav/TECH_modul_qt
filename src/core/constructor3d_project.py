from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET


def _float_attr(node: ET.Element, name: str, default: float = 0.0) -> float:
    try:
        return float(str(node.attrib.get(name, default)).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _has_parent(node: ET.Element) -> bool:
    parent = str(node.attrib.get("parent", "") or "").strip()
    return bool(parent)


def import_project_modules(path: str | Path) -> list[dict]:
    """
    Read 3D-Constructor .project XML and return top-level cabinet assemblies.

    3D-Constructor stores module dimensions on assembly objects (class="1") as:
    dtl = X/length, dtw = Y/depth/width, dtt = Z/height.
    """
    tree = ET.parse(str(path))
    root = tree.getroot()
    project_name = str(root.attrib.get("name", "") or Path(path).stem)

    assemblies = [node for node in root.findall(".//Obj") if node.attrib.get("class") == "1"]
    top_level = [node for node in assemblies if not _has_parent(node)]
    if not top_level:
        top_level = assemblies

    modules: list[dict] = []
    for i, node in enumerate(top_level, 1):
        code = str(node.attrib.get("code", "") or "").strip()
        name = str(node.attrib.get("name", "") or "").strip()
        length = _float_attr(node, "dtl") or _float_attr(node, "l") or 600.0
        width = _float_attr(node, "dtw") or _float_attr(node, "w") or 560.0
        height = _float_attr(node, "dtt") or 720.0
        modules.append(
            {
                "code": code or f"{project_name}_{i}",
                "name": name or code or f"{project_name} {i}",
                "length": length,
                "width": width,
                "height": height,
                "x": (i - 1) * (length + 20.0),
                "y": 0.0,
                "z": 0.0,
                "angle": 0.0,
                "coordinate_system": -1,
                "source": "3d-constructor",
                "source_project": str(path),
                "source_obj_id": str(node.attrib.get("id", "") or ""),
            }
        )
    return modules
