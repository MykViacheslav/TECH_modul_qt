from src.domain.material_profile_models import MaterialProfileDef


def test_material_profile_def_defaults():
    profile = MaterialProfileDef()

    assert profile.key == "STD_WHITE"
    assert profile.name_pl == "Standard bialy"
    assert profile.material_map == {}
    assert profile.edgeband_map == {}
    assert profile.hardware_vendor_map == {}
    assert profile.description == ""


def test_material_profile_def_to_dict_contains_all_fields():
    profile = MaterialProfileDef(
        key="OAK_PREMIUM",
        name_pl="Deb premium",
        material_map={
            "side": "PB18",
            "top": "PB18",
            "bottom": "PB18",
            "back": "HDF2.5",
            "front": "MDF19_LAK",
        },
        edgeband_map={
            "side": "ABS 2.0",
            "top": "ABS 2.0",
            "bottom": "ABS 2.0",
            "front": "ABS 2.0",
        },
        hardware_vendor_map={
            "hinge": "blum",
            "drawer_system": "blum",
        },
        description="Profil testowy premium",
    )

    d = profile.to_dict()

    assert d["key"] == "OAK_PREMIUM"
    assert d["name_pl"] == "Deb premium"
    assert d["material_map"]["side"] == "PB18"
    assert d["material_map"]["back"] == "HDF2.5"
    assert d["material_map"]["front"] == "MDF19_LAK"
    assert d["edgeband_map"]["side"] == "ABS 2.0"
    assert d["edgeband_map"]["front"] == "ABS 2.0"
    assert d["hardware_vendor_map"]["hinge"] == "blum"
    assert d["description"] == "Profil testowy premium"


def test_material_profile_def_from_dict_reads_all_fields():
    d = {
        "key": "WARDROBE_GRAPHITE",
        "name_pl": "Szafa grafit",
        "material_map": {
            "side": "PB16",
            "top": "PB16",
            "bottom": "PB16",
            "shelf": "PB16",
            "front": "MDF19",
        },
        "edgeband_map": {
            "side": "ABS 2.0",
            "top": "ABS 2.0",
            "bottom": "ABS 2.0",
            "shelf": "ABS 2.0",
        },
        "hardware_vendor_map": {
            "hinge": "hettich",
            "drawer_system": "hettich",
        },
        "description": "Profil do szaf grafitowych",
    }

    profile = MaterialProfileDef.from_dict(d)

    assert profile.key == "WARDROBE_GRAPHITE"
    assert profile.name_pl == "Szafa grafit"
    assert profile.material_map["side"] == "PB16"
    assert profile.material_map["front"] == "MDF19"
    assert profile.edgeband_map["shelf"] == "ABS 2.0"
    assert profile.hardware_vendor_map["hinge"] == "hettich"
    assert profile.description == "Profil do szaf grafitowych"


def test_material_profile_def_roundtrip_keeps_fields():
    profile1 = MaterialProfileDef(
        key="DISPLAY_GLASS",
        name_pl="Witryna premium",
        material_map={
            "side": "PB18",
            "top": "PB18",
            "bottom": "PB18",
            "front": "MDF19_LAK",
        },
        edgeband_map={
            "side": "ABS 0.8",
            "top": "ABS 0.8",
            "bottom": "ABS 0.8",
        },
        hardware_vendor_map={"hinge": "blum"},
        description="Profil do witryn",
    )

    d = profile1.to_dict()
    profile2 = MaterialProfileDef.from_dict(d)

    assert profile2.key == "DISPLAY_GLASS"
    assert profile2.name_pl == "Witryna premium"
    assert profile2.material_map["front"] == "MDF19_LAK"
    assert profile2.edgeband_map["top"] == "ABS 0.8"
    assert profile2.hardware_vendor_map["hinge"] == "blum"
    assert profile2.description == "Profil do witryn"
