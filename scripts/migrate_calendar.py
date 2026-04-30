import sqlite3
import os
from pathlib import Path

def migrate():
    # Use hardcoded path for safety in this scratch script
    db_path = Path("C:/PythonProject/TECH_modul/data/tech_modul.db")
    if not db_path.exists():
        print(f"DB not found at {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get current columns
    cursor.execute("PRAGMA table_info(calendar_events)")
    columns = [c[1] for c in cursor.fetchall()]
    
    new_cols = [
        ("date_end", "TEXT"),
        ("location", "TEXT"),
        ("notes", "TEXT"),
        ("all_day", "INTEGER DEFAULT 1")
    ]
    
    for col_name, col_type in new_cols:
        if col_name not in columns:
            print(f"Adding column {col_name}...")
            cursor.execute(f"ALTER TABLE calendar_events ADD COLUMN {col_name} {col_type}")
    
    conn.commit()
    conn.close()
    print("Migration finished.")

if __name__ == "__main__":
    migrate()
