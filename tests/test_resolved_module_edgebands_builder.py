from src.domain.module_models import ModuleDef
from src.domain.module_resolution_service import build_resolved_module_domain_state


def test_build_resolved_module_domain_state_keeps_resolved_edgebands():
    module = ModuleDef(
        name="TEST_STATE_EDGE_1",
        module_family="wardrobe",
        material_profile_key="WARDROBE_GRAPHITE",
        materials={},
        edgebands={},
        height_mm=0.0,
        depth_mm=0.0,
        cabinet_kind="",
        ref_point="",
    )

    state = build_resolved_module_domain_state(module)

    assert state.module_family_key == "wardrobe"
    assert state.material_profile_key == "WARDROBE_GRAPHITE"
    assert state.edgebands["side"] == "ABS 2.0"
    assert state.edgebands["top"] == "ABS 2.0"
    assert state.edgebands["bottom"] == "ABS 2.0"


def test_build_resolved_module_domain_state_preserves_manual_edgebands():
    module = ModuleDef(
        name="TEST_STATE_EDGE_2",
        module_family="kitchen_upper",
        material_profile_key="STD_WHITE",
        edgebands={
            "front": "MANUAL_FRONT_EDGE",
        },
    )

    state = build_resolved_module_domain_state(module)

    assert state.material_profile_key == "STD_WHITE"
    assert state.edgebands["front"] == "MANUAL_FRONT_EDGE"
    assert state.edgebands["side"] == "ABS 0.8"
