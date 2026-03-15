from src.domain.module_models import ModuleDef
from src.domain.material_profile_service import resolve_module_with_material_profile_registry


def test_resolve_module_with_material_profile_registry_uses_profile_key():
    module = ModuleDef(
        name="TEST_MP_1",
        material_profile_key="WARDROBE_GRAPHITE",
        materials={},
    )

    resolved = resolve_module_with_material_profile_registry(module)

    assert resolved.material_profile_key == "WARDROBE_GRAPHITE"
    assert resolved.materials["side"] == "PB16"
    assert resolved.materials["top"] == "PB16"
    assert resolved.materials["bottom"] == "PB16"
    assert resolved.materials["back"] == "HDF3"
    assert resolved.materials["front"] == "MDF19"
    assert resolved.hinge_vendor == "hettich"
    assert resolved.drawer_vendor == "hettich"


def test_resolve_module_with_material_profile_registry_uses_fallback_for_unknown_key():
    module = ModuleDef(
        name="TEST_MP_2",
        material_profile_key="UNKNOWN_PROFILE",
        materials={},
    )

    resolved = resolve_module_with_material_profile_registry(
        module,
        fallback_profile_key="DISPLAY_GLASS",
    )

    assert resolved.material_profile_key == "DISPLAY_GLASS"
    assert resolved.materials["side"] == "PB18"
    assert resolved.materials["top"] == "PB18"
    assert resolved.materials["bottom"] == "PB18"
    assert resolved.materials["front"] == "MDF19_LAK"
    assert resolved.hinge_vendor == "blum"
    assert resolved.drawer_vendor == "blum"


def test_resolve_module_with_material_profile_registry_preserves_explicit_module_materials():
    module = ModuleDef(
        name="TEST_MP_3",
        material_profile_key="STD_WHITE",
        materials={
            "front": "MDF18_CUSTOM_BLACK",
            "back": "HDF_CUSTOM_GREY",
        },
    )

    resolved = resolve_module_with_material_profile_registry(module)

    assert resolved.material_profile_key == "STD_WHITE"
    assert resolved.materials["side"] == "PB18"
    assert resolved.materials["top"] == "PB18"
    assert resolved.materials["bottom"] == "PB18"
    assert resolved.materials["front"] == "MDF18_CUSTOM_BLACK"
    assert resolved.materials["back"] == "HDF_CUSTOM_GREY"


def test_resolve_module_with_material_profile_registry_does_not_mutate_input():
    module = ModuleDef(
        name="TEST_MP_4",
        material_profile_key="",
        materials={
            "front": "MDF18_MANUAL",
        },
    )

    resolved = resolve_module_with_material_profile_registry(module)

    assert module.material_profile_key == ""
    assert module.materials == {"front": "MDF18_MANUAL"}

    assert resolved.material_profile_key == "STD_WHITE"
    assert resolved.materials["front"] == "MDF18_MANUAL"
    assert resolved.materials["side"] == "PB18"
    assert resolved.materials["back"] == "HDF2.5"
    assert resolved.hinge_vendor == "generic"
    assert resolved.drawer_vendor == "generic"
