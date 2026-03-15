from __future__ import annotations

from dataclasses import replace

from src.domain.module_models import ModuleDef, ModuleFamilyDef


def resolve_module_family(module: ModuleDef, family: ModuleFamilyDef | None) -> ModuleDef:
    """
    Zwraca nowy ModuleDef z nalozonymi domyslnymi ustawieniami rodziny.

    Zasady:
    - nie modyfikuje wejsciowego `module`
    - jesli `family is None`, zwraca kopie modulu
    - jesli module.cabinet_kind jest puste -> bierze family.default_cabinet_kind
    - jesli module.ref_point jest puste -> bierze family.default_ref_point
    - jesli module.height_mm <= 0 -> bierze family.default_height_mm
    - jesli module.depth_mm <= 0 -> bierze family.default_depth_mm
    - jesli module.material_profile_key jest puste -> bierze family.default_material_profile_key
    - jesli rodzina nie pozwala na dane dziedziczenie, resolver je wylacza
    """

    result = replace(module)

    if family is None:
        return result

    # rodzina modulu
    if family.key:
        result.module_family = family.key

    # podstawowe wartosci domyslne rodziny
    if not (result.cabinet_kind or "").strip():
        result.cabinet_kind = family.default_cabinet_kind

    if not (result.ref_point or "").strip():
        result.ref_point = family.default_ref_point

    if float(result.height_mm) <= 0:
        result.height_mm = float(family.default_height_mm)

    if float(result.depth_mm) <= 0:
        result.depth_mm = float(family.default_depth_mm)

    if not (result.material_profile_key or "").strip():
        result.material_profile_key = family.default_material_profile_key

    # ograniczenia dziedziczenia narzucone przez rodzine
    if not family.allow_inherit_height_from_wall:
        result.inherit_height_from_wall = False

    if not family.allow_inherit_depth_from_wall:
        result.inherit_depth_from_wall = False

    if not family.allow_inherit_materials_from_group:
        result.inherit_materials_from_group = False

    if not family.allow_inherit_edgeband_from_group:
        result.inherit_edgeband_from_group = False

    return result