"""
Konfiguracja modułu MSI Tech — stałe produkcyjne i domyślne wartości.
"""
from __future__ import annotations

# --- grubości płyt [mm] ---
THICKNESS_18 = 18.0   # standardowa wiórowa
THICKNESS_16 = 16.0   # cieńsza / szuflady
THICKNESS_HDF = 3.0   # plecy HDF

# --- wymiary graniczne modułu [mm] ---
MODULE_WIDTH_MIN = 200.0
MODULE_WIDTH_MAX = 2400.0
MODULE_HEIGHT_MIN = 200.0
MODULE_HEIGHT_MAX = 2700.0
MODULE_DEPTH_MIN = 150.0
MODULE_DEPTH_MAX = 700.0

# --- systemy szuflad ---
DRAWER_SYSTEM_DEFAULT = "blum_antaro"
DRAWER_SYSTEM_CHOICES = ["blum_antaro", "gtv_modernbox"]

# --- zawiasy ---
HINGE_CUP_DIAMETER = 35       # standardowy otworek Ø35
HINGE_INSET_MM = 3.0          # wcisk zawias wpuszczany
HINGES_PER_DOOR_HEIGHT: dict[float, int] = {
    # klucz: max wysokość drzwi [mm] → liczba zawiasów
    800.0: 2,
    1200.0: 3,
    1800.0: 4,
    9999.0: 5,
}

# --- kołki półkowe ---
SHELF_PIN_DIAMETER = 5.0      # kołek Ø5
SHELF_PIN_DEPTH = 12.0        # głębokość otworu
SHELF_PINS_PER_SHELF = 4

# --- okleinowanie ABS ---
EDGE_ABS_THICKNESS = 2.0      # grubość ABS
EDGE_CPL_THICKNESS = 0.45     # folia CPL

# --- domyślny profil materiałowy ---
# TODO: zastąpić dynamicznym wyborem z material_profile_models.py
DEFAULT_MATERIAL_PROFILE = "wiórowa_18"
