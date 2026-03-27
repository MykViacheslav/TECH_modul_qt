from __future__ import annotations

from src.domain.module_models import ModuleDef, new_module_id
from src.storage.default_module_store_json import load_default_module


CABINET_KIND_PL = {
    "lower": "Dolna (punkt od dolu)",
    "upper": "Gorna (punkt od gory)",
}

REF_POINTS_BY_KIND_PL = {
    "lower": {
        "LBB": "Lewy-TYL-DOL (0,0,0)",
        "CBB": "Srodek-TYL-DOL",
        "RBB": "Prawy-TYL-DOL",
    },
    "upper": {
        "LBT": "Lewy-TYL-GORA (0,0,0)",
        "CBT": "Srodek-TYL-GORA",
        "RBT": "Prawy-TYL-GORA",
    },
}

SHELF_MOUNT_PL = {
    "left": "Polki po LEWEJ stronie pionu",
    "right": "Polki po PRAWEJ stronie pionu",
}

MODULE_TYPE_PL = {
    "legacy": "Standard",
    "hanging": "Wiszacy",
    "legs": "Na nozkach",
    "legs_plinth": "Na nozkach z cokolem",
    "corner": "Szafka narozna",
}


def build_default_module() -> ModuleDef:
    m = load_default_module()
    if _is_startup_module_state_valid(m):
        return m

    return build_factory_default_module()


def build_factory_default_module() -> ModuleDef:
    return ModuleDef(
        module_id=new_module_id(),
        name="",
        base_group="kitchen",
        width_mm=800.0,
        depth_mm=500.0,
        height_mm=500.0,
        carcass_joint_type="type1",
        shelf_count=1,
        divider_count=0,
        shelf_mount="right",
        module_type="legacy",
        cabinet_kind="lower",
        ref_point="LBB",
        material_profile_key="STD_WHITE",
        visible_parts=set(["side_left", "side_right", "top", "bottom", "shelf", "back", "front"]),
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
        parts={},
    )


def _is_startup_module_state_valid(m: ModuleDef | None) -> bool:
    if m is None:
        return False

    try:
        width_mm = float(getattr(m, "width_mm", 0.0) or 0.0)
        depth_mm = float(getattr(m, "depth_mm", 0.0) or 0.0)
        height_mm = float(getattr(m, "height_mm", 0.0) or 0.0)
    except Exception:
        return False

    if width_mm < 100.0 or depth_mm < 100.0 or height_mm < 100.0:
        return False

    visible_parts = set(getattr(m, "visible_parts", set()) or set())
    if not visible_parts:
        return False

    return True


def normalize_rail_offsets_mm(
    height_mm: float,
    rail_thickness_mm: float,
    top_offset_mm: float,
    bottom_offset_mm: float,
) -> tuple[float, float]:
    H = max(0.0, float(height_mm))
    t = max(0.0, float(rail_thickness_mm))

    try:
        top = max(0.0, float(top_offset_mm))
    except Exception:
        top = 0.0

    try:
        bottom = max(0.0, float(bottom_offset_mm))
    except Exception:
        bottom = 0.0

    max_top = max(0.0, H - 2.0 * t)
    top = min(top, max_top)

    max_bottom = max(0.0, H - 2.0 * t - top)
    bottom = min(bottom, max_bottom)

    return top, bottom
