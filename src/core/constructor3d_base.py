from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass
class Constructor3DBaseModule:
    base_name: str
    code: str
    name: str
    width: float
    height: float
    depth: float
    category: str
    source_file: str
    record_id: str
    variables: list[dict[str, Any]]
    materials: list[dict[str, Any]]
    picture: str
    class_id: int | None = None
    price: float | None = None

    @property
    def anchor(self) -> str:
        safe_code = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in self.code)
        return f"3DC:{self.base_name}:{safe_code}"

    def to_payload(self) -> dict[str, Any]:
        return {
            "anchor": self.anchor,
            "name": self.name or self.code,
            "width": self.width,
            "height": self.height,
            "depth": self.depth,
            "materials": "import 3D-Constructor BASE",
            "formatki": [],
            "source": "3d-constructor",
            "source_type": "ls5",
            "code3dc": self.code,
            "constructor3d": {
                "base_name": self.base_name,
                "code": self.code,
                "category": self.category,
                "source_file": self.source_file,
                "record_id": self.record_id,
                "picture": self.picture,
                "class_id": self.class_id,
                "price": self.price,
                "variables": self.variables,
                "materials": self.materials,
            },
        }


def _tokenize(text: str) -> Iterable[Any]:
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c.isspace() or c == "'":
            i += 1
            continue
        if c in "()":
            yield c
            i += 1
            continue
        if c == '"':
            i += 1
            out: list[str] = []
            while i < n:
                if text[i] == "\\" and i + 1 < n:
                    out.append(text[i + 1])
                    i += 2
                    continue
                if text[i] == '"':
                    i += 1
                    break
                out.append(text[i])
                i += 1
            yield ("str", "".join(out))
            continue
        j = i
        while j < n and not text[j].isspace() and text[j] not in "()":
            j += 1
        yield text[i:j]
        i = j


def _atom(token: Any) -> Any:
    if isinstance(token, tuple):
        return token[1]
    try:
        raw = str(token)
        if any(ch in raw for ch in ".eE"):
            return float(raw)
        return int(raw)
    except (TypeError, ValueError):
        return token


def _parse_lisp_table(text: str) -> list[Any]:
    tokens = list(_tokenize(text))
    pos = 0

    def parse_one() -> Any:
        nonlocal pos
        if pos >= len(tokens):
            return None
        if tokens[pos] != "(":
            value = _atom(tokens[pos])
            pos += 1
            return value
        pos += 1
        items: list[Any] = []
        while pos < len(tokens) and tokens[pos] != ")":
            items.append(parse_one())
        if pos < len(tokens):
            pos += 1
        return items

    result = parse_one()
    return result if isinstance(result, list) else []


def _read_ls5(path: Path) -> list[Any]:
    return _parse_lisp_table(path.read_text(encoding="cp1251", errors="replace"))


def _field_names(header: list[Any]) -> list[str]:
    names: list[str] = []
    for item in header:
        if isinstance(item, list) and item:
            names.append(str(item[0]))
        else:
            names.append(str(item))
    return names


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _var_map(raw: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(raw, list):
        return out
    for row in raw:
        if not isinstance(row, list) or not row:
            continue
        key = str(row[0]).strip()
        if not key:
            continue
        out[key] = {
            "name": key,
            "expression": str(row[1]) if len(row) > 1 else "",
            "value": _as_float(row[2]) if len(row) > 2 else 0.0,
            "description": str(row[3]) if len(row) > 3 else "",
        }
    return out


def _pick_var(vars_by_name: dict[str, dict[str, Any]], names: list[str], default: float) -> float:
    for name in names:
        if name in vars_by_name:
            return _as_float(vars_by_name[name].get("value"), default)
    return default


def _list_dicts(raw: Any, keys: list[str]) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, list):
            continue
        row = {}
        for idx, key in enumerate(keys):
            row[key] = item[idx] if idx < len(item) else None
        rows.append(row)
    return rows


def _section_paths(sections: Any) -> dict[int, str]:
    if not isinstance(sections, list):
        return {}
    nodes: dict[int, tuple[int, str]] = {}
    for row in sections:
        if isinstance(row, list) and len(row) >= 3:
            try:
                nodes[int(row[0])] = (int(row[1]), str(row[2]))
            except (TypeError, ValueError):
                continue

    def build(node_id: int) -> str:
        seen: set[int] = set()
        labels: list[str] = []
        current = node_id
        while current in nodes and current not in seen:
            seen.add(current)
            parent, label = nodes[current]
            if label:
                labels.append(label)
            if parent == current or parent not in nodes:
                break
            current = parent
        return " / ".join(reversed(labels))

    return {node_id: build(node_id) for node_id in nodes}


def parse_ls5_modules(path: str | Path, base_name: str | None = None) -> list[Constructor3DBaseModule]:
    ls5_path = Path(path)
    table = _read_ls5(ls5_path)
    if len(table) < 7 or not isinstance(table[2], list):
        return []

    fields = _field_names(table[2])
    index = {name: i for i, name in enumerate(fields)}
    if "LISTV" not in index:
        return []

    base = base_name or ls5_path.parents[1].name
    sections = _section_paths(table[4] if len(table) > 4 else [])
    modules: list[Constructor3DBaseModule] = []

    for record in table[5:]:
        if not isinstance(record, list):
            continue
        offset = 1 if len(record) > len(fields) else 0

        def value(field: str, default: Any = "") -> Any:
            pos = index.get(field)
            if pos is None:
                return default
            if pos >= 4:
                pos += offset
            return record[pos] if pos < len(record) else default

        vars_by_name = _var_map(value("LISTV", []))
        if not vars_by_name:
            continue

        width = _pick_var(vars_by_name, ["L", "LB", "!X"], 600.0)
        height = _pick_var(vars_by_name, ["H", "H_", "Z", "!Z"], 720.0)
        depth = _pick_var(vars_by_name, ["W", "WB", "W_", "Y", "!Y"], 560.0)

        code_pairs: list[tuple[str, str]] = []
        for code_key, name_key in (("SHIFR", "NAME"), ("SHIFR2", "NAME2")):
            code = str(value(code_key, "") or "").strip()
            if not code or code.lower() == "nil":
                continue
            name = str(value(name_key, "") or "").strip()
            code_pairs.append((code, name))

        seen_codes: set[str] = set()
        for code, name in code_pairs:
            if code in seen_codes:
                continue
            seen_codes.add(code)
            section_id = int(record[0]) if record and isinstance(record[0], int) else 0
            modules.append(
                Constructor3DBaseModule(
                    base_name=base,
                    code=code,
                    name=name or code,
                    width=width,
                    height=height,
                    depth=depth,
                    category=sections.get(section_id, ""),
                    source_file=str(ls5_path),
                    record_id=str(record[4] if len(record) > len(fields) else value("MODEL", "")),
                    variables=list(vars_by_name.values()),
                    materials=_list_dicts(value("LMAT", []), ["key", "role", "material_id", "material"]),
                    picture=str(value("SLD", "")),
                    class_id=int(value("KLASS")) if isinstance(value("KLASS"), int) else None,
                    price=_as_float(value("CENA"), 0.0) if "CENA" in index else None,
                )
            )

    return modules


def scan_constructor3d_base(root: str | Path, table_name: str = "tab52.ls5") -> list[Constructor3DBaseModule]:
    root_path = Path(root)
    modules: list[Constructor3DBaseModule] = []
    for path in root_path.rglob(table_name):
        base_name = ""
        try:
            base_name = path.relative_to(root_path).parts[0]
        except Exception:
            base_name = path.parents[1].name
        modules.extend(parse_ls5_modules(path, base_name=base_name))
    return modules
