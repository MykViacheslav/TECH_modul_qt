from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


class Constructor3dcQuoteImportError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImportControlRow:
    section: str
    code: str
    name: str
    qty: float
    length_mm: float
    width_mm: float
    thickness_mm: float
    material_import: str
    edgeband_desc: str
    edgeband_mb: float
    area_m2: float
    status: str
    source: str
    source_id: str
    unit_cost: float


@dataclass(frozen=True)
class ImportProjectSummary:
    project_name: str
    project_date: str
    project_version: str
    module_name: str
    module_length_mm: float
    module_width_mm: float
    module_height_mm: float
    formatki_count: int
    fronty_count: int
    okucia_count: int
    laczniki_count: int
    operations_count: int
    total_area_m2: float
    total_edgeband_mb: float
    import_status: str


@dataclass(frozen=True)
class Constructor3dcQuoteImportData:
    summary: ImportProjectSummary
    control_rows: list[ImportControlRow]


SHEET_CLASSES: set[str] = {"18", "34", "114", "146"}
FRONT_CLASSES: set[str] = {"50", "82", "200"}
HARDWARE_CLASSES: set[str] = {"19"}
FASTENER_CLASSES: set[str] = {"51"}
OPERATION_CLASSES: set[str] = {"6"}


def _to_float(value: Any, default: float = 0.0) -> float:
    raw = str(value or "").strip().replace(",", ".")
    if not raw:
        return float(default)
    try:
        return float(raw)
    except Exception:
        return float(default)


def _normalize_material_label(material: dict[str, str], fallback: str) -> str:
    code = str(material.get("code", "") or "").strip()
    name = str(material.get("name", "") or "").strip()
    if code and name:
        return f"{code} | {name}"
    return code or name or fallback


def _parse_material_dictionary(root: ET.Element) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for item in root.findall(".//Dictionary/Materials/Item"):
        material_id = str(item.attrib.get("id", "") or "").strip()
        if not material_id:
            continue
        out[material_id] = {
            "id": material_id,
            "type": str(item.attrib.get("type", "") or "").strip().lower(),
            "code": str(item.attrib.get("code", "") or "").strip(),
            "name": str(item.attrib.get("name", "") or "").strip(),
            "thick": str(item.attrib.get("thick", "") or "").strip(),
            "cost": str(item.attrib.get("cost", "") or "").strip(),
        }
    return out


def _parse_classes(root: ET.Element) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in root.findall(".//Dictionary/Classes/Item"):
        class_id = str(item.attrib.get("id", "") or "").strip()
        if not class_id:
            continue
        out[class_id] = str(item.attrib.get("description", "") or "").strip()
    return out


def _parse_units(root: ET.Element) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in root.findall(".//Dictionary/Units/Item"):
        unit_id = str(item.attrib.get("id", "") or "").strip()
        if not unit_id:
            continue
        out[unit_id] = str(item.attrib.get("name", item.attrib.get("description", "")) or "").strip()
    return out


def _section_for_class(class_id: str) -> str:
    if class_id in SHEET_CLASSES:
        return "Formatka"
    if class_id in FRONT_CLASSES:
        return "Front"
    if class_id in HARDWARE_CLASSES:
        return "Okucie"
    if class_id in FASTENER_CLASSES:
        return "Lacznik"
    if class_id in OPERATION_CLASSES:
        return "Operacja"
    return ""


def _edge_sides_from_obj(obj: ET.Element) -> dict[str, str]:
    out: dict[str, str] = {}
    for side in ("L", "R", "T", "B"):
        band_id = str(obj.attrib.get(f"band{side}", "") or "").strip()
        if band_id:
            out[side] = band_id
    return out


def _best_dimension(obj: ET.Element, primary: str, secondary: str, tertiary: str) -> float:
    value = _to_float(obj.attrib.get(primary, ""), 0.0)
    if value > 0.0:
        return value
    value = _to_float(obj.attrib.get(secondary, ""), 0.0)
    if value > 0.0:
        return value
    return _to_float(obj.attrib.get(tertiary, ""), 0.0)


def parse_3dc_project_for_quote_import(project_path: str | Path) -> Constructor3dcQuoteImportData:
    path = Path(project_path)
    if not path.exists():
        raise FileNotFoundError(f"Nie znaleziono pliku 3D Constructor: {path}")

    try:
        root = ET.parse(path).getroot()
    except Exception as exc:
        raise Constructor3dcQuoteImportError(f"Nie mozna odczytac pliku .project: {exc}") from exc

    materials = _parse_material_dictionary(root)
    class_map = _parse_classes(root)
    unit_map = _parse_units(root)

    project_name = str(root.attrib.get("name", "") or "").strip() or path.stem
    project_date = str(root.attrib.get("date", "") or "").strip()
    project_version = str(root.attrib.get("version", "") or "").strip()

    module_name = ""
    module_l = 0.0
    module_w = 0.0
    module_h = 0.0
    for obj in root.findall(".//ProjectStructure/Obj"):
        cls = str(obj.attrib.get("class", "") or "").strip()
        if cls != "1":
            continue
        module_name = str(obj.attrib.get("name", "") or "").strip()
        module_l = _to_float(obj.attrib.get("dtl", ""), 0.0)
        module_w = _to_float(obj.attrib.get("dtw", ""), 0.0)
        module_h = _to_float(obj.attrib.get("dtt", ""), 0.0)
        break

    control_rows: list[ImportControlRow] = []
    count_formatki = 0
    count_fronty = 0
    count_okucia = 0
    count_laczniki = 0
    count_operations = 0
    total_area = 0.0
    total_edge = 0.0
    needs_mapping = False

    for obj in root.findall(".//ProjectStructure/Obj"):
        class_id = str(obj.attrib.get("class", "") or "").strip()
        section = _section_for_class(class_id)
        if not section:
            continue

        qty = _to_float(obj.attrib.get("quantity", ""), 1.0)
        if qty <= 0.0:
            qty = 1.0

        code = str(obj.attrib.get("code", "") or "").strip()
        source_id = str(obj.attrib.get("id", "") or "").strip()
        name = str(obj.attrib.get("name", "") or "").strip() or code or source_id or section
        source = str(class_map.get(class_id, f"class:{class_id}") or f"class:{class_id}")
        unit_cost = _to_float(obj.attrib.get("cost", ""), 0.0)

        length = 0.0
        width = 0.0
        thickness = 0.0
        area_m2 = 0.0
        edge_mb = 0.0
        edge_desc = ""
        material_label = ""
        status = "OK"

        material_id = str(obj.attrib.get("material", "") or "").strip()
        material_meta = materials.get(material_id, {})
        material_label = _normalize_material_label(material_meta, material_id)

        if section in {"Formatka", "Front"}:
            length = _best_dimension(obj, "dl", "dtl", "l")
            width = _best_dimension(obj, "dw", "dtw", "w")
            thickness = _to_float(obj.attrib.get("dtt", ""), 0.0)
            if thickness <= 0.0:
                thickness = _to_float(material_meta.get("thick", ""), 0.0)
            area_m2 = (max(0.0, length) * max(0.0, width) * qty) / 1_000_000.0

            sides = _edge_sides_from_obj(obj)
            edge_tokens: list[str] = []
            edge_mm_total = 0.0
            for side_key, band_id in sides.items():
                band_meta = materials.get(band_id, {})
                band_label = _normalize_material_label(band_meta, band_id)
                edge_tokens.append(f"{side_key}:{band_label}")
                if side_key in {"L", "R"}:
                    edge_mm_total += length
                elif side_key in {"T", "B"}:
                    edge_mm_total += width
            edge_mb = (edge_mm_total * qty) / 1000.0
            edge_desc = ", ".join(edge_tokens)
            total_area += area_m2
            total_edge += edge_mb
            if section == "Formatka":
                count_formatki += 1
            else:
                count_fronty += 1
            if not material_label:
                status = "Do mapowania"
                needs_mapping = True

        elif section in {"Okucie", "Lacznik"}:
            count_okucia += 1 if section == "Okucie" else 0
            count_laczniki += 1 if section == "Lacznik" else 0
            if not material_label:
                material_label = str(unit_map.get(str(obj.attrib.get("unit", "") or "").strip(), "") or "")
            if not material_label:
                status = "Do mapowania"
                needs_mapping = True

        elif section == "Operacja":
            count_operations += 1
            unit_key = str(obj.attrib.get("unit", "") or "").strip()
            material_label = str(unit_map.get(unit_key, "") or "")
            if not material_label:
                material_label = "usluga"

        control_rows.append(
            ImportControlRow(
                section=section,
                code=code,
                name=name,
                qty=qty,
                length_mm=length,
                width_mm=width,
                thickness_mm=thickness,
                material_import=material_label,
                edgeband_desc=edge_desc,
                edgeband_mb=edge_mb,
                area_m2=area_m2,
                status=status,
                source=source,
                source_id=source_id,
                unit_cost=unit_cost,
            )
        )

    summary = ImportProjectSummary(
        project_name=project_name,
        project_date=project_date,
        project_version=project_version,
        module_name=module_name,
        module_length_mm=module_l,
        module_width_mm=module_w,
        module_height_mm=module_h,
        formatki_count=count_formatki,
        fronty_count=count_fronty,
        okucia_count=count_okucia,
        laczniki_count=count_laczniki,
        operations_count=count_operations,
        total_area_m2=total_area,
        total_edgeband_mb=total_edge,
        import_status="wymaga mapowania" if needs_mapping else "OK",
    )
    return Constructor3dcQuoteImportData(summary=summary, control_rows=control_rows)
