from src.domain.module_family_registry import (
    build_default_module_families,
    build_default_module_family_map,
    get_default_module_family,
)


def test_build_default_module_families_contains_expected_keys():
    families = build_default_module_families()
    keys = [f.key for f in families]

    assert "kitchen_lower" in keys
    assert "kitchen_upper" in keys
    assert "wardrobe" in keys
    assert "display" in keys


def test_build_default_module_families_contains_polish_names():
    families = build_default_module_families()
    by_key = {f.key: f for f in families}

    assert by_key["kitchen_lower"].name_pl == "Szafka dolna"
    assert by_key["kitchen_upper"].name_pl == "Szafka gorna"
    assert by_key["wardrobe"].name_pl == "Szafa"
    assert by_key["display"].name_pl == "Witryna"


def test_build_default_module_family_map_has_unique_keys():
    families = build_default_module_families()
    family_map = build_default_module_family_map()

    assert len(family_map) == len(families)
    assert sorted(family_map.keys()) == sorted([f.key for f in families])


def test_get_default_module_family_returns_exact_match():
    family = get_default_module_family("wardrobe")

    assert family.key == "wardrobe"
    assert family.name_pl == "Szafa"
    assert family.default_cabinet_kind == "tall"
    assert family.default_depth_mm == 620.0


def test_get_default_module_family_returns_fallback_for_unknown_key():
    family = get_default_module_family("unknown_family")

    assert family.key == "kitchen_lower"
    assert family.name_pl == "Szafka dolna"


def test_get_default_module_family_returns_fallback_key_when_provided():
    family = get_default_module_family("unknown_family", fallback_key="display")

    assert family.key == "display"
    assert family.name_pl == "Witryna"


def test_registry_returns_fresh_objects_each_time():
    family1 = get_default_module_family("kitchen_lower")
    family2 = get_default_module_family("kitchen_lower")

    assert family1 is not family2

    family1.name_pl = "Zmiana testowa"

    family3 = get_default_module_family("kitchen_lower")
    assert family2.name_pl == "Szafka dolna"
    assert family3.name_pl == "Szafka dolna"