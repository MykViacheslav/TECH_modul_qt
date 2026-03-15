from __future__ import annotations

from src.domain.module_models import ModuleDef
from src.domain.module_family_registry import get_default_module_family
from src.domain.module_family_resolver import resolve_module_family


def resolve_module_with_family_registry(
    module: ModuleDef,
    fallback_family_key: str = "kitchen_lower",
) -> ModuleDef:
    """
    Rozwiazuje modul przez:
    1) odczyt module.module_family,
    2) pobranie rodziny z domyslnego registry,
    3) nalozenie rodziny przez resolver.

    Zasady:
    - nie modyfikuje wejsciowego `module`
    - jesli module.module_family jest pusty lub nieznany,
      uzywa fallback_family_key
    """

    family = get_default_module_family(
        key=module.module_family,
        fallback_key=fallback_family_key,
    )
    return resolve_module_family(module, family)