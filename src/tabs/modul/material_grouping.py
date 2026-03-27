from __future__ import annotations


MATERIAL_EDGE_GROUP_KEYS: dict[str, tuple[str, ...]] = {
    "carcass": ("carcass", "side", "top", "bottom", "shelf", "divider"),
    "front": ("front",),
    "back": ("back",),
}

PROFILE_GROUP_KEYS: dict[str, tuple[str, ...]] = {
    "carcass": ("carcass", "side", "top", "bottom", "shelf", "divider"),
    "front": ("front",),
    "back": ("back",),
}


def resolve_group_edgeband_defaults(
    edgebands: dict[str, str] | None,
    fallback_key: str = "Brak",
) -> dict[str, str]:
    source = dict(edgebands or {})
    fallback = str(fallback_key or "Brak").strip() or "Brak"
    out: dict[str, str] = {}

    for group_key, logical_keys in MATERIAL_EDGE_GROUP_KEYS.items():
        selected = ""
        for logical_key in logical_keys:
            raw = str(source.get(logical_key, "") or "").strip()
            if raw:
                selected = raw
                break
        out[group_key] = selected or fallback

    return out


def expand_group_edgebands_to_module_map(
    group_defaults: dict[str, str] | None,
    base_map: dict[str, str] | None = None,
) -> dict[str, str]:
    source = dict(group_defaults or {})
    out = dict(base_map or {})

    for group_key, logical_keys in MATERIAL_EDGE_GROUP_KEYS.items():
        selected = str(source.get(group_key, out.get(group_key, "Brak")) or "Brak").strip() or "Brak"
        out[group_key] = selected
        for logical_key in logical_keys:
            out[logical_key] = selected

    return out


def normalize_part_key_for_model(part_key: str) -> str:
    base_key = str(part_key or "").strip()
    if "__" in base_key:
        base_key = base_key.split("__", 1)[0]
    if "@" in base_key:
        base_key = base_key.split("@", 1)[0]
    return base_key


def get_material_edge_group_for_part_key(part_key: str) -> str:
    base_key = normalize_part_key_for_model(part_key)

    if base_key == "front":
        return "front"
    if base_key == "back":
        return "back"
    if base_key.startswith("shelf_") or base_key == "shelf":
        return "carcass"
    if base_key.startswith("divider_") or base_key == "divider":
        return "carcass"
    if base_key in ("side_left", "side_right", "top", "bottom"):
        return "carcass"

    return "carcass"


def get_material_group_for_part_key(part_key: str) -> str:
    return get_material_edge_group_for_part_key(part_key)


def collapse_profile_map_to_groups(
    source_map: dict[str, str] | None,
    fallback_map: dict[str, str] | None = None,
) -> dict[str, str]:
    source = dict(source_map or {})
    fallback = dict(fallback_map or {})
    out: dict[str, str] = {}

    for group_key, logical_keys in PROFILE_GROUP_KEYS.items():
        selected = ""
        for logical_key in logical_keys:
            raw = str(source.get(logical_key, "") or "").strip()
            if raw:
                selected = raw
                break
        if not selected:
            selected = str(fallback.get(group_key, "") or "").strip()
        if selected:
            out[group_key] = selected

    return out
