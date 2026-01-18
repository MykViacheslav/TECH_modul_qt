from __future__ import annotations

from typing import List, Tuple, Type
import traceback
import datetime
import pathlib


from .base import BaseTab
from .placeholder import PlaceholderTab

# Importy realnych zakładek (jeśli istnieją)
try:
    from .tab_module import Tab as ModuleTab
except Exception as e:
    ModuleTab = None
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[TAB_IMPORT_FAIL] {ts}  tab_module -> {e}"
        print(msg, flush=True)
        tb = traceback.format_exc()
        print(tb, flush=True)
        p = pathlib.Path(r"C:\PythonProject\TECH_modul\TECH_modul_qt\_handoff\tab_import_errors.txt")
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
            f.write(tb + "\n")
    except Exception:
        pass
try:
    from .tab_catalogs import Tab as CatalogsTab
except Exception as e:
    CatalogsTab = None
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[TAB_IMPORT_FAIL] {ts}  tab_catalogs -> {e}"
        print(msg, flush=True)
        tb = traceback.format_exc()
        print(tb, flush=True)
        p = pathlib.Path(r"C:\PythonProject\TECH_modul\TECH_modul_qt\_handoff\tab_import_errors.txt")
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
            f.write(tb + "\n")
    except Exception:
        pass
def build_tabs(ctx) -> List[Tuple[str, BaseTab]]:
    """
    Zwraca listę (tytuł, widget-tab).
    Każda zakładka działa niezależnie i komunikuje się przez ctx (bus/catalogs/settings).
    """
    out: List[Tuple[str, BaseTab]] = []

    # 1) Moduł (realny)
    if ModuleTab is not None:
        t = ModuleTab(ctx)
        out.append((t.TAB_TITLE_PL, t))
    else:
        out.append(("Moduł", PlaceholderTab(ctx, "Moduł")))

    # 2) Ściana
    out.append(("Ściana", PlaceholderTab(ctx, "Ściana")))

    # 3) Zestaw mebli
    out.append(("Zestaw mebli", PlaceholderTab(ctx, "Zestaw mebli")))

    # 4) Baza: materiały/okucia/krawędzie (realna, jeśli jest)
    if CatalogsTab is not None:
        t = CatalogsTab(ctx)
        out.append((t.TAB_TITLE_PL, t))
    else:
        out.append(("Baza: materiały i okucia", PlaceholderTab(ctx, "Baza: materiały i okucia")))

    # 5) Klienci
    out.append(("Klienci", PlaceholderTab(ctx, "Klienci")))

    # 6) Pracownicy
    out.append(("Pracownicy", PlaceholderTab(ctx, "Pracownicy")))

    # 7) Stałe wydatki
    out.append(("Stałe wydatki", PlaceholderTab(ctx, "Stałe wydatki")))

    # 8) Maszyny
    out.append(("Maszyny", PlaceholderTab(ctx, "Maszyny")))

    # 9) Leasingi
    out.append(("Leasingi", PlaceholderTab(ctx, "Leasingi")))

    # 10) Czynności
    out.append(("Czynności", PlaceholderTab(ctx, "Czynności")))

    # 11) Podsumowanie (wynik firmy)
    out.append(("Podsumowanie", PlaceholderTab(ctx, "Podsumowanie")))

    return out
