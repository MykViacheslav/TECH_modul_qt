from src.domain.module_models import ModuleFamilyDef


def test_module_family_def_defaults():
    family = ModuleFamilyDef()

    assert family.key == "kitchen_lower"
    assert family.name_pl == "Szafka dolna"
    assert family.default_cabinet_kind == "lower"
    assert family.default_ref_point == "LBB"
    assert family.default_height_mm == 720.0
    assert family.default_depth_mm == 560.0
    assert family.default_material_profile_key == ""

    assert family.allow_inherit_height_from_wall is True
    assert family.allow_inherit_depth_from_wall is False
    assert family.allow_inherit_materials_from_group is True
    assert family.allow_inherit_edgeband_from_group is True


def test_module_family_def_to_dict_contains_all_domain_fields():
    family = ModuleFamilyDef(
        key="wardrobe",
        name_pl="Szafa",
        default_cabinet_kind="tall",
        default_ref_point="LTF",
        default_height_mm=2300.0,
        default_depth_mm=620.0,
        default_material_profile_key="WARDROBE_OAK",
        allow_inherit_height_from_wall=False,
        allow_inherit_depth_from_wall=True,
        allow_inherit_materials_from_group=False,
        allow_inherit_edgeband_from_group=False,
    )

    d = family.to_dict()

    assert d["key"] == "wardrobe"
    assert d["name_pl"] == "Szafa"
    assert d["default_cabinet_kind"] == "tall"
    assert d["default_ref_point"] == "LTF"
    assert d["default_height_mm"] == 2300.0
    assert d["default_depth_mm"] == 620.0
    assert d["default_material_profile_key"] == "WARDROBE_OAK"
    assert d["allow_inherit_height_from_wall"] is False
    assert d["allow_inherit_depth_from_wall"] is True
    assert d["allow_inherit_materials_from_group"] is False
    assert d["allow_inherit_edgeband_from_group"] is False


def test_module_family_def_from_dict_reads_domain_fields():
    d = {
        "key": "display",
        "name_pl": "Witryna",
        "default_cabinet_kind": "display",
        "default_ref_point": "CBB",
        "default_height_mm": 1800.0,
        "default_depth_mm": 450.0,
        "default_material_profile_key": "DISPLAY_GLASS",
        "allow_inherit_height_from_wall": False,
        "allow_inherit_depth_from_wall": True,
        "allow_inherit_materials_from_group": True,
        "allow_inherit_edgeband_from_group": False,
    }

    family = ModuleFamilyDef.from_dict(d)

    assert family.key == "display"
    assert family.name_pl == "Witryna"
    assert family.default_cabinet_kind == "display"
    assert family.default_ref_point == "CBB"
    assert family.default_height_mm == 1800.0
    assert family.default_depth_mm == 450.0
    assert family.default_material_profile_key == "DISPLAY_GLASS"
    assert family.allow_inherit_height_from_wall is False
    assert family.allow_inherit_depth_from_wall is True
    assert family.allow_inherit_materials_from_group is True
    assert family.allow_inherit_edgeband_from_group is False


def test_module_family_def_roundtrip_keeps_domain_fields():
    family1 = ModuleFamilyDef(
        key="kitchen_upper",
        name_pl="Szafka gorna",
        default_cabinet_kind="upper",
        default_ref_point="LTB",
        default_height_mm=720.0,
        default_depth_mm=320.0,
        default_material_profile_key="UPPER_WHITE",
        allow_inherit_height_from_wall=True,
        allow_inherit_depth_from_wall=False,
        allow_inherit_materials_from_group=True,
        allow_inherit_edgeband_from_group=True,
    )

    d = family1.to_dict()
    family2 = ModuleFamilyDef.from_dict(d)

    assert family2.key == "kitchen_upper"
    assert family2.name_pl == "Szafka gorna"
    assert family2.default_cabinet_kind == "upper"
    assert family2.default_ref_point == "LTB"
    assert family2.default_height_mm == 720.0
    assert family2.default_depth_mm == 320.0
    assert family2.default_material_profile_key == "UPPER_WHITE"
    assert family2.allow_inherit_height_from_wall is True
    assert family2.allow_inherit_depth_from_wall is False
    assert family2.allow_inherit_materials_from_group is True
    assert family2.allow_inherit_edgeband_from_group is True