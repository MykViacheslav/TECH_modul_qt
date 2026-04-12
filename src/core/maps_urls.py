from __future__ import annotations

from urllib.parse import quote
import webbrowser


def build_google_maps_search_url(address: str) -> str:
    q = quote(str(address or "").strip(), safe="")
    return f"https://www.google.com/maps/search/?api=1&query={q}"


def build_google_maps_directions_url(
    origin: str,
    destination: str,
    waypoints: list[str] | None = None,
    travelmode: str = "driving",
) -> str:
    origin_q = quote(str(origin or "").strip(), safe="")
    destination_q = quote(str(destination or "").strip(), safe="")
    mode_q = quote(str(travelmode or "driving").strip(), safe="")
    url = f"https://www.google.com/maps/dir/?api=1&origin={origin_q}&destination={destination_q}&travelmode={mode_q}"
    if waypoints:
        ordered = [str(x or "").strip() for x in waypoints if str(x or "").strip()]
        if ordered:
            wp_text = "|".join(ordered)
            url += f"&waypoints={quote(wp_text, safe='')}"
    return url


def open_url(url: str) -> None:
    text = str(url or "").strip()
    if not text:
        return
    try:
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices

        if QDesktopServices.openUrl(QUrl(text)):
            return
    except Exception:
        pass
    webbrowser.open(text)
