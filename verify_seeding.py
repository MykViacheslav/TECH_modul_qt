import sys
import os
import sqlite3

# Add current dir to path
sys.path.append(os.getcwd())

try:
    from src.api.data_manager import TechModulDataManager
    dm = TechModulDataManager()
    techs = dm.get_technicians()

    print(f"Found {len(techs)} technicians:")
    for t in techs:
        print(f"- {t['name']} ({t['role']}) [Color: {t['avatar_color']}]")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
