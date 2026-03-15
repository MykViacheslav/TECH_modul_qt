from src.domain.module_models import ModuleDef
from src.domain.module_resolution_service import resolve_module_domain_defaults


def test_resolve_module_domain_defaults_applies_family_and_material_profile():
    module = ModuleDef(
        name="TEST_RES_1",
        module_family="wardrobe",
        material_profile_key="WARDROBE_GRAPHITE",
        cabinet_kind="",
        ref_point="",
        height_mm=0.0,
        depth_mm=0.0,
        materials={},
    )

    resolved = resolve_module_domain_defaults(module)

    assert resolved.module_family == "wardrobe"
    assert resolved.material_profile_key == "WARDROBE_GRAPHITE"

    assert resolved.cabinet_kind == "tall"
    assert resolved.ref_point == "LBB"
    assert resolved.height_mm == 2300.0
    assert resolved.depth_mm == 620.0

    assert resolved.materials["side"] == "PB16"
    assert resolved.materials["top"] == "PB16"
    assert resolved.materials["bottom"] == "PB16"
    assert resolved.materials["back"] == "HDF3"
    assert resolved.materials["front"] == "MDF19"
    assert resolved.hinge_vendor == "hettich"
    assert resolved.drawer_vendor == "hettich"


def test_resolve_module_domain_defaults_uses_fallbacks_for_unknown_keys():
    module = ModuleDef(
        name="TEST_RES_2",
        module_family="UNKNOWN_FAMILY",
        material_profile_key="UNKNOWN_PROFILE",
        cabinet_kind="",
        ref_point="",
        height_mm=0.0,
        depth_mm=0.0,
        materials={},
    )

    resolved = resolve_module_domain_defaults(
        module,
        fallback_family_key="display",
        fallback_profile_key="DISPLAY_GLASS",
    )

    assert resolved.module_family == "display"
    assert resolved.material_profile_key == "DISPLAY_GLASS"

    assert resolved.cabinet_kind == "display"
    assert resolved.ref_point == "LBB"
    assert resolved.height_mm == 1800.0
    assert resolved.depth_mm == 450.0

    assert resolved.materials["side"] == "PB18"
    assert resolved.materials["top"] == "PB18"
    assert resolved.materials["bottom"] == "PB18"
    assert resolved.materials["front"] == "MDF19_LAK"
    assert resolved.hinge_vendor == "blum"
    assert resolved.drawer_vendor == "blum"


def test_resolve_module_domain_defaults_preserves_explicit_values():
    module = ModuleDef(
        name="TEST_RES_3",
        module_family="kitchen_upper",
        material_profile_key="STD_WHITE",
        cabinet_kind="manual_kind",
        ref_point="MANUAL_REF",
        height_mm=1111.0,
        depth_mm=444.0,
        materials={
            "front": "MDF18_CUSTOM_BLACK",
            "back": "HDF_CUSTOM_GREY",
        },
    )

    resolved = resolve_module_domain_defaults(module)

    assert resolved.module_family == "kitchen_upper"
    assert resolved.material_profile_key == "STD_WHITE"

    assert resolved.cabinet_kind == "manual_kind"
    assert resolved.ref_point == "MANUAL_REF"
    assert resolved.height_mm == 1111.0
    assert resolved.depth_mm == 444.0

    assert resolved.materials["side"] == "PB18"
    assert resolved.materials["top"] == "PB18"
    assert resolved.materials["bottom"] == "PB18"
    assert resolved.materials["front"] == "MDF18_CUSTOM_BLACK"
    assert resolved.materials["back"] == "HDF_CUSTOM_GREY"


def test_resolve_module_domain_defaults_does_not_mutate_input():
    module = ModuleDef(
        name="TEST_RES_4",
        module_family="wardrobe",
        material_profile_key="WARDROBE_GRAPHITE",
        cabinet_kind="",
        ref_point="",
        height_mm=0.0,
        depth_mm=0.0,
        materials={"front": "MDF18_MANUAL"},
    )

    resolved = resolve_module_domain_defaults(module)

    assert module.module_family == "wardrobe"
    assert module.material_profile_key == "WARDROBE_GRAPHITE"
    assert module.cabinet_kind == ""
    assert module.ref_point == ""
    assert module.height_mm == 0.0
    assert module.depth_mm == 0.0
    assert module.materials == {"front": "MDF18_MANUAL"}

    assert resolved.module_family == "wardrobe"
    assert resolved.material_profile_key == "WARDROBE_GRAPHITE"
    assert resolved.cabinet_kind == "tall"
    assert resolved.ref_point == "LBB"
    assert resolved.height_mm == 2300.0
    assert resolved.depth_mm == 620.0
    assert resolved.materials["front"] == "MDF18_MANUAL"
    assert resolved.materials["side"] == "PB16"
