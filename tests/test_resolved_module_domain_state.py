from src.domain.resolved_module_models import ResolvedModuleDomainState


def test_resolved_module_domain_state_defaults():
    state = ResolvedModuleDomainState()

    assert state.module_name == "MOD_TEST_1"
    assert state.module_family_key == "kitchen_lower"
    assert state.material_profile_key == "STD_WHITE"
    assert state.cabinet_kind == "lower"
    assert state.ref_point == "LBB"
    assert state.width_mm == 820.0
    assert state.depth_mm == 500.0
    assert state.height_mm == 700.0
    assert state.materials == {}


def test_resolved_module_domain_state_to_dict_and_from_dict_roundtrip():
    state1 = ResolvedModuleDomainState(
        module_name="SZAFA_01",
        module_family_key="wardrobe",
        material_profile_key="WARDROBE_GRAPHITE",
        cabinet_kind="tall",
        ref_point="LBB",
        width_mm=1000.0,
        depth_mm=620.0,
        height_mm=2300.0,
        inherit_height_from_wall=True,
        inherit_depth_from_wall=True,
        inherit_materials_from_group=False,
        inherit_edgeband_from_group=True,
        materials={
            "side": "PB18_GRAPHITE",
            "front": "MDF18_GRAPHITE",
        },
    )

    d = state1.to_dict()
    state2 = ResolvedModuleDomainState.from_dict(d)

    assert state2.module_name == "SZAFA_01"
    assert state2.module_family_key == "wardrobe"
    assert state2.material_profile_key == "WARDROBE_GRAPHITE"
    assert state2.cabinet_kind == "tall"
    assert state2.ref_point == "LBB"
    assert state2.width_mm == 1000.0
    assert state2.depth_mm == 620.0
    assert state2.height_mm == 2300.0
    assert state2.inherit_height_from_wall is True
    assert state2.inherit_depth_from_wall is True
    assert state2.inherit_materials_from_group is False
    assert state2.inherit_edgeband_from_group is True
    assert state2.materials["side"] == "PB18_GRAPHITE"
    assert state2.materials["front"] == "MDF18_GRAPHITE"