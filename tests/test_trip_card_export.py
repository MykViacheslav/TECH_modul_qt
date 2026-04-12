from src.core.orders_map_service import MapOrderPoint
from src.core.trip_card_export import build_trip_card_rows, export_trip_card_to_csv, export_trip_card_to_html


def test_build_trip_card_rows_columns():
    pts = [
        MapOrderPoint(
            id="route::1",
            project_name="Projekt 1",
            client_name="Klient 1",
            contact_name="Jan",
            contact_phone="123",
            city="Krakow",
            full_address="ul. A 1",
            visit_type="montaz",
            visit_status="planowane",
            work_scope="Zakres",
            items_to_take="Wkretarka",
            crew_notes="Uwaga",
            trip_order=2,
        )
    ]
    rows = build_trip_card_rows(pts)
    assert len(rows) == 1
    assert "project_name" in rows[0]
    assert "trip_order" in rows[0]


def test_trip_card_csv_html_export(tmp_path):
    pts = [MapOrderPoint(id="route::1", project_name="Projekt 1", client_name="Klient 1", full_address="ul. A 1", trip_order=1)]
    csv_path = tmp_path / "trip.csv"
    html_path = tmp_path / "trip.html"
    export_trip_card_to_csv(pts, str(csv_path), trip_meta={"crew": "Ekipa A"})
    export_trip_card_to_html(pts, str(html_path), trip_meta={"crew": "Ekipa A", "date": "2026-04-11"})
    assert csv_path.exists()
    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "Karta wyjazdu" in html
    assert "Projekt 1" in html
