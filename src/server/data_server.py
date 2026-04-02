"""
Simple HTTP server for TECH_modul multi-computer setup.
Runs on the "server" computer, serves JSON data via REST API.
Uses only Python built-in modules (no external dependencies).
"""

from __future__ import annotations

import json
import os
import threading
import ssl
from functools import lru_cache
from io import BytesIO
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs

from PIL import Image, ImageDraw, ImageFont

from src.server.kiosk_page import build_kiosk_html
from src.server.package_scanner_page import build_package_scanner_html
from src.server.measure_mobile_page import build_measure_mobile_html
from src.server.stanowisko_page import build_stanowisko_html
from src.server.kiosk_service import KioskService
from src.domain.package_qr import parse_package_qr_payload
from src.storage.data_paths import data_dir


def _load_icon_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except Exception:
        return ImageFont.load_default()


@lru_cache(maxsize=8)
def _build_kiosk_icon(size: int) -> bytes:
    size = max(int(size), 64)
    img = Image.new("RGBA", (size, size), (16, 22, 35, 255))
    draw = ImageDraw.Draw(img)

    border = max(3, size // 64)
    radius = int(size * 0.18)
    outer = (border, border, size - border, size - border)
    inner = (int(size * 0.12), int(size * 0.12), int(size * 0.88), int(size * 0.88))

    draw.rounded_rectangle(outer, radius=radius, fill=(21, 31, 49, 255), outline=(110, 231, 255, 220), width=border)
    draw.rounded_rectangle(inner, radius=int(size * 0.14), fill=(14, 20, 34, 255), outline=(124, 156, 255, 200), width=max(2, border - 1))

    accent = (110, 231, 255, 255)
    good = (47, 209, 140, 255)
    white = (243, 247, 255, 255)

    block = int(size * 0.11)
    gap = int(size * 0.045)
    x0 = int(size * 0.2)
    y0 = int(size * 0.2)
    coords = [
        (x0, y0),
        (x0 + block + gap, y0),
        (x0, y0 + block + gap),
    ]
    for idx, (x, y) in enumerate(coords):
        color = accent if idx != 1 else good
        draw.rounded_rectangle((x, y, x + block, y + block), radius=max(4, block // 5), fill=color)

    qr_size = int(size * 0.26)
    qr_x = int(size * 0.58)
    qr_y = int(size * 0.24)
    draw.rounded_rectangle((qr_x, qr_y, qr_x + qr_size, qr_y + qr_size), radius=max(6, qr_size // 7), fill=(255, 255, 255, 255))
    draw.rounded_rectangle((qr_x + qr_size * 0.2, qr_y + qr_size * 0.2, qr_x + qr_size * 0.8, qr_y + qr_size * 0.8), radius=max(4, qr_size // 10), fill=(16, 22, 35, 255))

    text = "TM"
    font = _load_icon_font(int(size * 0.26))
    bbox = draw.textbbox((0, 0), text, font=font)
    tx = (size - (bbox[2] - bbox[0])) / 2
    ty = size * 0.52
    draw.text((tx, ty), text, fill=white, font=font)

    bar_y = int(size * 0.79)
    draw.rounded_rectangle((int(size * 0.18), bar_y, int(size * 0.82), bar_y + max(6, size // 34)), radius=max(3, size // 40), fill=(110, 231, 255, 200))

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _build_kiosk_manifest() -> dict[str, Any]:
    return {
        "name": "TECH_modul Kiosk",
        "short_name": "TECH Kiosk",
        "start_url": "/kiosk-lite",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#101623",
        "theme_color": "#101623",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }


def _build_time_kiosk_manifest() -> dict[str, Any]:
    return {
        "name": "TECH_modul Czas Pracy",
        "short_name": "Czas Pracy",
        "start_url": "/kiosk-time?app=1",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#101623",
        "theme_color": "#101623",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }


def _build_pack_scanner_manifest() -> dict[str, Any]:
    return {
        "name": "TECH_modul Pack Scanner",
        "short_name": "Pack Scanner",
        "start_url": "/pack-scanner?app=1",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#0f172a",
        "theme_color": "#0f172a",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }


def _build_measure_mobile_manifest() -> dict[str, Any]:
    return {
        "name": "TECH_modul Pomiary Mobile",
        "short_name": "Pomiary",
        "start_url": "/measure-mobile?app=1",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#10233a",
        "theme_color": "#10233a",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }


def _build_service_worker() -> bytes:
    script = """
self.addEventListener('install', event => {
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  event.respondWith(fetch(event.request));
});
"""
    return script.strip().encode("utf-8")


class DataStoreHandler(BaseHTTPRequestHandler):
    """HTTP request handler for data operations."""
    
    # Reference to data directory (set by server)
    data_dir: Path = data_dir()
    kiosk_service: Optional[KioskService] = None
    
    def log_message(self, format: str, *args) -> None:
        """Override to reduce log noise."""
        pass # Comment out for debugging: super().log_message(format, *args)
    
    def _send_json(self, data: Any, status: int = 200) -> None:
        """Send JSON response."""
        response = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response)
    
    def _send_error(self, message: str, status: int = 400) -> None:
        """Send error response."""
        self._send_json({"error": message}, status)

    def _send_html(self, html: str, status: int = 200) -> None:
        response = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response)

    def _send_binary(self, data: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)
    
    def _read_json_body(self) -> Optional[dict]:
        """Read JSON from request body."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                return None
            body = self.rfile.read(content_length)
            return json.loads(body.decode("utf-8"))
        except Exception as e:
            self._send_error(f"Invalid JSON body: {e}")
            return None
    
    def _get_file_path(self, store_name: str) -> Path:
        """Get path to data file."""
        # Sanitize store_name to prevent directory traversal
        safe_name = "".join(c for c in store_name if c.isalnum() or c in "-_.")
        return self.data_dir / f"{safe_name}.json"

    def _get_kiosk_service(self) -> KioskService:
        service = type(self).kiosk_service
        if service is None:
            raise RuntimeError("Kiosk service is not configured.")
        return service
    
    def do_GET(self) -> None:
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path_parts = [part for part in parsed.path.strip("/").split("/") if part]
        first = path_parts[0] if path_parts else ""

        # GET /manifest.webmanifest - PWA manifest for Android home screen icon
        if parsed.path.rstrip("/") == "/manifest.webmanifest":
            manifest = json.dumps(_build_kiosk_manifest(), ensure_ascii=False).encode("utf-8")
            self._send_binary(manifest, "application/manifest+json; charset=utf-8")
            return

        # GET /manifest-time.webmanifest - dedicated manifest for time clock reader
        if parsed.path.rstrip("/") in {"/manifest-time.webmanifest", "/time-kiosk.webmanifest"}:
            manifest = json.dumps(_build_time_kiosk_manifest(), ensure_ascii=False).encode("utf-8")
            self._send_binary(manifest, "application/manifest+json; charset=utf-8")
            return

        # GET /pack-scanner.webmanifest - PWA manifest for package scanner app icon
        if parsed.path.rstrip("/") in {"/pack-scanner.webmanifest", "/manifest-pack.webmanifest"}:
            manifest = json.dumps(_build_pack_scanner_manifest(), ensure_ascii=False).encode("utf-8")
            self._send_binary(manifest, "application/manifest+json; charset=utf-8")
            return

        # GET /measure-mobile.webmanifest - PWA manifest for measurements mobile view
        if parsed.path.rstrip("/") in {"/measure-mobile.webmanifest", "/manifest-measure.webmanifest"}:
            manifest = json.dumps(_build_measure_mobile_manifest(), ensure_ascii=False).encode("utf-8")
            self._send_binary(manifest, "application/manifest+json; charset=utf-8")
            return

        # GET /sw.js - very small service worker so Android can install the kiosk
        if parsed.path.rstrip("/") == "/sw.js":
            self._send_binary(_build_service_worker(), "application/javascript; charset=utf-8")
            return

        # GET app icons
        if parsed.path.rstrip("/") in {"/icon-180.png", "/apple-touch-icon.png", "/icon-192.png", "/icon-512.png"}:
            size = 192
            if parsed.path.rstrip("/") in {"/icon-180.png", "/apple-touch-icon.png"}:
                size = 180
            elif parsed.path.rstrip("/") == "/icon-512.png":
                size = 512
            self._send_binary(_build_kiosk_icon(size), "image/png")
            return

        # GET /ca.crt - CA cert download for Android/iOS HTTPS trust setup
        if parsed.path.rstrip("/") in {"/ca.crt", "/tech-modul-ca.crt"}:
            ca_file = data_dir() / "https" / "TECH_modul_CA.crt"
            if not ca_file.exists():
                self._send_error("CA certificate not found. Start HTTPS first.", 404)
                return
            self._send_binary(ca_file.read_bytes(), "application/x-x509-ca-cert")
            return

        # GET /kiosk or /kiosk-lite - web kiosk for Android tablets
        if parsed.path.rstrip("/") in {"/kiosk", "/kiosk-lite"}:
            lite_mode = parsed.path.rstrip("/") == "/kiosk-lite"
            query = parse_qs(parsed.query or "")
            if str((query.get("mode") or [""])[0]).strip().lower() == "lite":
                lite_mode = True
            self._send_html(build_kiosk_html(lite=lite_mode))
            return

        # GET /kiosk-time - dedicated time reader URL for home-screen icon
        if parsed.path.rstrip("/") in {"/kiosk-time", "/czas-pracy", "/czytnik-godzin"}:
            self._send_html(build_kiosk_html(lite=True))
            return

        # GET /pack-scanner - lightweight package QR scanner (no ads)
        if parsed.path.rstrip("/") in {"/pack-scanner", "/scanner", "/pack-scan", "/scanner-mobile"}:
            self._send_html(build_package_scanner_html())
            return

        # GET /measure-mobile - lightweight phone view for wall measurements
        if parsed.path.rstrip("/") in {"/measure-mobile", "/pomiary-mobile", "/measurement-mobile"}:
            self._send_html(build_measure_mobile_html())
            return

        # GET /stanowisko?id=cnc - wall display for a production station
        if parsed.path.rstrip("/") in {"/stanowisko", "/station", "/stanowiska"}:
            query = parse_qs(parsed.query or "")
            station_id = str((query.get("id") or query.get("station") or [""])[0]).strip().lower()
            self._send_html(build_stanowisko_html(station_id))
            return

        # GET /api/health - health check
        if first == "api" and len(path_parts) == 2 and path_parts[1] == "health":
            self._send_json({"status": "ok", "timestamp": datetime.now().isoformat()})
            return

        # GET /api/kiosk/workers - list workers for the kiosk
        if first == "api" and len(path_parts) == 3 and path_parts[1] == "kiosk" and path_parts[2] == "workers":
            self._handle_kiosk_workers()
            return

        # GET /api/kiosk/stateEmailworker_id=... - current kiosk state for a worker
        if first == "api" and len(path_parts) == 3 and path_parts[1] == "kiosk" and path_parts[2] == "state":
            self._handle_kiosk_state(parsed)
            return
        
        # GET /api/stores - list all available stores
        if first == "api" and len(path_parts) == 1:
            self._handle_list_stores()
            return
        
        # GET /api/{store} - get all data from store
        if first == "api" and len(path_parts) == 2:
            store_name = path_parts[1]
            self._handle_get_store(store_name)
            return
        
        # GET /api/{store}/{id} - get specific item
        if first == "api" and len(path_parts) == 3:
            store_name = path_parts[1]
            item_id = path_parts[2]
            self._handle_get_item(store_name, item_id)
            return
        
        self._send_error("Not found", 404)
    
    def do_POST(self) -> None:
        """Handle POST requests (create/update)."""
        parsed = urlparse(self.path)
        path_parts = [part for part in parsed.path.strip("/").split("/") if part]
        first = path_parts[0] if path_parts else ""

        # POST /api/kiosk/scan - resolve QR scan text
        if first == "api" and len(path_parts) == 3 and path_parts[1] == "kiosk" and path_parts[2] == "scan":
            self._handle_kiosk_scan()
            return

        # POST /api/kiosk/action - perform a kiosk action
        if first == "api" and len(path_parts) == 3 and path_parts[1] == "kiosk" and path_parts[2] == "action":
            self._handle_kiosk_action()
            return

        # POST /api/pack/parse - parse TECH_PACK payload
        if first == "api" and len(path_parts) == 3 and path_parts[1] == "pack" and path_parts[2] == "parse":
            self._handle_pack_parse()
            return
        
        # POST /api/{store} - create or update item
        if first == "api" and len(path_parts) == 2:
            store_name = path_parts[1]
            self._handle_post_store(store_name)
            return
        
        self._send_error("Not found", 404)
    
    def do_PUT(self) -> None:
        """Handle PUT requests (update)."""
        parsed = urlparse(self.path)
        path_parts = [part for part in parsed.path.strip("/").split("/") if part]
        first = path_parts[0] if path_parts else ""
        
        # PUT /api/{store}/{id} - update specific item
        if first == "api" and len(path_parts) == 3:
            store_name = path_parts[1]
            item_id = path_parts[2]
            self._handle_put_item(store_name, item_id)
            return
        
        self._send_error("Not found", 404)
    
    def do_DELETE(self) -> None:
        """Handle DELETE requests."""
        parsed = urlparse(self.path)
        path_parts = [part for part in parsed.path.strip("/").split("/") if part]
        first = path_parts[0] if path_parts else ""
        
        # DELETE /api/{store}/{id} - delete specific item
        if first == "api" and len(path_parts) == 3:
            store_name = path_parts[1]
            item_id = path_parts[2]
            self._handle_delete_item(store_name, item_id)
            return
        
        self._send_error("Not found", 404)
    
    def do_OPTIONS(self) -> None:
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    # --- Handler implementations ---
    
    def _handle_list_stores(self) -> None:
        """List all available data stores."""
        stores = []
        for f in self.data_dir.glob("*.json"):
            stores.append(f.stem)
        self._send_json({"stores": sorted(stores)})
    
    def _handle_get_store(self, store_name: str) -> None:
        """Get all data from a store."""
        file_path = self._get_file_path(store_name)
        if not file_path.exists():
            self._send_json({"data": []})
            return
        
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            # Handle both list format and dict format
            if isinstance(data, list):
                self._send_json({"data": data})
            elif isinstance(data, dict):
                # Try to find the main data key
                for key in ["items", "rows", "data", "orders", "alarms", "workers", "clients"]:
                    if key in data:
                        self._send_json({"data": data[key]})
                        return
                self._send_json({"data": data})
            else:
                self._send_json({"data": []})
        except Exception as e:
            self._send_error(f"Failed to read store: {e}", 500)
    
    def _handle_get_item(self, store_name: str, item_id: str) -> None:
        """Get specific item from store."""
        file_path = self._get_file_path(store_name)
        if not file_path.exists():
            self._send_error("Store not found", 404)
            return
        
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("items"), dict):
                for key, item in data.get("items", {}).items():
                    if not isinstance(item, dict):
                        continue
                    item_id_field = (
                        item.get("id")
                        or item.get("code")
                        or item.get("order_id")
                        or item.get("worker_id")
                        or item.get("name")
                        or item.get("alarm_id")
                        or str(key)
                    )
                    if str(item_id_field) == str(item_id) or str(key) == str(item_id):
                        self._send_json({"data": item})
                        return
            items = self._extract_items(data, store_name)
            
            for item in items:
                # Check various ID fields
                item_id_field = item.get("id") or item.get("code") or item.get("order_id") or item.get("worker_id") or item.get("name") or item.get("alarm_id")
                if str(item_id_field) == str(item_id):
                    self._send_json({"data": item})
                    return
            
            self._send_error("Item not found", 404)
        except Exception as e:
            self._send_error(f"Failed to read item: {e}", 500)
    
    def _handle_post_store(self, store_name: str) -> None:
        """Create or update item in store."""
        body = self._read_json_body()
        if body is None:
            self._send_error("No data provided")
            return
        
        file_path = self._get_file_path(store_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Read existing data
            if file_path.exists():
                data = json.loads(file_path.read_text(encoding="utf-8"))
            else:
                data = []

            # Map-mode store: {"schema_version": N, "items": {"id": {...}}}
            if isinstance(data, dict) and isinstance(data.get("items"), dict):
                item = body.get("data", body)
                if not isinstance(item, dict):
                    self._send_error("Invalid item format", 400)
                    return
                item_id = (
                    item.get("id")
                    or item.get("code")
                    or item.get("order_id")
                    or item.get("worker_id")
                    or item.get("name")
                    or item.get("alarm_id")
                )
                item_id_str = str(item_id or "").strip()
                if not item_id_str:
                    self._send_error("Item id is required for map stores", 400)
                    return
                items_map = data.get("items", {})
                items_map[item_id_str] = item
                data["items"] = items_map
                if "schema_version" not in data:
                    data["schema_version"] = 2
                file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                self._send_json({"ok": True, "message": "Saved", "id": item_id_str})
                return
            
            # Ensure data is a list
            if isinstance(data, dict):
                # Try to find the main data key
                for key in ["items", "rows", "data", "orders", "alarms", "workers", "clients"]:
                    if key in data and isinstance(data[key], list):
                        data = data[key]
                        data_key = key
                        break
                else:
                    data = []
                    data_key = "data"
            else:
                data_key = None
            
            if not isinstance(data, list):
                data = []
            
            # Get item from body
            item = body.get("data", body)
            item_id = item.get("id") or item.get("code") or item.get("order_id") or item.get("worker_id") or item.get("name") or item.get("alarm_id")
            
            # Find and update or append
            found = False
            for i, existing in enumerate(data):
                existing_id = existing.get("id") or existing.get("code") or existing.get("order_id") or existing.get("worker_id") or existing.get("name") or existing.get("alarm_id")
                if str(existing_id) == str(item_id):
                    data[i] = item
                    found = True
                    break
            
            if not found:
                data.append(item)
            
            # Save back
            if data_key:
                save_data = {data_key: data}
            else:
                save_data = data
            
            file_path.write_text(json.dumps(save_data, ensure_ascii=False, indent=2), encoding="utf-8")
            
            self._send_json({"ok": True, "message": "Saved", "id": item_id})
        except Exception as e:
            self._send_error(f"Failed to save: {e}", 500)
    
    def _handle_put_item(self, store_name: str, item_id: str) -> None:
        """Update specific item."""
        body = self._read_json_body()
        if body is None:
            return # Error already sent
        # Reuse POST handler
        self._handle_post_store(store_name)
    
    def _handle_delete_item(self, store_name: str, item_id: str) -> None:
        """Delete specific item from store."""
        file_path = self._get_file_path(store_name)
        if not file_path.exists():
            self._send_error("Store not found", 404)
            return
        
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("items"), dict):
                items_map = data.get("items", {})
                removed = items_map.pop(str(item_id), None)
                if removed is None:
                    # Fallback: remove by inner id fields
                    to_delete = None
                    for key, item in items_map.items():
                        if not isinstance(item, dict):
                            continue
                        item_id_field = item.get("id") or item.get("code") or item.get("order_id") or item.get("worker_id") or item.get("name") or item.get("alarm_id")
                        if str(item_id_field) == str(item_id):
                            to_delete = key
                            break
                    if to_delete is not None:
                        items_map.pop(to_delete, None)
                data["items"] = items_map
                file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                self._send_json({"ok": True, "message": "Deleted"})
                return
            items = self._extract_items(data, store_name)
            
            new_items = []
            for item in items:
                item_id_field = item.get("id") or item.get("code") or item.get("order_id") or item.get("worker_id") or item.get("name") or item.get("alarm_id")
                if str(item_id_field) != str(item_id):
                    new_items.append(item)
            
            file_path.write_text(json.dumps(new_items, ensure_ascii=False, indent=2), encoding="utf-8")
            
            self._send_json({"ok": True, "message": "Deleted"})
        except Exception as e:
            self._send_error(f"Failed to delete: {e}", 500)
    
    def _extract_items(self, data: Any, store_name: str) -> list:
        """Extract items list from various data formats."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ["items", "rows", "data", "orders", "alarms", "workers", "clients"]:
                if key in data and isinstance(data[key], list):
                    return data[key]
                if key in data and isinstance(data[key], dict):
                    return [item for item in data[key].values() if isinstance(item, dict)]
        return []

    def _handle_kiosk_workers(self) -> None:
        service = self._get_kiosk_service()
        self._send_json({"ok": True, "workers": service.list_workers()})

    def _handle_kiosk_state(self, parsed) -> None:
        service = self._get_kiosk_service()
        query = parse_qs(parsed.query or "")
        worker_id = str((query.get("worker_id") or [""])[0] or "").strip()
        if not worker_id:
            self._send_error("worker_id is required", 400)
            return
        result = service.get_state(worker_id)
        self._send_json(result.to_dict(), 200 if result.ok else 404)

    def _handle_kiosk_scan(self) -> None:
        service = self._get_kiosk_service()
        body = self._read_json_body()
        if body is None:
            self._send_error("No data provided")
            return
        qr_text = str(body.get("qr_text") or body.get("text") or body.get("scan") or "").strip()
        if not qr_text:
            self._send_error("qr_text is required", 400)
            return
        result = service.resolve_scan(qr_text)
        self._send_json(result.to_dict(), 200 if result.ok else 404)

    def _handle_kiosk_action(self) -> None:
        service = self._get_kiosk_service()
        body = self._read_json_body()
        if body is None:
            self._send_error("No data provided")
            return
        worker_id = str(body.get("worker_id") or body.get("workerId") or "").strip()
        action = str(body.get("action") or "").strip()
        work_type = str(body.get("work_type") or body.get("workType") or "").strip()
        if not worker_id:
            self._send_error("worker_id is required", 400)
            return
        if not action:
            self._send_error("action is required", 400)
            return
        result = service.perform_action(worker_id, action, work_type=work_type)
        self._send_json(result.to_dict(), 200 if result.ok else 400)

    def _handle_pack_parse(self) -> None:
        body = self._read_json_body()
        if body is None:
            self._send_error("No data provided")
            return
        qr_text = str(body.get("qr_text") or body.get("text") or body.get("scan") or "").strip()
        if not qr_text:
            self._send_error("qr_text is required", 400)
            return
        parsed = parse_package_qr_payload(qr_text)
        if parsed is None:
            self._send_json({"ok": False, "message": "Not a TECH_PACK payload"}, 400)
            return
        self._send_json({"ok": True, "message": "OK", "data": parsed.to_dict()}, 200)


class DataServer:
    """
    HTTP server for TECH_modul data.
    Run this on the "server" computer.
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8000, kiosk_service: KioskService | None = None):
        self.host = host
        self.port = port
        self.kiosk_service = kiosk_service
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
    
    def start(self, background: bool = True, ssl_context: ssl.SSLContext | None = None, scheme: str = "http") -> None:
        """Start the server."""
        handler = DataStoreHandler
        handler.data_dir = data_dir()
        handler.kiosk_service = self.kiosk_service if self.kiosk_service is not None else KioskService()

        self._server = HTTPServer((self.host, self.port), handler)
        if ssl_context is not None:
            self._server.socket = ssl_context.wrap_socket(self._server.socket, server_side=True)
        self._running = True

        actual_port = self._server.server_port if self._server is not None else self.port
        print(f"TECH_modul Server started on {scheme}://{self.host}:{actual_port}")
        print(f"Data directory: {data_dir()}")
        
        if background:
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
        else:
            self._server.serve_forever()
    
    def stop(self) -> None:
        """Stop the server."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._running = False
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)
            print("Server stopped.")
    
    @property
    def is_running(self) -> bool:
        return self._running


def start_server(host: str = "0.0.0.0", port: int = 8000, ssl_context: ssl.SSLContext | None = None, scheme: str = "http") -> DataServer:
    """Convenience function to start server."""
    server = DataServer(host, port)
    server.start(background=True, ssl_context=ssl_context, scheme=scheme)
    return server
