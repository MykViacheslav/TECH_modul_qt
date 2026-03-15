from __future__ import annotations

from typing import Dict, List

from src.domain.module_models import ModuleFamilyDef


def _clone_family(family: ModuleFamilyDef) -> ModuleFamilyDef:
    return ModuleFamilyDef.from_dict(family.to_dict())


def build_default_module_families() -> List[ModuleFamilyDef]:
    """
    Zwraca liste domyslnych rodzin modulow.
    Kazde wywolanie zwraca swieze obiekty.
    """

    families = [
        ModuleFamilyDef(
            key="kitchen_lower",
            name_pl="Szafka dolna",
            default_cabinet_kind="lower",
            default_ref_point="LBB",
            default_height_mm=720.0,
            default_depth_mm=560.0,
            default_material_profile_key="",
            allow_inherit_height_from_wall=True,
            allow_inherit_depth_from_wall=False,
            allow_inherit_materials_from_group=True,
            allow_inherit_edgeband_from_group=True,
        ),
        ModuleFamilyDef(
            key="kitchen_upper",
            name_pl="Szafka gorna",
            default_cabinet_kind="upper",
            default_ref_point="LTB",
            default_height_mm=720.0,
            default_depth_mm=320.0,
            default_material_profile_key="",
            allow_inherit_height_from_wall=False,
            allow_inherit_depth_from_wall=False,
            allow_inherit_materials_from_group=True,
            allow_inherit_edgeband_from_group=True,
        ),
        ModuleFamilyDef(
            key="wardrobe",
            name_pl="Szafa",
            default_cabinet_kind="tall",
            default_ref_point="LBB",
            default_height_mm=2300.0,
            default_depth_mm=620.0,
            default_material_profile_key="",
            allow_inherit_height_from_wall=True,
            allow_inherit_depth_from_wall=True,
            allow_inherit_materials_from_group=True,
            allow_inherit_edgeband_from_group=True,
        ),
        ModuleFamilyDef(
            key="display",
            name_pl="Witryna",
            default_cabinet_kind="display",
            default_ref_point="LBB",
            default_height_mm=1800.0,
            default_depth_mm=450.0,
            default_material_profile_key="",
            allow_inherit_height_from_wall=False,
            allow_inherit_depth_from_wall=False,
            allow_inherit_materials_from_group=True,
            allow_inherit_edgeband_from_group=True,
        ),
    ]

    return [_clone_family(f) for f in families]


def build_default_module_family_map() -> Dict[str, ModuleFamilyDef]:
    """
    Zwraca slownik {family_key: ModuleFamilyDef}.
    Kazde wywolanie zwraca swieze obiekty.
    """

    result: Dict[str, ModuleFamilyDef] = {}
    for family in build_default_module_families():
        result[family.key] = family
    return result


def get_default_module_family(
    key: str,
    fallback_key: str = "kitchen_lower",
) -> ModuleFamilyDef:
    """
    Zwraca rodzine po kluczu.
    Jesli klucz nie istnieje, zwraca fallback.
    """

    family_map = build_default_module_family_map()

    normalized_key = (key or "").strip()
    normalized_fallback = (fallback_key or "kitchen_lower").strip() or "kitchen_lower"

    if normalized_key in family_map:
        return _clone_family(family_map[normalized_key])

    if normalized_fallback in family_map:
        return _clone_family(family_map[normalized_fallback])

    # awaryjnie: pierwszy dostepny wpis
    first_family = next(iter(family_map.values()))
    return _clone_family(first_family)