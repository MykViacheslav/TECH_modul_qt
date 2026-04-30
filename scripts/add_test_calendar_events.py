"""Add test calendar events to SQLite database."""
import sqlite3
import uuid
from datetime import datetime

conn = sqlite3.connect("database/tech_modul.db")
now = datetime.now().isoformat()

events = [
    {
        "id": str(uuid.uuid4()),
        "title": "Pomiar u klienta Nowak",
        "date": "2026-04-27",
        "date_end": "2026-04-27",
        "all_day": 0,
        "event_type": "pomiary",
        "station": "Biuro",
        "order_code": "ZAM-101",
        "worker_name": "Jan Pomiar",
        "client_name": "Piotr Nowak",
        "location": "ul. Dluga 15, Krakow",
        "notes": "Kuchnia + lazienka, wziac dalmierz",
        "status": "planned",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Produkcja szafek ZAM-098",
        "date": "2026-04-27",
        "date_end": "2026-04-29",
        "all_day": 1,
        "event_type": "zlecenie",
        "station": "CNC",
        "order_code": "ZAM-098",
        "worker_name": "Marek CNC",
        "client_name": "Anna Kowalska",
        "location": "",
        "notes": "Korpusy + polki, material: plyta laminowana dab",
        "status": "in_progress",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Montaz kuchni Wisniewska",
        "date": "2026-04-28",
        "date_end": "2026-04-29",
        "all_day": 1,
        "event_type": "montaz",
        "station": "Skladanie",
        "order_code": "ZAM-095",
        "worker_name": "Tomek Montaz",
        "client_name": "Maria Wisniewska",
        "location": "ul. Kwiatowa 8, Warszawa",
        "notes": "Zestaw 12 modulow, wziac uchwyt blatu",
        "status": "confirmed",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Wycena projektu Kowalski",
        "date": "2026-04-28",
        "date_end": "2026-04-28",
        "all_day": 1,
        "event_type": "wstepna_wycena",
        "station": "Biuro",
        "order_code": "ZAM-102",
        "worker_name": "Emilia Kmita",
        "client_name": "Jan Kowalski",
        "location": "",
        "notes": "Kuchnia nowoczesna, budzet ok 35tys",
        "status": "planned",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Lakierowanie frontow ZAM-097",
        "date": "2026-04-29",
        "date_end": "2026-04-30",
        "all_day": 1,
        "event_type": "zlecenie",
        "station": "Lakiernia",
        "order_code": "ZAM-097",
        "worker_name": "Adam Lakier",
        "client_name": "Katarzyna Zielinska",
        "location": "",
        "notes": "RAL 9010 mat, 24 fronty",
        "status": "planned",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Spotkanie z architektem",
        "date": "2026-04-29",
        "date_end": "2026-04-29",
        "all_day": 0,
        "event_type": "wstepna_wycena",
        "station": "Biuro",
        "order_code": "ZAM-103",
        "worker_name": "Emilia Kmita",
        "client_name": "Arch. Nowicki",
        "location": "Biuro - sala konferencyjna",
        "notes": "Projekt mebloscianka salon, materialy do przejrzenia",
        "status": "confirmed",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Transport materialow z hurtowni",
        "date": "2026-04-30",
        "date_end": "2026-04-30",
        "all_day": 1,
        "event_type": "zamowienie_mat",
        "station": "Biuro",
        "order_code": "ZAM-101",
        "worker_name": "Jan Pomiar",
        "client_name": "",
        "location": "Hurtownia Kronopol, Strzelce Opolskie",
        "notes": "Plyta MDF 18mm, obrzeze ABS",
        "status": "planned",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Poprawki szuflad ZAM-094",
        "date": "2026-04-30",
        "date_end": "2026-04-30",
        "all_day": 1,
        "event_type": "poprawki",
        "station": "Skladanie",
        "order_code": "ZAM-094",
        "worker_name": "Tomek Montaz",
        "client_name": "Robert Maj",
        "location": "",
        "notes": "Wymiana prowadnic szuflad (reklamacja)",
        "status": "in_progress",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Dzien wolny - Swieto Pracy",
        "date": "2026-05-01",
        "date_end": "2026-05-01",
        "all_day": 1,
        "event_type": "urlop",
        "station": "",
        "order_code": "",
        "worker_name": "",
        "client_name": "",
        "location": "",
        "notes": "Dzien ustawowo wolny od pracy",
        "status": "confirmed",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Pomiar u klienta Lewandowski",
        "date": "2026-05-02",
        "date_end": "2026-05-02",
        "all_day": 0,
        "event_type": "pomiary",
        "station": "Biuro",
        "order_code": "ZAM-104",
        "worker_name": "Jan Pomiar",
        "client_name": "Andrzej Lewandowski",
        "location": "ul. Ogrodowa 22, Krakow",
        "notes": "Szafy wnekowe sypialnia + garderoba",
        "status": "planned",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Produkcja korpusow ZAM-101",
        "date": "2026-05-04",
        "date_end": "2026-05-06",
        "all_day": 1,
        "event_type": "zlecenie",
        "station": "CNC",
        "order_code": "ZAM-101",
        "worker_name": "Marek CNC",
        "client_name": "Piotr Nowak",
        "location": "",
        "notes": "Kuchnia - 14 korpusow",
        "status": "planned",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Montaz kuchni Zielinska",
        "date": "2026-05-07",
        "date_end": "2026-05-08",
        "all_day": 1,
        "event_type": "montaz",
        "station": "Skladanie",
        "order_code": "ZAM-097",
        "worker_name": "Tomek Montaz",
        "client_name": "Katarzyna Zielinska",
        "location": "ul. Parkowa 5, Krakow",
        "notes": "Po lakierowaniu, sprawdzic kolor na miejscu",
        "status": "planned",
    },
]

for ev in events:
    conn.execute(
        """INSERT INTO calendar_events
           (id, title, date, date_end, all_day, event_type, station, order_code,
            worker_name, client_name, location, notes, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            ev["id"], ev["title"], ev["date"], ev["date_end"], ev["all_day"],
            ev["event_type"], ev["station"], ev["order_code"], ev["worker_name"],
            ev["client_name"], ev["location"], ev["notes"], ev["status"], now,
        ),
    )

conn.commit()

cursor = conn.execute("SELECT COUNT(*) FROM calendar_events")
total = cursor.fetchone()[0]
print(f"Dodano {len(events)} zdarzen. Lacznie w bazie: {total}")

cursor2 = conn.execute(
    "SELECT date, title, event_type, worker_name, status FROM calendar_events ORDER BY date"
)
for row in cursor2:
    print(f"  {row[0]} | {row[1][:40]:<40} | {row[2]:<16} | {row[3]:<15} | {row[4]}")

conn.close()
