from src.domain.module_models import ModuleDef
from src.domain.module_family_service import resolve_module_with_family_registry


def test_resolve_module_with_family_registry_uses_module_family_key():
    module = ModuleDef(
        name="TEST_SVC_1",
        module_family="wardrobe",
        cabinet_kind="",
        ref_point="",
        height_mm=0.0,
        depth_mm=0.0,
        material_profile_key="",
    )

    resolved = resolve_module_with_family_registry(module)

    assert resolved.module_family == "wardrobe"
    assert resolved.cabinet_kind == "tall"
    assert resolved.ref_point == "LBB"
    assert resolved.height_mm == 2300.0
    assert resolved.depth_mm == 620.0


def test_resolve_module_with_family_registry_uses_fallback_for_unknown_family():
    module = ModuleDef(
        name="TEST_SVC_2",
        module_family="unknown_family",
        cabinet_kind="",
        ref_point="",
        height_mm=0.0,
        depth_mm=0.0,
        material_profile_key="",
    )

    resolved = resolve_module_with_family_registry(
        module,
        fallback_family_key="display",
    )

    assert resolved.module_family == "display"
    assert resolved.cabinet_kind == "display"
    assert resolved.ref_point == "LBB"
    assert resolved.height_mm == 1800.0
    assert resolved.depth_mm == 450.0


def test_resolve_module_with_family_registry_preserves_explicit_module_values():
    module = ModuleDef(
        name="TEST_SVC_3",
        module_family="kitchen_upper",
        cabinet_kind="manual_kind",
        ref_point="MANUAL_REF",
        height_mm=1111.0,
        depth_mm=444.0,
        material_profile_key="CUSTOM_PROFILE",
    )

    resolved = resolve_module_with_family_registry(module)

    assert resolved.module_family == "kitchen_upper"
    assert resolved.cabinet_kind == "manual_kind"
    assert resolved.ref_point == "MANUAL_REF"
    assert resolved.height_mm == 1111.0
    assert resolved.depth_mm == 444.0
    assert resolved.material_profile_key == "CUSTOM_PROFILE"


def test_resolve_module_with_family_registry_does_not_mutate_input():
    module = ModuleDef(
        name="TEST_SVC_4",
        module_family="display",
        cabinet_kind="",
        ref_point="",
        height_mm=0.0,
        depth_mm=0.0,
        material_profile_key="",
    )

    resolved = resolve_module_with_family_registry(module)

    assert module.module_family == "display"
    assert module.cabinet_kind == ""
    assert module.ref_point == ""
    assert module.height_mm == 0.0
    assert module.depth_mm == 0.0
    assert module.material_profile_key == ""

    assert resolved.module_family == "display"
    assert resolved.cabinet_kind == "display"
    assert resolved.ref_point == "LBB"
    assert resolved.height_mm == 1800.0
    assert resolved.depth_mm == 450.0