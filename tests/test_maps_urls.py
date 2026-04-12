from src.core.maps_urls import build_google_maps_directions_url, build_google_maps_search_url


def test_build_search_url_encodes_address():
    url = build_google_maps_search_url("Krakow ul. Karmelicka 10/2")
    assert "google.com/maps/search" in url
    assert "Krakow%20ul.%20Karmelicka%2010%2F2" in url


def test_build_directions_url_keeps_waypoint_order():
    url = build_google_maps_directions_url(
        origin="A start",
        destination="D end",
        waypoints=["B mid", "C mid"],
        travelmode="driving",
    )
    assert "origin=A%20start" in url
    assert "destination=D%20end" in url
    assert "waypoints=B%20mid%7CC%20mid" in url
