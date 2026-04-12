from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from src.domain.material_profile_models import MaterialProfileDef
from src.domain.material_profile_registry import build_default_material_profiles, get_default_material_profile
from src.storage.data_paths import data_dir


@dataclass(frozen=True)
class MaterialDef:
    key: str
    name_pl: str
    thickness_mm: float
    core: Optional[Dict] = None
    skins_left: List[Dict] = field(default_factory=list)
    skins_right: List[Dict] = field(default_factory=list)
    manufacturer: str = ""
    material_type: str = ""
    material_group: str = ""
    finish_group: str = ""
    price_pln_per_m2: float = 0.0
    price_note: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "skins_left", list(self.skins_left or []))
        object.__setattr__(self, "skins_right", list(self.skins_right or []))

    @property
    def composite_enabled(self) -> bool:
        return bool(self.core or self.skins_left or self.skins_right)

    @property
    def core_thickness_mm(self) -> float:
        return float((self.core or {}).get("thickness_mm", 0.0) or 0.0)

    @property
    def left_facing_thickness_mm(self) -> float:
        if not self.skins_left:
            return 0.0
        return float((self.skins_left[0] or {}).get("thickness_mm", 0.0) or 0.0)

    @property
    def right_facing_thickness_mm(self) -> float:
        if not self.skins_right:
            return 0.0
        return float((self.skins_right[0] or {}).get("thickness_mm", 0.0) or 0.0)


@dataclass(frozen=True)
class EdgeBandDef:
    key: str
    name_pl: str
    thickness_mm: float = 0.0
    manufacturer: str = ""
    edgeband_type: str = ""
    material_group: str = ""
    price_pln_per_m: float = 0.0
    price_note: str = ""


@dataclass(frozen=True)
class HardwareDef:
    key: str
    name_pl: str
    manufacturer: str = ""
    category: str = ""
    item_type: str = ""
    unit: str = "szt"
    price_pln: float = 0.0
    price_note: str = ""


class CatalogStoreJson:
    """
    Stala baza dla:
    - materialow
    - oklein
    - okuc

    Plik: data/catalog.json
    """

    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "catalog.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

        if not self._path.exists():
            self._path.write_text(
                json.dumps(self._default_catalog(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        self._ensure_catalog_schema()

    def list_materials(self) -> List[MaterialDef]:
        data = self._read()
        out: List[MaterialDef] = []
        for item in (data.get("materials") or []):
            try:
                normalized = self._normalize_section_row("materials", item)
                out.append(
                    MaterialDef(
                        key=str(normalized["key"]),
                        name_pl=str(normalized.get("name_pl", normalized["key"])),
                        thickness_mm=self._material_total_thickness_mm(normalized),
                        core=dict(normalized.get("core") or {}) or None,
                        skins_left=[dict(layer) for layer in (normalized.get("skins_left") or []) if isinstance(layer, dict)],
                        skins_right=[dict(layer) for layer in (normalized.get("skins_right") or []) if isinstance(layer, dict)],
                        manufacturer=str(normalized.get("manufacturer", "") or ""),
                        material_type=str(normalized.get("material_type", "") or ""),
                        material_group=str(normalized.get("material_group", "") or ""),
                        finish_group=str(normalized.get("finish_group", "") or ""),
                        price_pln_per_m2=self._safe_float(normalized.get("price_pln_per_m2", 0.0)),
                        price_note=str(normalized.get("price_note", "") or ""),
                    )
                )
            except Exception:
                continue
        return sorted(out, key=lambda x: x.key)

    def list_edgebands(self) -> List[EdgeBandDef]:
        data = self._read()
        out: List[EdgeBandDef] = []
        for item in (data.get("edgebands") or []):
            try:
                out.append(
                    EdgeBandDef(
                        key=str(item["key"]),
                        name_pl=str(item.get("name_pl", item["key"])),
                        thickness_mm=self._safe_float(item.get("thickness_mm", 0.0)),
                        manufacturer=str(item.get("manufacturer", "") or ""),
                        edgeband_type=str(item.get("edgeband_type", "") or ""),
                        material_group=str(item.get("material_group", "") or ""),
                        price_pln_per_m=self._safe_float(item.get("price_pln_per_m", 0.0)),
                        price_note=str(item.get("price_note", "") or ""),
                    )
                )
            except Exception:
                continue
        return sorted(out, key=lambda x: x.key)

    def list_hardware(
        self,
        category: str = "",
        manufacturer: str = "",
    ) -> List[HardwareDef]:
        data = self._read()
        wanted_category = str(category or "").strip().lower()
        wanted_manufacturer = str(manufacturer or "").strip().lower()

        out: List[HardwareDef] = []
        for item in (data.get("hardware") or []):
            try:
                hw = HardwareDef(
                    key=str(item["key"]),
                    name_pl=str(item.get("name_pl", item["key"])),
                    manufacturer=str(item.get("manufacturer", "") or ""),
                    category=str(item.get("category", "") or ""),
                    item_type=str(item.get("item_type", "") or ""),
                    unit=str(item.get("unit", "szt") or "szt"),
                    price_pln=self._safe_float(item.get("price_pln", 0.0)),
                    price_note=str(item.get("price_note", "") or ""),
                )
            except Exception:
                continue

            if wanted_category and hw.category.strip().lower() != wanted_category:
                continue
            if wanted_manufacturer and hw.manufacturer.strip().lower() != wanted_manufacturer:
                continue
            out.append(hw)

        return sorted(out, key=lambda x: x.key)

    def list_hardware_manufacturers(self, category: str = "") -> List[str]:
        seen: Dict[str, str] = {}
        for item in self.list_hardware(category=category):
            raw = str(item.manufacturer or "").strip()
            if not raw:
                continue
            normalized = raw.lower()
            if normalized not in seen:
                seen[normalized] = raw
        return [seen[key] for key in sorted(seen.keys())]

    def list_material_profiles(self) -> List[MaterialProfileDef]:
        data = self._read()
        out: List[MaterialProfileDef] = []
        for item in (data.get("material_profiles") or []):
            if not isinstance(item, dict):
                continue
            try:
                out.append(MaterialProfileDef.from_dict(item))
            except Exception:
                continue
        return sorted(out, key=lambda x: x.key)

    def get_material(self, key: str) -> Optional[MaterialDef]:
        for item in self.list_materials():
            if item.key == key:
                return item
        return None

    def get_edgeband(self, key: str) -> Optional[EdgeBandDef]:
        for item in self.list_edgebands():
            if item.key == key:
                return item
        return None

    def get_hardware(self, key: str) -> Optional[HardwareDef]:
        for item in self.list_hardware():
            if item.key == key:
                return item
        return None

    def get_material_profile(
        self,
        key: str,
        fallback_key: str = "STD_WHITE",
    ) -> MaterialProfileDef:
        normalized_key = str(key or "").strip()
        normalized_fallback = str(fallback_key or "STD_WHITE").strip() or "STD_WHITE"

        profile_map = {profile.key: profile for profile in self.list_material_profiles()}

        if normalized_key in profile_map:
            return MaterialProfileDef.from_dict(profile_map[normalized_key].to_dict())

        if normalized_fallback in profile_map:
            return MaterialProfileDef.from_dict(profile_map[normalized_fallback].to_dict())

        return get_default_material_profile(normalized_key, fallback_key=normalized_fallback)

    def find_hardware(self, category: str, manufacturer: str = "") -> Optional[HardwareDef]:
        wanted_category = str(category or "").strip().lower()
        wanted_manufacturer = str(manufacturer or "").strip().lower()

        if not wanted_category:
            return None

        if wanted_manufacturer:
            exact = self.list_hardware(category=wanted_category, manufacturer=wanted_manufacturer)
            if exact:
                return exact[0]

        generic = self.list_hardware(category=wanted_category, manufacturer="generic")
        if generic:
            return generic[0]

        items = self.list_hardware(category=wanted_category)
        return items[0] if items else None

    def material_thickness(self, key: str, fallback_mm: float) -> float:
        item = self.get_material(key)
        if not item:
            return float(fallback_mm)
        return self._compute_material_total_thickness(
            thickness_mm=item.thickness_mm,
            core=item.core,
            skins_left=item.skins_left,
            skins_right=item.skins_right,
        )

    def material_price_per_m2(self, key: str, fallback_pln: float = 0.0) -> float:
        item = self.get_material(key)
        return float(item.price_pln_per_m2) if item else float(fallback_pln)

    def edgeband_price_per_m(self, key: str, fallback_pln: float = 0.0) -> float:
        item = self.get_edgeband(key)
        return float(item.price_pln_per_m) if item else float(fallback_pln)

    def hardware_price(self, key: str, fallback_pln: float = 0.0) -> float:
        item = self.get_hardware(key)
        return float(item.price_pln) if item else float(fallback_pln)

    def export_catalog(self) -> Dict[str, List[Dict]]:
        self._ensure_catalog_schema()
        data = self._read()
        return {
            "materials": [dict(item) for item in (data.get("materials") or []) if isinstance(item, dict)],
            "edgebands": [dict(item) for item in (data.get("edgebands") or []) if isinstance(item, dict)],
            "hardware": [dict(item) for item in (data.get("hardware") or []) if isinstance(item, dict)],
            "material_profiles": [dict(item) for item in (data.get("material_profiles") or []) if isinstance(item, dict)],
        }

    def replace_catalog(
        self,
        *,
        materials: List[Dict] | None = None,
        edgebands: List[Dict] | None = None,
        hardware: List[Dict] | None = None,
        material_profiles: List[Dict] | None = None,
    ) -> None:
        current = self.export_catalog()
        payload = {
            "materials": self._normalize_material_rows(materials if materials is not None else current["materials"]),
            "edgebands": self._normalize_edgeband_rows(edgebands if edgebands is not None else current["edgebands"]),
            "hardware": self._normalize_hardware_rows(hardware if hardware is not None else current["hardware"]),
            "material_profiles": self._normalize_material_profile_rows(
                material_profiles if material_profiles is not None else current["material_profiles"]
            ),
        }
        self._write(payload)
        self._ensure_catalog_schema()

    def _ensure_catalog_schema(self) -> None:
        data = self._read()
        defaults = self._default_catalog()

        if not isinstance(data, dict):
            self._write(defaults)
            return

        changed = False
        normalized: Dict[str, List[Dict]] = {}

        for section in ("materials", "edgebands", "hardware", "material_profiles"):
            existing_raw = data.get(section) or []
            if not isinstance(existing_raw, list):
                normalized[section] = list(defaults[section])
                changed = True
                continue

            existing_map: Dict[str, Dict] = {}
            for item in existing_raw:
                if not isinstance(item, dict):
                    changed = True
                    continue
                key = str(item.get("key", "") or "").strip()
                if not key:
                    changed = True
                    continue
                existing_map[key] = dict(item)

            merged_items: List[Dict] = []
            for default_item in defaults[section]:
                key = str(default_item.get("key", "") or "")
                existing_item = existing_map.pop(key, None)
                if existing_item is None:
                    merged = dict(default_item)
                    changed = True
                else:
                    merged = self._merge_default_item(section, default_item, existing_item)
                    if merged != existing_item:
                        changed = True
                merged_items.append(merged)

            for existing_item in existing_map.values():
                merged = self._normalize_section_row(section, existing_item)
                if merged != existing_item:
                    changed = True
                merged_items.append(merged)

            normalized[section] = merged_items

        if changed:
            self._write(
                {
                    "materials": normalized.get("materials", defaults["materials"]),
                    "edgebands": normalized.get("edgebands", defaults["edgebands"]),
                    "hardware": normalized.get("hardware", defaults["hardware"]),
                    "material_profiles": normalized.get("material_profiles", defaults["material_profiles"]),
                }
            )

    def _write(self, data: Dict) -> None:
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _safe_float(value: object) -> float:
        try:
            return float(value or 0.0)
        except Exception:
            return 0.0

    def _read(self) -> Dict:
        try:
            txt = self._path.read_text(encoding="utf-8")
            data = json.loads(txt) if txt.strip() else {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _normalize_material_rows(self, rows: List[Dict]) -> List[Dict]:
        normalized: List[Dict] = []
        for row in rows:
            item = self._normalize_section_row("materials", row)
            if item:
                normalized.append(item)
        return normalized

    def _normalize_edgeband_rows(self, rows: List[Dict]) -> List[Dict]:
        normalized: List[Dict] = []
        for row in rows:
            item = self._normalize_section_row("edgebands", row)
            if item:
                normalized.append(item)
        return normalized

    def _normalize_hardware_rows(self, rows: List[Dict]) -> List[Dict]:
        normalized: List[Dict] = []
        for row in rows:
            item = self._normalize_section_row("hardware", row)
            if item:
                normalized.append(item)
        return normalized

    def _normalize_material_profile_rows(self, rows: List[Dict]) -> List[Dict]:
        normalized: List[Dict] = []
        for row in rows:
            item = self._normalize_section_row("material_profiles", row)
            if item:
                normalized.append(item)
        return normalized

    def _normalize_section_row(self, section: str, row: Dict) -> Dict:
        source = dict(row or {})
        key = str(source.get("key", "") or "").strip()
        if not key:
            return {}

        if section == "materials":
            core = self._normalize_material_layer(source.get("core"))
            skins_left = self._normalize_material_layers(source.get("skins_left"))
            skins_right = self._normalize_material_layers(source.get("skins_right"))
            if core is None and not skins_left and not skins_right:
                core, skins_left, skins_right = self._legacy_composite_to_layers(source)
            legacy_thickness = self._safe_float(source.get("thickness_mm", 0.0))
            computed_thickness = self._compute_material_total_thickness(
                thickness_mm=legacy_thickness,
                core=core,
                skins_left=skins_left,
                skins_right=skins_right,
            )
            return {
                "key": key,
                "name_pl": str(source.get("name_pl", key) or key),
                "thickness_mm": computed_thickness,
                "core": core,
                "skins_left": skins_left,
                "skins_right": skins_right,
                "manufacturer": str(source.get("manufacturer", "") or ""),
                "material_type": str(source.get("material_type", "") or ""),
                "material_group": str(source.get("material_group", "") or ""),
                "finish_group": str(source.get("finish_group", "") or ""),
                "price_pln_per_m2": self._safe_float(source.get("price_pln_per_m2", 0.0)),
                "price_note": str(source.get("price_note", "") or ""),
            }

        if section == "edgebands":
            return {
                "key": key,
                "name_pl": str(source.get("name_pl", key) or key),
                "thickness_mm": self._safe_float(source.get("thickness_mm", 0.0)),
                "manufacturer": str(source.get("manufacturer", "") or ""),
                "edgeband_type": str(source.get("edgeband_type", "") or ""),
                "material_group": str(source.get("material_group", "") or ""),
                "price_pln_per_m": self._safe_float(source.get("price_pln_per_m", 0.0)),
                "price_note": str(source.get("price_note", "") or ""),
            }

        if section == "hardware":
            return {
                "key": key,
                "name_pl": str(source.get("name_pl", key) or key),
                "manufacturer": str(source.get("manufacturer", "") or ""),
                "category": str(source.get("category", "") or ""),
                "item_type": str(source.get("item_type", "") or ""),
                "unit": str(source.get("unit", "szt") or "szt"),
                "price_pln": self._safe_float(source.get("price_pln", 0.0)),
                "price_note": str(source.get("price_note", "") or ""),
            }

        if section == "material_profiles":
            material_map_raw = source.get("material_map", {})
            edgeband_map_raw = source.get("edgeband_map", {})
            hardware_map_raw = source.get("hardware_vendor_map", {})

            if not isinstance(material_map_raw, dict):
                material_map_raw = {
                    "carcass": source.get("material_carcass", ""),
                    "front": source.get("material_front", ""),
                    "back": source.get("material_back", ""),
                }

            if not isinstance(edgeband_map_raw, dict):
                edgeband_map_raw = {
                    "carcass": source.get("edgeband_carcass", ""),
                    "front": source.get("edgeband_front", ""),
                    "back": source.get("edgeband_back", ""),
                }

            if not isinstance(hardware_map_raw, dict):
                hardware_map_raw = {
                    "hinge": source.get("hinge_vendor", ""),
                    "drawer_system": source.get("drawer_vendor", ""),
                }

            return {
                "key": key,
                "name_pl": str(source.get("name_pl", key) or key),
                "material_map": {
                    str(k): str(v)
                    for k, v in dict(material_map_raw or {}).items()
                    if str(v or "").strip()
                },
                "edgeband_map": {
                    str(k): str(v)
                    for k, v in dict(edgeband_map_raw or {}).items()
                    if str(v or "").strip()
                },
                "hardware_vendor_map": {
                    str(k): str(v)
                    for k, v in dict(hardware_map_raw or {}).items()
                    if str(v or "").strip()
                },
                "description": str(source.get("description", "") or ""),
            }

        return {}

    def _legacy_composite_to_layers(self, source: Dict) -> tuple[Optional[Dict], List[Dict], List[Dict]]:
        enabled = str(source.get("composite_enabled", "") or "").strip().lower() in {"1", "true", "yes", "y", "tak"}
        core_thickness = self._safe_float(source.get("core_thickness_mm", 0.0))
        left_thickness = self._safe_float(source.get("left_facing_thickness_mm", 0.0))
        right_thickness = self._safe_float(source.get("right_facing_thickness_mm", 0.0))
        if not enabled and core_thickness <= 0.0 and left_thickness <= 0.0 and right_thickness <= 0.0:
            return None, [], []

        core = None
        if core_thickness > 0.0:
            core = {
                "code": str(source.get("core_material_key", "") or "").strip(),
                "name_pl": str(source.get("core_material_name_pl", "") or "").strip(),
                "thickness_mm": core_thickness,
            }
            if not core["name_pl"]:
                core["name_pl"] = core["code"]

        skins_left: List[Dict] = []
        if left_thickness > 0.0:
            left = {
                "code": str(source.get("left_facing_key", "") or "").strip(),
                "name_pl": str(source.get("left_facing_name_pl", "") or "").strip(),
                "thickness_mm": left_thickness,
            }
            if not left["name_pl"]:
                left["name_pl"] = left["code"]
            skins_left.append(left)

        skins_right: List[Dict] = []
        if right_thickness > 0.0:
            right = {
                "code": str(source.get("right_facing_key", "") or "").strip(),
                "name_pl": str(source.get("right_facing_name_pl", "") or "").strip(),
                "thickness_mm": right_thickness,
            }
            if not right["name_pl"]:
                right["name_pl"] = right["code"]
            skins_right.append(right)

        return core, skins_left, skins_right

    def _material_total_thickness_mm(self, source: Dict) -> float:
        return self._compute_material_total_thickness(
            thickness_mm=self._safe_float(source.get("thickness_mm", 0.0)),
            core=source.get("core"),
            skins_left=source.get("skins_left"),
            skins_right=source.get("skins_right"),
        )

    def _normalize_material_layer(self, raw_layer: object) -> Optional[Dict]:
        if not isinstance(raw_layer, dict):
            return None
        code = str(raw_layer.get("code", "") or "").strip()
        name_pl = str(raw_layer.get("name_pl", "") or "").strip()
        thickness_mm = self._safe_float(raw_layer.get("thickness_mm", 0.0))
        if not code and not name_pl and thickness_mm <= 0.0:
            return None
        return {
            "code": code,
            "name_pl": name_pl or code,
            "thickness_mm": thickness_mm,
        }

    def _normalize_material_layers(self, raw_layers: object) -> List[Dict]:
        out: List[Dict] = []
        if not isinstance(raw_layers, list):
            return out
        for raw_layer in raw_layers:
            normalized = self._normalize_material_layer(raw_layer)
            if normalized is not None:
                out.append(normalized)
        return out

    def _compute_material_total_thickness(
        self,
        *,
        thickness_mm: float,
        core: object,
        skins_left: object,
        skins_right: object,
    ) -> float:
        normalized_core = self._normalize_material_layer(core)
        normalized_left = self._normalize_material_layers(skins_left)
        normalized_right = self._normalize_material_layers(skins_right)

        if normalized_core is None and not normalized_left and not normalized_right:
            return self._safe_float(thickness_mm)

        total = self._safe_float((normalized_core or {}).get("thickness_mm", 0.0))
        total += sum(self._safe_float(layer.get("thickness_mm", 0.0)) for layer in normalized_left)
        total += sum(self._safe_float(layer.get("thickness_mm", 0.0)) for layer in normalized_right)
        return float(total)

    def _merge_default_item(self, section: str, default_item: Dict, existing_item: Dict) -> Dict:
        if section != "material_profiles":
            merged = dict(default_item)
            merged.update(existing_item)
            return self._normalize_section_row(section, merged)

        merged = dict(default_item)
        merged.update(existing_item)

        default_material_map = dict(default_item.get("material_map", {}) or {})
        default_edgeband_map = dict(default_item.get("edgeband_map", {}) or {})
        default_hardware_map = dict(default_item.get("hardware_vendor_map", {}) or {})

        existing_material_map = dict(existing_item.get("material_map", {}) or {})
        existing_edgeband_map = dict(existing_item.get("edgeband_map", {}) or {})
        existing_hardware_map = dict(existing_item.get("hardware_vendor_map", {}) or {})

        merged["material_map"] = dict(default_material_map)
        merged["material_map"].update(existing_material_map)
        merged["edgeband_map"] = dict(default_edgeband_map)
        merged["edgeband_map"].update(existing_edgeband_map)
        merged["hardware_vendor_map"] = dict(default_hardware_map)
        merged["hardware_vendor_map"].update(existing_hardware_map)

        return self._normalize_section_row(section, merged)

    @staticmethod
    def _collapse_profile_source_to_groups(source_map: Dict[str, str] | None) -> Dict[str, str]:
        source = dict(source_map or {})
        out: Dict[str, str] = {}
        groups = {
            "carcass": ("carcass", "side", "top", "bottom", "shelf", "divider"),
            "front": ("front",),
            "back": ("back",),
        }
        for group_key, logical_keys in groups.items():
            selected = ""
            for logical_key in logical_keys:
                raw = str(source.get(logical_key, "") or "").strip()
                if raw:
                    selected = raw
                    break
            if selected:
                out[group_key] = selected
        return out

    @classmethod
    def _default_material_profile_rows(cls) -> List[Dict]:
        rows: List[Dict] = []
        for profile in build_default_material_profiles():
            rows.append(
                {
                    "key": profile.key,
                    "name_pl": profile.name_pl,
                    "material_map": cls._collapse_profile_source_to_groups(profile.material_map),
                    "edgeband_map": cls._collapse_profile_source_to_groups(profile.edgeband_map),
                    "hardware_vendor_map": {
                        "hinge": str((profile.hardware_vendor_map or {}).get("hinge", "") or "").strip(),
                        "drawer_system": str((profile.hardware_vendor_map or {}).get("drawer_system", "") or "").strip(),
                    },
                    "description": str(profile.description or ""),
                }
            )
        return rows

    @classmethod
    def _default_catalog(cls) -> Dict:
        return {
            "materials": [
                {
                    "key": "PB18",
                    "name_pl": "Plyta wiorowa",
                    "thickness_mm": 18.0,
                    "manufacturer": "Egger",
                    "material_type": "laminowana",
                    "material_group": "carcass_board",
                    "finish_group": "melamine",
                    "price_pln_per_m2": 72.0,
                },
                {
                    "key": "PB16",
                    "name_pl": "Plyta wiorowa",
                    "thickness_mm": 16.0,
                    "manufacturer": "Egger",
                    "material_type": "laminowana",
                    "material_group": "carcass_board",
                    "finish_group": "melamine",
                    "price_pln_per_m2": 66.0,
                },
                {
                    "key": "MDF18",
                    "name_pl": "MDF",
                    "thickness_mm": 18.0,
                    "manufacturer": "Swiss Krono",
                    "material_type": "surowy",
                    "material_group": "front_board",
                    "finish_group": "raw",
                    "price_pln_per_m2": 98.0,
                },
                {
                    "key": "MDF19",
                    "name_pl": "MDF",
                    "thickness_mm": 19.0,
                    "manufacturer": "Swiss Krono",
                    "material_type": "surowy",
                    "material_group": "front_board",
                    "finish_group": "raw",
                    "price_pln_per_m2": 108.0,
                },
                {
                    "key": "MDF19_LAK",
                    "name_pl": "MDF lakierowany",
                    "thickness_mm": 19.0,
                    "manufacturer": "Swiss Krono",
                    "material_type": "lakierowany",
                    "material_group": "front_board",
                    "finish_group": "lacquer",
                    "price_pln_per_m2": 189.0,
                    "price_note": "Przykladowa cena frontu lakierowanego",
                },
                {
                    "key": "HDF3",
                    "name_pl": "HDF",
                    "thickness_mm": 3.0,
                    "manufacturer": "Pfleiderer",
                    "material_type": "plecy",
                    "material_group": "back_board",
                    "finish_group": "raw",
                    "price_pln_per_m2": 24.0,
                },
                {
                    "key": "HDF2.5",
                    "name_pl": "HDF",
                    "thickness_mm": 2.5,
                    "manufacturer": "Pfleiderer",
                    "material_type": "plecy",
                    "material_group": "back_board",
                    "finish_group": "raw",
                    "price_pln_per_m2": 21.0,
                },
            ],
            "edgebands": [
                {
                    "key": "Brak",
                    "name_pl": "Brak",
                    "thickness_mm": 0.0,
                    "manufacturer": "",
                    "edgeband_type": "none",
                    "material_group": "none",
                    "price_pln_per_m": 0.0,
                },
                {
                    "key": "ABS 0.8",
                    "name_pl": "ABS 0,8",
                    "thickness_mm": 0.8,
                    "manufacturer": "Rehau",
                    "edgeband_type": "ABS",
                    "material_group": "abs",
                    "price_pln_per_m": 4.5,
                },
                {
                    "key": "ABS 2.0",
                    "name_pl": "ABS 2,0",
                    "thickness_mm": 2.0,
                    "manufacturer": "Rehau",
                    "edgeband_type": "ABS",
                    "material_group": "abs",
                    "price_pln_per_m": 7.8,
                },
                {
                    "key": "Fornir 0.6",
                    "name_pl": "Fornir 0,6",
                    "thickness_mm": 0.6,
                    "manufacturer": "Schorn",
                    "edgeband_type": "fornir",
                    "material_group": "veneer",
                    "price_pln_per_m": 6.2,
                },
                {
                    "key": "HPL 0.8",
                    "name_pl": "HPL 0,8",
                    "thickness_mm": 0.8,
                    "manufacturer": "Egger",
                    "edgeband_type": "HPL",
                    "material_group": "hpl",
                    "price_pln_per_m": 8.9,
                },
            ],
            "hardware": [
                {
                    "key": "hinge_generic",
                    "name_pl": "Zawias puszkowy",
                    "manufacturer": "generic",
                    "category": "hinge",
                    "item_type": "standard",
                    "unit": "szt",
                    "price_pln": 4.2,
                },
                {
                    "key": "hinge_blum_cliptop",
                    "name_pl": "Zawias Blum ClipTop",
                    "manufacturer": "blum",
                    "category": "hinge",
                    "item_type": "standard",
                    "unit": "szt",
                    "price_pln": 9.8,
                },
                {
                    "key": "hinge_hettich_sensys",
                    "name_pl": "Zawias Hettich Sensys",
                    "manufacturer": "hettich",
                    "category": "hinge",
                    "item_type": "standard",
                    "unit": "szt",
                    "price_pln": 8.9,
                },
                {
                    "key": "drawer_system_generic",
                    "name_pl": "System szuflady",
                    "manufacturer": "generic",
                    "category": "drawer_system",
                    "item_type": "standard",
                    "unit": "kpl",
                    "price_pln": 45.0,
                },
                {
                    "key": "drawer_system_blum",
                    "name_pl": "System szuflady Blum",
                    "manufacturer": "blum",
                    "category": "drawer_system",
                    "item_type": "standard",
                    "unit": "kpl",
                    "price_pln": 92.0,
                },
                {
                    "key": "drawer_system_hettich",
                    "name_pl": "System szuflady Hettich",
                    "manufacturer": "hettich",
                    "category": "drawer_system",
                    "item_type": "standard",
                    "unit": "kpl",
                    "price_pln": 74.0,
                },
                {
                    "key": "drawer_tip_on_generic",
                    "name_pl": "TIP-ON do szuflady",
                    "manufacturer": "generic",
                    "category": "drawer_tip_on",
                    "item_type": "push_to_open",
                    "unit": "szt",
                    "price_pln": 12.0,
                },
                {
                    "key": "drawer_tip_on_blum",
                    "name_pl": "TIP-ON Blum",
                    "manufacturer": "blum",
                    "category": "drawer_tip_on",
                    "item_type": "push_to_open",
                    "unit": "szt",
                    "price_pln": 20.0,
                },
                {
                    "key": "drawer_tip_on_hettich",
                    "name_pl": "Push to open Hettich",
                    "manufacturer": "hettich",
                    "category": "drawer_tip_on",
                    "item_type": "push_to_open",
                    "unit": "szt",
                    "price_pln": 18.0,
                },
                {
                    "key": "shelf_support_generic",
                    "name_pl": "Polkotrzymacz",
                    "manufacturer": "generic",
                    "category": "shelf_support",
                    "item_type": "support",
                    "unit": "szt",
                    "price_pln": 0.8,
                },
                {
                    "key": "wall_hanger_generic",
                    "name_pl": "Zawieszka meblowa",
                    "manufacturer": "generic",
                    "category": "wall_hanger",
                    "item_type": "hanger",
                    "unit": "szt",
                    "price_pln": 14.0,
                },
                {
                    "key": "divider_connector_generic",
                    "name_pl": "Lacznik pionu",
                    "manufacturer": "generic",
                    "category": "divider_connector",
                    "item_type": "connector",
                    "unit": "szt",
                    "price_pln": 1.4,
                },
                {
                    "key": "cabinet_leg_generic",
                    "name_pl": "Nozka meblowa",
                    "manufacturer": "generic",
                    "category": "cabinet_leg",
                    "item_type": "support",
                    "unit": "szt",
                    "price_pln": 8.0,
                },
                {
                    "key": "plinth_clip_generic",
                    "name_pl": "Klips cokolu",
                    "manufacturer": "generic",
                    "category": "plinth_clip",
                    "item_type": "clip",
                    "unit": "szt",
                    "price_pln": 1.6,
                },
                {
                    "key": "corner_connector_generic",
                    "name_pl": "Lacznik szafki naroznej",
                    "manufacturer": "generic",
                    "category": "corner_connector",
                    "item_type": "connector",
                    "unit": "kpl",
                    "price_pln": 18.0,
                },
            ],
            "material_profiles": cls._default_material_profile_rows(),
        }
