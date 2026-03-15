from src.domain.module_models import ModuleDef
from src.domain.material_profile_service import resolve_module_with_material_profile_registry


def test_material_profile_service_fills_missing_edgebands_from_profile():
    module = ModuleDef(
        name="TEST_EDGE_SVC_1",
        material_profile_key="WARDROBE_GRAPHITE",
        edgebands={},
    )

    resolved = resolve_module_with_material_profile_registry(module)

    assert resolved.material_profile_key == "WARDROBE_GRAPHITE"
    assert resolved.edgebands["side"] == "ABS 2.0"
    assert resolved.edgebands["top"] == "ABS 2.0"
    assert resolved.edgebands["bottom"] == "ABS 2.0"
    assert resolved.edgebands["shelf"] == "ABS 2.0"
    assert resolved.edgebands["back"] == "Brak"


def test_material_profile_service_preserves_explicit_edgebands():
    module = ModuleDef(
        name="TEST_EDGE_SVC_2",
        material_profile_key="STD_WHITE",
        edgebands={
            "front": "CUSTOM_EDGE",
            "side": "CUSTOM_SIDE_EDGE",
        },
    )

    resolved = resolve_module_with_material_profile_registry(module)

    assert resolved.material_profile_key == "STD_WHITE"
    assert resolved.edgebands["front"] == "CUSTOM_EDGE"
    assert resolved.edgebands["side"] == "CUSTOM_SIDE_EDGE"
    assert resolved.edgebands["top"] == "ABS 0.8"
    assert resolved.edgebands["bottom"] == "ABS 0.8"
