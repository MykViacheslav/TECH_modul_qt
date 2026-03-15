from __future__ import annotations

from dataclasses import dataclass, field

from src.app.app_settings import load_drawing_settings
from src.core.rules.hardware import estimate_module_hardware_requirements
from src.domain.module_models import ModuleDef
from src.storage.catalog_store_json import CatalogStoreJson


@dataclass(frozen=True)
class MaterialCostLine:
    key: str
    label: str
    count: int
    area_m2: float
    cost_pln: float = 0.0
    priced: bool = False


@dataclass(frozen=True)
class EdgebandCostLine:
    key: str
    label: str
    length_m: float
    cost_pln: float = 0.0
    priced: bool = False


@dataclass(frozen=True)
class HardwareCostLine:
    key: str
    label: str
    manufacturer: str
    quantity: float
    unit: str
    cost_pln: float = 0.0
    note: str = ""
    priced: bool = False


@dataclass(frozen=True)
class ModuleCostBreakdown:
    material_lines: list[MaterialCostLine] = field(default_factory=list)
    edgeband_lines: list[EdgebandCostLine] = field(default_factory=list)
    hardware_lines: list[HardwareCostLine] = field(default_factory=list)
    material_total_pln: float = 0.0
    edgeband_total_pln: float = 0.0
    hardware_total_pln: float = 0.0

    @property
    def grand_total_pln(self) -> float:
        return float(self.material_total_pln + self.edgeband_total_pln + self.hardware_total_pln)


def _material_label(catalog: CatalogStoreJson, key: str) -> str:
    item = catalog.get_material(key)
    if item is None:
        return key or "-"
    if not item.name_pl or item.name_pl == item.key:
        return item.key
    return f"{item.key} - {item.name_pl}"


def calculate_module_cost_breakdown(
    module: ModuleDef,
    catalog: CatalogStoreJson,
    auto_double_front_width_mm: float | None = None,
) -> ModuleCostBreakdown:
    if auto_double_front_width_mm is None:
        auto_double_front_width_mm = float(load_drawing_settings().auto_double_front_width_mm or 600.0)

    material_acc: dict[str, dict[str, float | bool]] = {}
    for part in (module.parts or {}).values():
        material_key = str(part.material_key or "-")
        dims = part.dims_mm or {}
        width_mm = float(dims.get("w", 0.0) or 0.0)
        height_mm = float(dims.get("h", 0.0) or 0.0)
        area_m2 = (width_mm * height_mm) / 1_000_000.0
        price = catalog.material_price_per_m2(material_key, 0.0)
        priced = price > 0.0

        if material_key not in material_acc:
            material_acc[material_key] = {"count": 0.0, "area": 0.0, "cost": 0.0, "priced": False}

        material_acc[material_key]["count"] += 1.0
        material_acc[material_key]["area"] += area_m2
        if priced:
            material_acc[material_key]["cost"] += area_m2 * price
            material_acc[material_key]["priced"] = True

    material_lines: list[MaterialCostLine] = []
    material_total = 0.0
    for material_key in sorted(material_acc.keys()):
        entry = material_acc[material_key]
        cost = float(entry["cost"])
        material_total += cost
        material_lines.append(
            MaterialCostLine(
                key=material_key,
                label=_material_label(catalog, material_key),
                count=int(entry["count"]),
                area_m2=float(entry["area"]),
                cost_pln=cost,
                priced=bool(entry["priced"]),
            )
        )

    edgeband_acc_m: dict[str, float] = {}
    for part in (module.parts or {}).values():
        dims = part.dims_mm or {}
        width_mm = float(dims.get("w", 0.0) or 0.0)
        height_mm = float(dims.get("h", 0.0) or 0.0)
        for side, key in dict(part.edge_banding or {}).items():
            if not key or key == "Brak":
                continue
            if side in ("left", "right"):
                edge_mm = height_mm
            elif side in ("top", "bottom"):
                edge_mm = width_mm
            else:
                edge_mm = 0.0
            edgeband_acc_m[key] = edgeband_acc_m.get(key, 0.0) + (edge_mm / 1000.0)

    edgeband_lines: list[EdgebandCostLine] = []
    edgeband_total = 0.0
    for key in sorted(edgeband_acc_m.keys()):
        length_m = float(edgeband_acc_m[key])
        price = catalog.edgeband_price_per_m(key, 0.0)
        priced = price > 0.0
        cost = length_m * price if priced else 0.0
        edgeband_total += cost

        item = catalog.get_edgeband(key)
        label = str(getattr(item, "name_pl", key) or key)
        edgeband_lines.append(
            EdgebandCostLine(
                key=key,
                label=label,
                length_m=length_m,
                cost_pln=cost,
                priced=priced,
            )
        )

    hardware_lines: list[HardwareCostLine] = []
    hardware_total = 0.0
    for requirement in estimate_module_hardware_requirements(
        module,
        auto_double_front_width_mm=float(auto_double_front_width_mm or 600.0),
    ):
        item = catalog.find_hardware(
            category=requirement.category,
            manufacturer=requirement.manufacturer,
        )

        quantity = float(requirement.quantity or 0.0)
        if item is None:
            hardware_lines.append(
                HardwareCostLine(
                    key=requirement.category,
                    label=requirement.category,
                    manufacturer=requirement.manufacturer,
                    quantity=quantity,
                    unit=requirement.unit,
                    cost_pln=0.0,
                    note=requirement.note,
                    priced=False,
                )
            )
            continue

        manufacturer = str(getattr(item, "manufacturer", "") or "").strip()
        label = str(getattr(item, "name_pl", getattr(item, "key", requirement.category)) or requirement.category)
        price = float(getattr(item, "price_pln", 0.0) or 0.0)
        cost = quantity * price
        hardware_total += cost

        hardware_lines.append(
            HardwareCostLine(
                key=str(getattr(item, "key", requirement.category) or requirement.category),
                label=label,
                manufacturer=manufacturer,
                quantity=quantity,
                unit=str(getattr(item, "unit", requirement.unit) or requirement.unit),
                cost_pln=cost,
                note=requirement.note,
                priced=price > 0.0,
            )
        )

    return ModuleCostBreakdown(
        material_lines=material_lines,
        edgeband_lines=edgeband_lines,
        hardware_lines=hardware_lines,
        material_total_pln=material_total,
        edgeband_total_pln=edgeband_total,
        hardware_total_pln=hardware_total,
    )
