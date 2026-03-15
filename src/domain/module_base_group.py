from __future__ import annotations


BASE_GROUP_ORDER: tuple[str, ...] = (
    "kitchen",
    "wardrobe",
    "bathroom",
    "other",
)


BASE_GROUP_LABELS_PL: dict[str, str] = {
    "kitchen": "Kuchnia",
    "wardrobe": "Szafy",
    "bathroom": "Lazienka",
    "other": "Inne",
}


FAMILY_TO_BASE_GROUP: dict[str, str] = {
    "kitchen_lower": "kitchen",
    "kitchen_upper": "kitchen",
    "wardrobe": "wardrobe",
}


def is_predefined_module_base_group(key: str) -> bool:
    normalized = str(key or "").strip().lower()
    return normalized in BASE_GROUP_LABELS_PL


def normalize_module_base_group(key: str, fallback_key: str = "other") -> str:
    raw_value = str(key or "").strip()
    fallback_raw = str(fallback_key or "other").strip()

    normalized = raw_value.lower()
    if normalized in BASE_GROUP_LABELS_PL:
        return normalized
    if raw_value:
        return raw_value

    fallback_normalized = fallback_raw.lower()
    if fallback_normalized in BASE_GROUP_LABELS_PL:
        return fallback_normalized
    if fallback_raw:
        return fallback_raw
    return "other"


def default_module_base_group_for_family(module_family: str, fallback_key: str = "other") -> str:
    normalized_family = str(module_family or "").strip()
    if normalized_family in FAMILY_TO_BASE_GROUP:
        return FAMILY_TO_BASE_GROUP[normalized_family]
    return normalize_module_base_group("", fallback_key=fallback_key)


def module_base_group_label_pl(key: str) -> str:
    normalized = normalize_module_base_group(key)
    if normalized in BASE_GROUP_LABELS_PL:
        return BASE_GROUP_LABELS_PL[normalized]
    return normalized


def sort_module_base_groups(groups: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    seen: list[str] = []
    for group in groups:
        normalized = normalize_module_base_group(group)
        if normalized and normalized not in seen:
            seen.append(normalized)

    predefined = [group for group in BASE_GROUP_ORDER if group in seen]
    custom = sorted(
        [group for group in seen if group not in BASE_GROUP_ORDER],
        key=lambda value: module_base_group_label_pl(value).lower(),
    )
    return predefined + custom
