from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import ast
import math
import re
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
    cnc_data: str | None = None
    edges: dict[str, str] | None = None
    technology_summary: dict[str, Any] | None = None


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
class ImportModuleData:
    name: str
    code: str
    width_mm: float
    height_mm: float
    depth_mm: float
    x_pos: float = 0.0
    y_pos: float = 0.0
    z_pos: float = 0.0


@dataclass(frozen=True)
class Constructor3dcQuoteImportData:
    summary: ImportProjectSummary
    control_rows: list[ImportControlRow]
    modules: list[ImportModuleData] | None = None


SHEET_CLASSES: set[str] = {"18", "34", "114", "146"}
FRONT_CLASSES: set[str] = {"50", "82", "200"}
HARDWARE_CLASSES: set[str] = {"19"}
FASTENER_CLASSES: set[str] = {"51"}
OPERATION_CLASSES: set[str] = {"6"}

DRILL_FACE_TAGS: set[str] = {"bf"}
DRILL_EDGE_TAGS: set[str] = {"br", "bl", "bt", "bb"}
DRILL_TAGS: set[str] = DRILL_FACE_TAGS | DRILL_EDGE_TAGS
GROOVE_TAGS: set[str] = {"gr"}
MILL_START_TAGS: set[str] = {"ms"}
MILL_LINE_TAGS: set[str] = {"ml"}
MILL_ARC_TAGS: set[str] = {"mac"}


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


def _safe_eval_expr(expr: str, variables: dict[str, float]) -> float:
    text = str(expr or "").strip()
    if not text:
        return 0.0
    text = text.replace(",", ".")

    def _eval_node(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        if isinstance(node, ast.Num):
            return float(node.n)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            return 0.0
        if isinstance(node, ast.Name):
            return float(variables.get(node.id, 0.0))
        if isinstance(node, ast.Attribute):
            base_name = getattr(node.value, "id", "") if hasattr(node, "value") else ""
            combined = f"{base_name}.{node.attr}" if base_name else node.attr
            return float(variables.get(combined, 0.0))
        if isinstance(node, ast.UnaryOp):
            value = _eval_node(node.operand)
            if isinstance(node.op, ast.UAdd):
                return value
            if isinstance(node.op, ast.USub):
                return -value
            return 0.0
        if isinstance(node, ast.BinOp):
            left = _eval_node(node.left)
            right = _eval_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if abs(right) < 1e-9:
                    return 0.0
                return left / right
            if isinstance(node.op, ast.Pow):
                return left**right
            return 0.0
        return 0.0

    try:
        tree = ast.parse(text, mode="eval")
    except Exception:
        return _to_float(text, 0.0)
    try:
        return float(_eval_node(tree))
    except Exception:
        return _to_float(text, 0.0)


def _to_number_list(values: set[float]) -> list[float]:
    out: list[float] = []
    for value in sorted(values):
        rounded = round(float(value), 4)
        if abs(rounded - round(rounded)) < 1e-9:
            out.append(float(int(round(rounded))))
        else:
            out.append(rounded)
    return out


def _infer_part_type(section: str, name: str = "") -> str:
    if section == "Formatka":
        return "panel"
    if section == "Front":
        return "front"
    if section == "Okucie":
        return "hardware"
    if section == "Lacznik":
        return "fastener"
    if section == "Operacja":
        return "operation"
    raw = str(name or "").lower()
    if "front" in raw:
        return "front"
    if "plyt" in raw or "panel" in raw:
        return "panel"
    return "part"


def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return float(math.hypot(x2 - x1, y2 - y1))


def _arc_length_from_cmd(
    start_xy: tuple[float, float] | None,
    end_xy: tuple[float, float] | None,
    center_xy: tuple[float, float] | None,
) -> float:
    if not start_xy or not end_xy or not center_xy:
        return 0.0
    sx, sy = start_xy
    ex, ey = end_xy
    cx, cy = center_xy
    radius_start = _distance(sx, sy, cx, cy)
    radius_end = _distance(ex, ey, cx, cy)
    radius = (radius_start + radius_end) / 2.0
    if radius <= 0.0:
        return 0.0
    v1x, v1y = sx - cx, sy - cy
    v2x, v2y = ex - cx, ey - cy
    n1 = math.hypot(v1x, v1y)
    n2 = math.hypot(v2x, v2y)
    if n1 <= 0.0 or n2 <= 0.0:
        return 0.0
    dot = (v1x * v2x + v1y * v2y) / (n1 * n2)
    dot = max(-1.0, min(1.0, dot))
    angle = math.acos(dot)
    return float(radius * angle)


def _iter_program_commands(node: ET.Element):
    for child in list(node):
        if child.tag == "else":
            continue
        if child.tag == "if":
            for nested in _iter_program_commands(child):
                yield nested
            continue
        yield child
        for nested in _iter_program_commands(child):
            yield nested


def _build_technology_summary(
    *,
    section: str,
    part_name: str,
    material_name: str,
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    quantity: float,
    program_xml_list: list[str],
) -> dict[str, Any]:
    drill_total = 0
    drill_face = 0
    drill_edge = 0
    drill_diameters: set[float] = set()
    drill_depths: set[float] = set()
    groove_count = 0
    groove_total_length = 0.0
    groove_depths: set[float] = set()
    groove_tool_widths: set[float] = set()
    milling_count = 0
    milling_total_path = 0.0
    milling_tool_diameters: set[float] = set()
    milling_depths: set[float] = set()
    milling_arc_count = 0
    milling_line_count = 0
    tool_names: set[str] = set()
    tool_diameters: set[float] = set()

    for program_xml in program_xml_list:
        raw = str(program_xml or "").strip()
        if not raw:
            continue
        try:
            program_root = ET.fromstring(raw)
        except Exception:
            continue

        vars_map: dict[str, float] = {
            "dx": _to_float(program_root.attrib.get("dx", ""), 0.0),
            "dy": _to_float(program_root.attrib.get("dy", ""), 0.0),
            "dz": _to_float(program_root.attrib.get("dz", ""), 0.0),
            "tool.dia": 0.0,
        }
        tool_map: dict[str, float] = {}
        for tool in program_root.findall(".//tool"):
            t_name = str(tool.attrib.get("name", "") or "").strip()
            t_dia = _to_float(tool.attrib.get("d", ""), 0.0)
            if t_name:
                tool_names.add(t_name)
                tool_map[t_name] = t_dia
            if t_dia > 0.0:
                tool_diameters.add(t_dia)

        for var in program_root.findall(".//var"):
            v_name = str(var.attrib.get("name", "") or "").strip()
            v_expr = str(var.attrib.get("expr", "") or "").strip()
            if not v_name:
                continue
            vars_map[v_name] = _safe_eval_expr(v_expr, vars_map)

        current_mill_xy: tuple[float, float] | None = None
        for cmd in _iter_program_commands(program_root):
            tag = str(cmd.tag or "").strip().lower()
            cmd_tool_name = str(cmd.attrib.get("name", "") or "").strip()
            cmd_tool_dia = 0.0
            if cmd_tool_name:
                tool_names.add(cmd_tool_name)
                cmd_tool_dia = _to_float(tool_map.get(cmd_tool_name), 0.0)
                if cmd_tool_dia <= 0.0:
                    cmd_tool_dia = _safe_eval_expr(str(cmd.attrib.get("t", "") or ""), vars_map)
                if cmd_tool_dia > 0.0:
                    tool_diameters.add(cmd_tool_dia)

            if tag in DRILL_TAGS:
                drill_total += 1
                if tag in DRILL_FACE_TAGS:
                    drill_face += 1
                else:
                    drill_edge += 1
                depth = _safe_eval_expr(str(cmd.attrib.get("dp", "") or ""), vars_map)
                if depth > 0.0:
                    drill_depths.add(depth)
                if cmd_tool_dia <= 0.0:
                    cmd_tool_dia = _safe_eval_expr(str(cmd.attrib.get("d", "") or ""), vars_map)
                if cmd_tool_dia > 0.0:
                    drill_diameters.add(cmd_tool_dia)
                continue

            if tag in GROOVE_TAGS:
                groove_count += 1
                x1 = _safe_eval_expr(str(cmd.attrib.get("x1", "") or ""), vars_map)
                y1 = _safe_eval_expr(str(cmd.attrib.get("y1", "") or ""), vars_map)
                x2 = _safe_eval_expr(str(cmd.attrib.get("x2", "") or ""), vars_map)
                y2 = _safe_eval_expr(str(cmd.attrib.get("y2", "") or ""), vars_map)
                groove_total_length += _distance(x1, y1, x2, y2)
                depth = _safe_eval_expr(str(cmd.attrib.get("dp", "") or ""), vars_map)
                if depth > 0.0:
                    groove_depths.add(depth)
                groove_width = _safe_eval_expr(str(cmd.attrib.get("t", "") or ""), vars_map)
                if groove_width > 0.0:
                    groove_tool_widths.add(groove_width)
                    tool_diameters.add(groove_width)
                continue

            if tag in MILL_START_TAGS:
                milling_count += 1
                mx = _safe_eval_expr(str(cmd.attrib.get("x", "") or ""), vars_map)
                my = _safe_eval_expr(str(cmd.attrib.get("y", "") or ""), vars_map)
                current_mill_xy = (mx, my)
                depth = _safe_eval_expr(str(cmd.attrib.get("dp", "") or ""), vars_map)
                if depth > 0.0:
                    milling_depths.add(depth)
                if cmd_tool_dia > 0.0:
                    milling_tool_diameters.add(cmd_tool_dia)
                continue

            if tag in MILL_LINE_TAGS:
                milling_line_count += 1
                nx = _safe_eval_expr(str(cmd.attrib.get("x", "") or ""), vars_map)
                ny = _safe_eval_expr(str(cmd.attrib.get("y", "") or ""), vars_map)
                if current_mill_xy is not None:
                    milling_total_path += _distance(current_mill_xy[0], current_mill_xy[1], nx, ny)
                current_mill_xy = (nx, ny)
                continue

            if tag in MILL_ARC_TAGS:
                milling_arc_count += 1
                ex = _safe_eval_expr(str(cmd.attrib.get("x", "") or ""), vars_map)
                ey = _safe_eval_expr(str(cmd.attrib.get("y", "") or ""), vars_map)
                cx = _safe_eval_expr(str(cmd.attrib.get("cx", "") or ""), vars_map)
                cy = _safe_eval_expr(str(cmd.attrib.get("cy", "") or ""), vars_map)
                milling_total_path += _arc_length_from_cmd(current_mill_xy, (ex, ey), (cx, cy))
                current_mill_xy = (ex, ey)
                continue

    operation_count_total = int(drill_total + groove_count + milling_count + milling_line_count + milling_arc_count)
    operation_type_count = int(
        (1 if drill_total > 0 else 0)
        + (1 if groove_count > 0 else 0)
        + (1 if (milling_count > 0 or milling_line_count > 0 or milling_arc_count > 0) else 0)
    )
    tool_count_unique = len(tool_names | {f"dia:{d}" for d in tool_diameters})
    cnc_complexity_score = int(
        (drill_total * 1)
        + (groove_count * 2)
        + (milling_count * 2)
        + tool_count_unique
        + (2 if milling_arc_count > 0 else 0)
    )

    drill_summary_text = ""
    if drill_total > 0:
        dia_text = ", ".join(f"Ø{d:g}" for d in _to_number_list(drill_diameters))
        depth_text = ", ".join(f"{d:g}" for d in _to_number_list(drill_depths))
        drill_summary_text = (
            f"{drill_total} drills"
            + (f" [{dia_text}]" if dia_text else "")
            + (f" depth {depth_text}" if depth_text else "")
        )

    groove_summary_text = ""
    if groove_count > 0:
        groove_summary_text = (
            f"{groove_count} grooves, total {round(groove_total_length, 1):g} mm"
            + (
                f", tool {', '.join(str(v).rstrip('0').rstrip('.') for v in _to_number_list(groove_tool_widths))}"
                if groove_tool_widths
                else ""
            )
        )

    milling_summary_text = ""
    if milling_count > 0 or milling_line_count > 0 or milling_arc_count > 0:
        dia_text = ", ".join(f"Ø{d:g}" for d in _to_number_list(milling_tool_diameters))
        milling_summary_text = (
            f"{milling_count} milling paths, total {round(milling_total_path, 1):g} mm"
            + (f", tools {dia_text}" if dia_text else "")
            + (f", arcs {milling_arc_count}" if milling_arc_count else "")
        )

    tool_summary_text = ""
    if tool_names or tool_diameters:
        names = sorted(tool_names)
        diams = [f"Ø{d:g}" for d in _to_number_list(tool_diameters)]
        tool_summary_text = ", ".join(names + diams)

    return {
        "part_name": part_name,
        "part_type": _infer_part_type(section, part_name),
        "material_name": material_name or None,
        "length_mm": float(length_mm or 0.0),
        "width_mm": float(width_mm or 0.0),
        "thickness_mm": float(thickness_mm or 0.0),
        "quantity": float(quantity or 0.0),
        "drill_count_total": int(drill_total),
        "drill_count_face": int(drill_face),
        "drill_count_edge": int(drill_edge),
        "drill_diameters_mm": _to_number_list(drill_diameters),
        "drill_depths_mm": _to_number_list(drill_depths),
        "drill_summary_text": drill_summary_text or None,
        "groove_count": int(groove_count),
        "groove_total_length_mm": float(round(groove_total_length, 3)),
        "groove_depths_mm": _to_number_list(groove_depths),
        "groove_tool_widths_mm": _to_number_list(groove_tool_widths),
        "groove_summary_text": groove_summary_text or None,
        "milling_count": int(milling_count),
        "milling_total_path_length_mm": float(round(milling_total_path, 3)) if milling_total_path > 0 else 0.0,
        "milling_length_estimated_mm": float(round(milling_total_path, 3)) if milling_total_path > 0 else 0.0,
        "milling_tool_diameters_mm": _to_number_list(milling_tool_diameters),
        "milling_depths_mm": _to_number_list(milling_depths),
        "milling_arc_count": int(milling_arc_count),
        "milling_line_count": int(milling_line_count),
        "milling_summary_text": milling_summary_text or None,
        "tool_names": sorted(tool_names),
        "tool_diameters_mm": _to_number_list(tool_diameters),
        "tool_count_unique": int(tool_count_unique),
        "tool_summary_text": tool_summary_text or None,
        "operation_count_total": int(operation_count_total),
        "operation_type_count": int(operation_type_count),
        "has_drilling": bool(drill_total > 0),
        "has_grooving": bool(groove_count > 0),
        "has_milling": bool(milling_count > 0 or milling_line_count > 0 or milling_arc_count > 0),
        "cnc_complexity_score": int(cnc_complexity_score),
    }


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

    # Map operations to part ids (many operations may be linked to one part).
    part_cnc_map: dict[str, list[str]] = {}
    for op in root.findall(".//operation[@typeId='XNC']"):
        program_xml = str(op.get("program", "") or "")
        for p_ref in op.findall("part"):
            pid = str(p_ref.get("id", "") or "").strip()
            if pid:
                part_cnc_map.setdefault(pid, []).append(program_xml)

    project_name = str(root.attrib.get("name", "") or "").strip() or path.stem
    project_date = str(root.attrib.get("date", "") or "").strip()
    project_version = str(root.attrib.get("version", "") or "").strip()

    # Find modules (class 1 = product/assembly).
    all_modules: list[ImportModuleData] = []
    project_objs = root.findall(".//ProjectStructure/Obj")
    for obj in project_objs:
        cls = str(obj.attrib.get("class", "") or "").strip()
        if cls != "1":
            continue

        name = str(obj.attrib.get("name", "") or "").strip()
        code = str(obj.attrib.get("code", "") or "").strip()
        l = _to_float(obj.attrib.get("dl", obj.attrib.get("dtl", "0")), 0.0)
        w = _to_float(obj.attrib.get("dw", obj.attrib.get("dtw", "0")), 0.0)
        h = _to_float(obj.attrib.get("dtt", "0"), 0.0)

        all_modules.append(
            ImportModuleData(
                name=name,
                code=code,
                width_mm=l,
                height_mm=w,
                depth_mm=h,
            )
        )

    # Fallback for files without ProjectStructure module nodes.
    if not all_modules:
        prefix_map: dict[str, dict[str, Any]] = {}
        for obj in root.findall(".//part"):
            pcode = str(obj.get("part.code", "") or "")
            match = re.match(r"(ASS[0-9]+\.[0-9]+)", pcode)
            if match:
                prefix = match.group(1)
                if prefix not in prefix_map:
                    prefix_map[prefix] = {
                        "name": obj.get("part.name", prefix),
                        "max_l": 0.0,
                        "max_w": 0.0,
                        "max_t": 0.0,
                    }

                l = _to_float(obj.get("l", 0), 0.0)
                w = _to_float(obj.get("w", 0), 0.0)
                t = _to_float(obj.get("t", 0), 0.0)
                prefix_map[prefix]["max_l"] = max(prefix_map[prefix]["max_l"], l)
                prefix_map[prefix]["max_w"] = max(prefix_map[prefix]["max_w"], w)
                prefix_map[prefix]["max_t"] = max(prefix_map[prefix]["max_t"], t)

        for pr, data in prefix_map.items():
            all_modules.append(
                ImportModuleData(
                    name=str(data["name"]).split(" - ")[0],
                    code=pr,
                    width_mm=float(data["max_l"]),
                    height_mm=float(data["max_w"]),
                    depth_mm=float(data["max_t"]),
                )
            )

    if all_modules:
        module_name = all_modules[0].name
        module_l = all_modules[0].width_mm
        module_w = all_modules[0].height_mm
        module_h = all_modules[0].depth_mm
    else:
        module_name = "Projekt pusty"
        module_l, module_w, module_h = 0.0, 0.0, 0.0

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

        edges = {
            "top": obj.get("elt") or obj.get("bandT"),
            "bottom": obj.get("elb") or obj.get("bandB"),
            "left": obj.get("ell") or obj.get("bandL"),
            "right": obj.get("elr") or obj.get("bandR"),
        }

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
            if section == "Okucie":
                count_okucia += 1
            if section == "Lacznik":
                count_laczniki += 1
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

        cnc_programs = part_cnc_map.get(source_id, [])
        cnc_data_raw = "\n".join([str(item or "") for item in cnc_programs if str(item or "").strip()])
        technology_summary = _build_technology_summary(
            section=section,
            part_name=name,
            material_name=material_label,
            length_mm=length,
            width_mm=width,
            thickness_mm=thickness,
            quantity=qty,
            program_xml_list=cnc_programs,
        )

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
                cnc_data=cnc_data_raw or None,
                edges=edges,
                technology_summary=technology_summary,
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
    return Constructor3dcQuoteImportData(summary=summary, control_rows=control_rows, modules=all_modules)
