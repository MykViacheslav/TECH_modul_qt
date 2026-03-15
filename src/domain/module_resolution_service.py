from __future__ import annotations

from src.domain.module_models import ModuleDef
from src.domain.module_family_service import resolve_module_with_family_registry
from src.domain.material_profile_service import resolve_module_with_material_profile_registry
from src.domain.resolved_module_models import ResolvedModuleDomainState


def resolve_module_domain_defaults(
    module: ModuleDef,
    fallback_family_key: str = "kitchen_lower",
    fallback_profile_key: str = "STD_WHITE",
) -> ModuleDef:
    """
    Naklada na modul podstawowe domyslne reguly domain:

    1) rodzina modulu (module_family)
    2) profil materialowy (material_profile_key)

    Zasady:
    - nie modyfikuje wejsciowego `module`
    - najpierw rozwiazuje rodzine modulu
    - potem rozwiazuje profil materialowy
    """

    resolved = resolve_module_with_family_registry(
        module,
        fallback_family_key=fallback_family_key,
    )

    resolved = resolve_module_with_material_profile_registry(
        resolved,
        fallback_profile_key=fallback_profile_key,
    )

    return resolved


def build_resolved_module_domain_state(
    module: ModuleDef,
    fallback_family_key: str = "kitchen_lower",
    fallback_profile_key: str = "STD_WHITE",
) -> ResolvedModuleDomainState:
    """
    Buduje jawny, serializowalny stan resolved-domain
    na podstawie ModuleDef.
    """

    resolved = resolve_module_domain_defaults(
        module,
        fallback_family_key=fallback_family_key,
        fallback_profile_key=fallback_profile_key,
    )

    return ResolvedModuleDomainState(
        module_name=resolved.name,
        module_family_key=resolved.module_family,
        material_profile_key=resolved.material_profile_key,
        cabinet_kind=resolved.cabinet_kind,
        ref_point=resolved.ref_point,
        width_mm=float(resolved.width_mm),
        depth_mm=float(resolved.depth_mm),
        height_mm=float(resolved.height_mm),
        inherit_height_from_wall=bool(resolved.inherit_height_from_wall),
        inherit_depth_from_wall=bool(resolved.inherit_depth_from_wall),
        inherit_materials_from_group=bool(resolved.inherit_materials_from_group),
        inherit_edgeband_from_group=bool(resolved.inherit_edgeband_from_group),
        materials=dict(resolved.materials or {}),
        edgebands=dict(resolved.edgebands or {}),
    )