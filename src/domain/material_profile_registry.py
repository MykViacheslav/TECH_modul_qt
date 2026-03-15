from __future__ import annotations

from typing import Dict, List

from src.domain.material_profile_models import MaterialProfileDef


def _clone_profile(profile: MaterialProfileDef) -> MaterialProfileDef:
    return MaterialProfileDef.from_dict(profile.to_dict())


def build_default_material_profiles() -> List[MaterialProfileDef]:
    """
    Zwraca liste domyslnych profili materialowo-okuciowych.
    Kazde wywolanie zwraca swieze obiekty.
    """

    profiles = [
        MaterialProfileDef(
            key="STD_WHITE",
            name_pl="Standard bialy",
            material_map={
                "side": "PB18",
                "top": "PB18",
                "bottom": "PB18",
                "back": "HDF2.5",
                "shelf": "PB18",
                "divider": "PB18",
                "front": "MDF19",
            },
            edgeband_map={
                "side": "ABS 0.8",
                "top": "ABS 0.8",
                "bottom": "ABS 0.8",
                "shelf": "ABS 0.8",
                "divider": "ABS 0.8",
                "front": "ABS 0.8",
                "back": "Brak",
            },
            hardware_vendor_map={
                "hinge": "generic",
                "drawer_system": "generic",
            },
            description="Uniwersalny profil dla standardowych bialych modulow.",
        ),
        MaterialProfileDef(
            key="OAK_PREMIUM",
            name_pl="Deb premium",
            material_map={
                "side": "PB18",
                "top": "PB18",
                "bottom": "PB18",
                "back": "HDF2.5",
                "shelf": "PB18",
                "divider": "PB18",
                "front": "MDF19_LAK",
            },
            edgeband_map={
                "side": "ABS 2.0",
                "top": "ABS 2.0",
                "bottom": "ABS 2.0",
                "shelf": "ABS 2.0",
                "divider": "ABS 2.0",
                "front": "ABS 2.0",
                "back": "Brak",
            },
            hardware_vendor_map={
                "hinge": "blum",
                "drawer_system": "blum",
            },
            description="Wariant premium: lakierowany front, grubsza okleina i Blum.",
        ),
        MaterialProfileDef(
            key="WARDROBE_GRAPHITE",
            name_pl="Szafa grafit",
            material_map={
                "side": "PB16",
                "top": "PB16",
                "bottom": "PB16",
                "back": "HDF3",
                "shelf": "PB16",
                "divider": "PB16",
                "front": "MDF19",
            },
            edgeband_map={
                "side": "ABS 2.0",
                "top": "ABS 2.0",
                "bottom": "ABS 2.0",
                "shelf": "ABS 2.0",
                "divider": "ABS 2.0",
                "front": "ABS 2.0",
                "back": "Brak",
            },
            hardware_vendor_map={
                "hinge": "hettich",
                "drawer_system": "hettich",
            },
            description="Szafowy profil ekonomiczny z Hettich i plyta 16 mm.",
        ),
        MaterialProfileDef(
            key="DISPLAY_GLASS",
            name_pl="Witryna premium",
            material_map={
                "side": "PB18",
                "top": "PB18",
                "bottom": "PB18",
                "back": "HDF2.5",
                "shelf": "PB18",
                "divider": "PB18",
                "front": "MDF19_LAK",
            },
            edgeband_map={
                "side": "ABS 0.8",
                "top": "ABS 0.8",
                "bottom": "ABS 0.8",
                "shelf": "ABS 0.8",
                "divider": "ABS 0.8",
                "front": "ABS 0.8",
                "back": "Brak",
            },
            hardware_vendor_map={
                "hinge": "blum",
                "drawer_system": "blum",
            },
            description="Profil pod witryny i zabudowy premium z lakierowanym frontem.",
        ),
    ]

    return [_clone_profile(profile) for profile in profiles]


def build_default_material_profile_map() -> Dict[str, MaterialProfileDef]:
    result: Dict[str, MaterialProfileDef] = {}
    for profile in build_default_material_profiles():
        result[profile.key] = profile
    return result


def get_default_material_profile(
    key: str,
    fallback_key: str = "STD_WHITE",
) -> MaterialProfileDef:
    profile_map = build_default_material_profile_map()

    normalized_key = (key or "").strip()
    normalized_fallback = (fallback_key or "STD_WHITE").strip() or "STD_WHITE"

    if normalized_key in profile_map:
        return _clone_profile(profile_map[normalized_key])

    if normalized_fallback in profile_map:
        return _clone_profile(profile_map[normalized_fallback])

    first_profile = next(iter(profile_map.values()))
    return _clone_profile(first_profile)
