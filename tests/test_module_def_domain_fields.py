from src.domain.module_models import ModuleDef


def test_module_def_new_domain_fields_have_defaults():
    m = ModuleDef()

    assert m.module_family == "kitchen_lower"
    assert m.base_group == "kitchen"
    assert m.material_profile_key == ""
    assert m.module_type == "legacy"

    assert m.inherit_height_from_wall is False
    assert m.inherit_depth_from_wall is False
    assert m.inherit_materials_from_group is False
    assert m.inherit_edgeband_from_group is False

    assert m.front_layout in ("overlay", "inset")
    assert m.facade_mode in ("doors", "drawers", "mixed")
    assert m.shelf_mount in ("left", "right", "both")
    assert m.drawer_layout_mode in ("equal", "small_top", "small_bottom")
    assert m.drawer_small_front_height_mm > 0.0


def test_module_def_to_dict_contains_new_domain_fields():
    m = ModuleDef(
        name="X1",
        base_group="bathroom",
        module_family="kitchen_upper",
        module_type="hanging",
        material_profile_key="UPPER_WHITE",
        inherit_height_from_wall=True,
        inherit_depth_from_wall=True,
        inherit_materials_from_group=True,
        inherit_edgeband_from_group=True,
    )

    d = m.to_dict()

    assert d["module_family"] == "kitchen_upper"
    assert d["module_type"] == "hanging"
    assert d["base_group"] == "bathroom"
    assert d["material_profile_key"] == "UPPER_WHITE"
    assert d["inherit_height_from_wall"] is True
    assert d["inherit_depth_from_wall"] is True
    assert d["inherit_materials_from_group"] is True
    assert d["inherit_edgeband_from_group"] is True


def test_module_def_from_dict_reads_new_domain_fields():
    d = {
        "name": "X2",
        "width_mm": 900.0,
        "depth_mm": 560.0,
        "height_mm": 720.0,
        "base_group": "wardrobe",
        "module_family": "wardrobe",
        "module_type": "corner",
        "material_profile_key": "WARDROBE_OAK",
        "inherit_height_from_wall": True,
        "inherit_depth_from_wall": False,
        "inherit_materials_from_group": True,
        "inherit_edgeband_from_group": False,
        "visible_parts": ["side_left", "side_right", "top", "bottom", "front"],
    }

    m = ModuleDef.from_dict(d)

    assert m.name == "X2"
    assert m.width_mm == 900.0
    assert m.depth_mm == 560.0
    assert m.height_mm == 720.0

    assert m.module_family == "wardrobe"
    assert m.module_type == "corner"
    assert m.base_group == "wardrobe"
    assert m.material_profile_key == "WARDROBE_OAK"

    assert m.inherit_height_from_wall is True
    assert m.inherit_depth_from_wall is False
    assert m.inherit_materials_from_group is True
    assert m.inherit_edgeband_from_group is False

    assert "front" in m.visible_parts


def test_module_def_roundtrip_keeps_new_domain_fields():
    m1 = ModuleDef(
        name="ROUNDTRIP",
        base_group="other",
        module_family="display",
        module_type="legs_plinth",
        material_profile_key="DISPLAY_GLASS",
        inherit_height_from_wall=True,
        inherit_depth_from_wall=True,
        inherit_materials_from_group=False,
        inherit_edgeband_from_group=True,
    )

    d = m1.to_dict()
    m2 = ModuleDef.from_dict(d)

    assert m2.name == "ROUNDTRIP"
    assert m2.base_group == "other"
    assert m2.module_family == "display"
    assert m2.module_type == "legs_plinth"
    assert m2.material_profile_key == "DISPLAY_GLASS"
    assert m2.inherit_height_from_wall is True
    assert m2.inherit_depth_from_wall is True
    assert m2.inherit_materials_from_group is False
    assert m2.inherit_edgeband_from_group is True


def test_module_def_normalizes_shelf_mount_and_persists_drawer_layout():
    m = ModuleDef.from_dict(
        {
            "name": "SHELF_BOTH",
            "shelf_mount": "both",
            "drawer_layout_mode": "small_top",
            "drawer_small_front_height_mm": 155.0,
        }
    )

    assert m.shelf_mount == "both"
    assert m.drawer_layout_mode == "small_top"
    assert m.drawer_small_front_height_mm == 155.0

    d = m.to_dict()
    assert d["shelf_mount"] == "both"
    assert d["drawer_layout_mode"] == "small_top"
    assert d["drawer_small_front_height_mm"] == 155.0


def test_module_def_base_group_defaults_from_family_when_missing():
    m = ModuleDef(module_family="wardrobe", base_group="")

    assert m.base_group == "wardrobe"


def test_module_def_keeps_custom_base_group_name():
    m = ModuleDef(module_family="display", base_group="Biuro premium")

    assert m.base_group == "Biuro premium"
