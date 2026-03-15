from src.domain.material_profile_registry import (
    build_default_material_profiles,
    build_default_material_profile_map,
    get_default_material_profile,
)


def test_build_default_material_profiles_contains_expected_keys():
    profiles = build_default_material_profiles()
    keys = [p.key for p in profiles]

    assert "STD_WHITE" in keys
    assert "OAK_PREMIUM" in keys
    assert "WARDROBE_GRAPHITE" in keys
    assert "DISPLAY_GLASS" in keys


def test_build_default_material_profiles_contains_human_readable_names():
    profiles = build_default_material_profiles()
    by_key = {p.key: p for p in profiles}

    assert by_key["STD_WHITE"].name_pl == "Standard bialy"
    assert by_key["OAK_PREMIUM"].name_pl == "Deb premium"
    assert by_key["WARDROBE_GRAPHITE"].name_pl == "Szafa grafit"
    assert by_key["DISPLAY_GLASS"].name_pl == "Witryna premium"


def test_build_default_material_profile_map_has_unique_keys():
    profiles = build_default_material_profiles()
    profile_map = build_default_material_profile_map()

    assert len(profile_map) == len(profiles)
    assert sorted(profile_map.keys()) == sorted([p.key for p in profiles])


def test_get_default_material_profile_returns_exact_match():
    profile = get_default_material_profile("WARDROBE_GRAPHITE")

    assert profile.key == "WARDROBE_GRAPHITE"
    assert profile.name_pl == "Szafa grafit"
    assert profile.material_map["side"] == "PB16"
    assert profile.edgeband_map["side"] == "ABS 2.0"
    assert profile.hardware_vendor_map["hinge"] == "hettich"


def test_get_default_material_profile_returns_fallback_for_unknown_key():
    profile = get_default_material_profile("UNKNOWN_PROFILE")

    assert profile.key == "STD_WHITE"
    assert profile.name_pl == "Standard bialy"


def test_get_default_material_profile_returns_given_fallback_key():
    profile = get_default_material_profile("UNKNOWN_PROFILE", fallback_key="DISPLAY_GLASS")

    assert profile.key == "DISPLAY_GLASS"
    assert profile.name_pl == "Witryna premium"


def test_material_profile_registry_returns_fresh_objects_each_time():
    profile1 = get_default_material_profile("STD_WHITE")
    profile2 = get_default_material_profile("STD_WHITE")

    assert profile1 is not profile2

    profile1.name_pl = "Zmiana testowa"

    profile3 = get_default_material_profile("STD_WHITE")
    assert profile2.name_pl == "Standard bialy"
    assert profile3.name_pl == "Standard bialy"
