from src.domain.module_models import ModuleDef, ModuleFamilyDef
from src.domain.module_family_resolver import resolve_module_family


def test_resolve_module_family_returns_copy_when_family_is_none():
    module = ModuleDef(
        name="TEST_A",
        width_mm=800.0,
        depth_mm=500.0,
        height_mm=700.0,
        cabinet_kind="lower",
        ref_point="LBB",
        module_family="kitchen_lower",
        material_profile_key="BASE_PROFILE",
        inherit_height_from_wall=True,
        inherit_depth_from_wall=True,
        inherit_materials_from_group=True,
        inherit_edgeband_from_group=True,
    )

    resolved = resolve_module_family(module, None)

    assert resolved is not module
    assert resolved.to_dict() == module.to_dict()


def test_resolve_module_family_applies_missing_defaults():
    module = ModuleDef(
        name="TEST_B",
        width_mm=900.0,
        depth_mm=0.0,
        height_mm=0.0,
        cabinet_kind="",
        ref_point="",
        module_family="custom_old",
        material_profile_key="",
    )

    family = ModuleFamilyDef(
        key="wardrobe",
        name_pl="Szafa",
        default_cabinet_kind="tall",
        default_ref_point="LTF",
        default_height_mm=2300.0,
        default_depth_mm=620.0,
        default_material_profile_key="WARDROBE_OAK",
        allow_inherit_height_from_wall=True,
        allow_inherit_depth_from_wall=True,
        allow_inherit_materials_from_group=True,
        allow_inherit_edgeband_from_group=True,
    )

    resolved = resolve_module_family(module, family)

    assert resolved.module_family == "wardrobe"
    assert resolved.cabinet_kind == "tall"
    assert resolved.ref_point == "LTF"
    assert resolved.height_mm == 2300.0
    assert resolved.depth_mm == 620.0
    assert resolved.material_profile_key == "WARDROBE_OAK"


def test_resolve_module_family_does_not_override_explicit_module_values():
    module = ModuleDef(
        name="TEST_C",
        width_mm=800.0,
        depth_mm=510.0,
        height_mm=715.0,
        cabinet_kind="upper",
        ref_point="LBT",
        module_family="custom_manual",
        material_profile_key="MY_PROFILE",
    )

    family = ModuleFamilyDef(
        key="kitchen_lower",
        name_pl="Szafka dolna",
        default_cabinet_kind="lower",
        default_ref_point="LBB",
        default_height_mm=720.0,
        default_depth_mm=560.0,
        default_material_profile_key="LOWER_STD",
    )

    resolved = resolve_module_family(module, family)

    assert resolved.module_family == "kitchen_lower"
    assert resolved.cabinet_kind == "upper"
    assert resolved.ref_point == "LBT"
    assert resolved.height_mm == 715.0
    assert resolved.depth_mm == 510.0
    assert resolved.material_profile_key == "MY_PROFILE"


def test_resolve_module_family_turns_off_disallowed_inheritance_flags():
    module = ModuleDef(
        name="TEST_D",
        inherit_height_from_wall=True,
        inherit_depth_from_wall=True,
        inherit_materials_from_group=True,
        inherit_edgeband_from_group=True,
    )

    family = ModuleFamilyDef(
        key="display",
        name_pl="Witryna",
        allow_inherit_height_from_wall=False,
        allow_inherit_depth_from_wall=True,
        allow_inherit_materials_from_group=False,
        allow_inherit_edgeband_from_group=False,
    )

    resolved = resolve_module_family(module, family)

    assert resolved.inherit_height_from_wall is False
    assert resolved.inherit_depth_from_wall is True
    assert resolved.inherit_materials_from_group is False
    assert resolved.inherit_edgeband_from_group is False


def test_resolve_module_family_does_not_mutate_input_module():
    module = ModuleDef(
        name="TEST_E",
        depth_mm=0.0,
        height_mm=0.0,
        cabinet_kind="",
        ref_point="",
        material_profile_key="",
        inherit_height_from_wall=True,
    )

    family = ModuleFamilyDef(
        key="kitchen_upper",
        name_pl="Szafka gorna",
        default_cabinet_kind="upper",
        default_ref_point="LTB",
        default_height_mm=720.0,
        default_depth_mm=320.0,
        default_material_profile_key="UPPER_WHITE",
        allow_inherit_height_from_wall=False,
    )

    resolved = resolve_module_family(module, family)

    assert module.module_family == "kitchen_lower"
    assert module.cabinet_kind == ""
    assert module.ref_point == ""
    assert module.height_mm == 0.0
    assert module.depth_mm == 0.0
    assert module.material_profile_key == ""
    assert module.inherit_height_from_wall is True

    assert resolved.module_family == "kitchen_upper"
    assert resolved.cabinet_kind == "upper"
    assert resolved.ref_point == "LTB"
    assert resolved.height_mm == 720.0
    assert resolved.depth_mm == 320.0
    assert resolved.material_profile_key == "UPPER_WHITE"
    assert resolved.inherit_height_from_wall is False