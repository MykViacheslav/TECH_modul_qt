from src.domain.module_models import ModuleDef
from src.domain.module_resolution_service import build_resolved_module_domain_state


def test_build_resolved_module_domain_state_applies_family_and_material_profile():
    module = ModuleDef(
        name="TEST_STATE_1",
        module_family="wardrobe",
        material_profile_key="WARDROBE_GRAPHITE",
        cabinet_kind="",
        ref_point="",
        width_mm=900.0,
        height_mm=0.0,
        depth_mm=0.0,
        materials={},
    )

    state = build_resolved_module_domain_state(module)

    assert state.module_name == "TEST_STATE_1"
    assert state.module_family_key == "wardrobe"
    assert state.material_profile_key == "WARDROBE_GRAPHITE"
    assert state.cabinet_kind == "tall"
    assert state.ref_point == "LBB"
    assert state.width_mm == 900.0
    assert state.height_mm == 2300.0
    assert state.depth_mm == 620.0
    assert state.materials["side"] == "PB16"
    assert state.materials["front"] == "MDF19"


def test_build_resolved_module_domain_state_uses_fallbacks():
    module = ModuleDef(
        name="TEST_STATE_2",
        module_family="UNKNOWN_FAMILY",
        material_profile_key="UNKNOWN_PROFILE",
        cabinet_kind="",
        ref_point="",
        width_mm=800.0,
        height_mm=0.0,
        depth_mm=0.0,
        materials={},
    )

    state = build_resolved_module_domain_state(
        module,
        fallback_family_key="display",
        fallback_profile_key="DISPLAY_GLASS",
    )

    assert state.module_family_key == "display"
    assert state.material_profile_key == "DISPLAY_GLASS"
    assert state.cabinet_kind == "display"
    assert state.ref_point == "LBB"
    assert state.height_mm == 1800.0
    assert state.depth_mm == 450.0
    assert state.materials["front"] == "MDF19_LAK"


def test_build_resolved_module_domain_state_preserves_explicit_materials():
    module = ModuleDef(
        name="TEST_STATE_3",
        module_family="kitchen_upper",
        material_profile_key="STD_WHITE",
        cabinet_kind="manual_kind",
        ref_point="MANUAL_REF",
        width_mm=600.0,
        height_mm=1111.0,
        depth_mm=333.0,
        materials={
            "front": "MDF18_CUSTOM_BLACK",
        },
    )

    state = build_resolved_module_domain_state(module)

    assert state.module_family_key == "kitchen_upper"
    assert state.material_profile_key == "STD_WHITE"
    assert state.cabinet_kind == "manual_kind"
    assert state.ref_point == "MANUAL_REF"
    assert state.height_mm == 1111.0
    assert state.depth_mm == 333.0
    assert state.materials["front"] == "MDF18_CUSTOM_BLACK"
    assert state.materials["side"] == "PB18"
