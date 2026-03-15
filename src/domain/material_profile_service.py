from __future__ import annotations

from dataclasses import replace

from src.domain.module_models import ModuleDef
from src.domain.material_profile_registry import get_default_material_profile


def resolve_module_with_material_profile_registry(
    module: ModuleDef,
    fallback_profile_key: str = "STD_WHITE",
) -> ModuleDef:
    """
    Resolves module materials and edgebands by:
    1) reading module.material_profile_key,
    2) loading a profile from the default registry,
    3) filling missing entries in module.materials and module.edgebands.

    Rules:
    - does not mutate the input `module`
    - if module.material_profile_key is empty or unknown,
      uses fallback_profile_key
    - explicit module.materials and module.edgebands entries
      take precedence over profile values
    - generic hardware vendors can be upgraded from the profile
    """

    profile = get_default_material_profile(
        key=module.material_profile_key,
        fallback_key=fallback_profile_key,
    )

    resolved_materials = dict(profile.material_map or {})
    resolved_materials.update(dict(module.materials or {}))

    resolved_edgebands = dict(profile.edgeband_map or {})
    resolved_edgebands.update(dict(module.edgebands or {}))

    profile_hardware = dict(profile.hardware_vendor_map or {})

    current_hinge_vendor = str(getattr(module, "hinge_vendor", "generic") or "generic").strip().lower() or "generic"
    current_drawer_vendor = str(getattr(module, "drawer_vendor", "generic") or "generic").strip().lower() or "generic"

    if current_hinge_vendor == "generic":
        current_hinge_vendor = str(profile_hardware.get("hinge", current_hinge_vendor) or current_hinge_vendor).strip().lower() or "generic"

    if current_drawer_vendor == "generic":
        current_drawer_vendor = str(profile_hardware.get("drawer_system", current_drawer_vendor) or current_drawer_vendor).strip().lower() or "generic"

    return replace(
        module,
        material_profile_key=profile.key,
        materials=resolved_materials,
        edgebands=resolved_edgebands,
        hinge_vendor=current_hinge_vendor,
        drawer_vendor=current_drawer_vendor,
    )
