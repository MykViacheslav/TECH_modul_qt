import sqlite3
from pathlib import Path

def check():
    db_path = Path("C:/PythonProject/TECH_modul/data/tech_modul.db")
    if not db_path.exists():
        print("No DB")
        return
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    for table in ["calendar_events", "order_calendar_events"]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            print(f"{table}: {cursor.fetchone()[0]}")
        except Exception as e:
            print(f"{table}: error {e}")
    conn.close()

if __name__ == "__main__":
    check()
