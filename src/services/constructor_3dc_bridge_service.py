from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


SHEET_PART_CLASSES: set[str] = {"18", "34", "50", "114", "146"}


class Constructor3dcParseError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConstructorProjectPart:
    project_name: str
    obj_id: str
    obj_code: str
    name: str
    material_id: str
    material_code: str
    material_name: str
    length_l_mm: float
    length_b_mm: float
    qty: float
    edge_l: bool
    edge_p: bool
    edge_g: bool
    edge_d: bool
    notes: str

    def as_giblab_row(self) -> list[str]:
        return [
            self.project_name,
            self.material_name,
            self.obj_code or self.obj_id,
            self.name,
            _format_mm(self.length_l_mm),
            _format_mm(self.length_b_mm),
            _format_qty(self.qty),
            "1" if self.edge_l else "0",
            "1" if self.edge_p else "0",
            "1" if self.edge_g else "0",
            "1" if self.edge_d else "0",
            self.notes,
        ]

    def as_formatka_row(self, ordinal: int) -> dict[str, Any]:
        part_id = (self.obj_code or self.obj_id or f"F{ordinal:03d}").strip()
        l_val = float(self.length_l_mm)
        b_val = float(self.length_b_mm)
        qty = float(self.qty if self.qty > 0 else 1.0)
        m2 = (l_val * b_val * qty) / 1_000_000.0 if l_val > 0.0 and b_val > 0.0 else 0.0
        edge_mb = qty * (
            (l_val / 1000.0 if self.edge_l else 0.0)
            + (l_val / 1000.0 if self.edge_p else 0.0)
            + (b_val / 1000.0 if self.edge_g else 0.0)
            + (b_val / 1000.0 if self.edge_d else 0.0)
        )
        notes = " | ".join(
            part
            for part in [
                f"3dc:{self.project_name}" if self.project_name else "",
                self.material_name,
                self.notes,
            ]
            if str(part or "").strip()
        )
        return {
            "id": part_id,
            "name": self.name,
            "length_l": _format_mm(l_val),
            "length_b": _format_mm(b_val),
            "qty": qty,
            "m2": m2,
            "okleina_l": bool(self.edge_l),
            "okleina_p": bool(self.edge_p),
            "okleina_g": bool(self.edge_g),
            "okleina_d": bool(self.edge_d),
            "okleina_mb": edge_mb,
            "lakier_1s": False,
            "lakier_2s": False,
            "notes": notes,
        }


def _to_float(value: Any, default: float = 0.0) -> float:
    raw = str(value or "").strip().replace(",", ".")
    if not raw:
        return float(default)
    try:
        return float(raw)
    except Exception:
        return float(default)


def _format_mm(value: float) -> str:
    text = f"{float(value):.2f}"
    return text.rstrip("0").rstrip(".")


def _format_qty(value: float) -> str:
    text = f"{float(value):.3f}"
    return text.rstrip("0").rstrip(".")


def _band_on(value: str) -> bool:
    raw = str(value or "").strip().lower()
    if not raw:
        return False
    return raw not in {"0", "false", "none", "null", "-"}


def build_default_giblab_filename(project_name: str, when: datetime | None = None) -> str:
    dt = when or datetime.now()
    safe = "".join(ch if ch.isascii() and (ch.isalnum() or ch in ("-", "_")) else "_" for ch in str(project_name or ""))
    safe = safe.strip("_") or "projekt_3dc"
    while "__" in safe:
        safe = safe.replace("__", "_")
    return f"giblab_3dc_{safe}_{dt.strftime('%Y%m%d_%H%M%S')}.csv"


def parse_3dc_project_parts(project_path: str | Path) -> list[ConstructorProjectPart]:
    path = Path(project_path)
    if not path.exists():
        raise FileNotFoundError(f"Nie znaleziono pliku 3D Constructor: {path}")

    try:
        root = ET.parse(path).getroot()
    except Exception as exc:
        raise Constructor3dcParseError(f"Nie mozna odczytac pliku .project: {exc}") from exc

    project_name = str(root.attrib.get("name", "") or "").strip() or path.stem
    materials_by_id: dict[str, dict[str, str]] = {}
    for item in root.findall(".//Dictionary/Materials/Item"):
        material_id = str(item.attrib.get("id", "") or "").strip()
        if not material_id:
            continue
        materials_by_id[material_id] = {
            "code": str(item.attrib.get("code", "") or "").strip(),
            "name": str(item.attrib.get("name", "") or "").strip(),
            "type": str(item.attrib.get("type", "") or "").strip(),
        }

    out: list[ConstructorProjectPart] = []
    for obj in root.findall(".//ProjectStructure/Obj"):
        cls = str(obj.attrib.get("class", "") or "").strip()
        if cls not in SHEET_PART_CLASSES:
            continue

        length_l = _to_float(obj.attrib.get("l", ""), 0.0)
        length_b = _to_float(obj.attrib.get("w", ""), 0.0)
        if length_l <= 0.0:
            length_l = _to_float(obj.attrib.get("dl", ""), 0.0)
        if length_b <= 0.0:
            length_b = _to_float(obj.attrib.get("dw", ""), 0.0)
        if length_l <= 0.0 or length_b <= 0.0:
            continue

        material_id = str(obj.attrib.get("material", "") or "").strip()
        material = materials_by_id.get(material_id, {})
        material_code = str(material.get("code", "") or "").strip()
        material_name_raw = str(material.get("name", "") or "").strip()
        if material_code and material_name_raw:
            material_name = f"{material_code} | {material_name_raw}"
        else:
            material_name = material_code or material_name_raw or material_id

        obj_id = str(obj.attrib.get("id", "") or "").strip()
        obj_code = str(obj.attrib.get("code", "") or "").strip()
        obj_name = str(obj.attrib.get("name", "") or "").strip() or obj_code or obj_id or "Element"
        qty = max(0.0, _to_float(obj.attrib.get("quantity", ""), 1.0))
        if qty <= 0.0:
            qty = 1.0

        edge_l = _band_on(obj.attrib.get("bandL", ""))
        edge_p = _band_on(obj.attrib.get("bandR", ""))
        edge_g = _band_on(obj.attrib.get("bandT", ""))
        edge_d = _band_on(obj.attrib.get("bandB", ""))
        note_bits: list[str] = [f"class:{cls}"]
        if material_id:
            note_bits.append(f"material_id:{material_id}")
        if material_code:
            note_bits.append(f"material_code:{material_code}")
        notes = " | ".join(note_bits)

        out.append(
            ConstructorProjectPart(
                project_name=project_name,
                obj_id=obj_id,
                obj_code=obj_code,
                name=obj_name,
                material_id=material_id,
                material_code=material_code,
                material_name=material_name,
                length_l_mm=length_l,
                length_b_mm=length_b,
                qty=qty,
                edge_l=edge_l,
                edge_p=edge_p,
                edge_g=edge_g,
                edge_d=edge_d,
                notes=notes,
            )
        )

    return out


def export_giblab_csv_from_3dc_project(project_path: str | Path, csv_path: str | Path) -> Path:
    parts = parse_3dc_project_parts(project_path)
    if not parts:
        raise Constructor3dcParseError("Brak elementow plytowych do eksportu GibLab w pliku .project.")

    target = Path(csv_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(
            [
                "Pozycja",
                "Material",
                "ID",
                "Nazwa",
                "L_mm",
                "B_mm",
                "Sztuki",
                "Okleina_L",
                "Okleina_P",
                "Okleina_G",
                "Okleina_D",
                "Uwagi",
            ]
        )
        for part in parts:
            writer.writerow(part.as_giblab_row())
    return target


def build_formatki_rows_from_3dc_project(project_path: str | Path) -> tuple[str, list[dict[str, Any]]]:
    parts = parse_3dc_project_parts(project_path)
    if not parts:
        raise Constructor3dcParseError("Brak elementow plytowych do importu formatek w pliku .project.")
    project_name = str(parts[0].project_name or "").strip() or Path(project_path).stem
    rows = [part.as_formatka_row(idx + 1) for idx, part in enumerate(parts)]
    return project_name, rows


def build_position_payload_from_3dc_project(project_path: str | Path) -> dict[str, Any]:
    parts = parse_3dc_project_parts(project_path)
    if not parts:
        raise Constructor3dcParseError("Brak elementow plytowych do importu pozycji w pliku .project.")

    project_name = str(parts[0].project_name or "").strip() or Path(project_path).stem
    formatki_rows = [part.as_formatka_row(idx + 1) for idx, part in enumerate(parts)]

    area_by_material: dict[str, float] = {}
    for part in parts:
        material_name = str(part.material_name or "").strip() or str(part.material_id or "").strip() or "[brak]"
        area = max(0.0, float(part.length_l_mm)) * max(0.0, float(part.length_b_mm)) * max(0.0, float(part.qty))
        area_by_material[material_name] = area_by_material.get(material_name, 0.0) + area

    material_hint = ""
    if area_by_material:
        material_hint = max(area_by_material.items(), key=lambda item: item[1])[0]

    return {
        "project_name": project_name,
        "material_name_hint": material_hint,
        "formatki_rows": formatki_rows,
        "parts_count": len(parts),
    }
