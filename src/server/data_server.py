"""
Simple HTTP server for TECH_modul multi-computer setup.
Runs on the "server" computer, serves JSON data via REST API.
Uses only Python built-in modules (no external dependencies).
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs

from src.server.kiosk_page import build_kiosk_html
from src.server.kiosk_service import KioskService
from src.storage.data_paths import data_dir


class DataStoreHandler(BaseHTTPRequestHandler):
    """HTTP request handler for data operations."""
    
    # Reference to data directory (set by server)
    data_dir: Path = data_dir()
    kiosk_service: Optional[KioskService] = None
    
    def log_message(self, format: str, *args) -> None:
        """Override to reduce log noise."""
        pass  # Comment out for debugging: super().log_message(format, *args)
    
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

        # GET /kiosk - web kiosk for Android tablets
        if parsed.path.rstrip("/") == "/kiosk":
            self._send_html(build_kiosk_html())
            return

        # GET /api/health - health check
        if first == "api" and len(path_parts) == 2 and path_parts[1] == "health":
            self._send_json({"status": "ok", "timestamp": datetime.now().isoformat()})
            return

        # GET /api/kiosk/workers - list workers for the kiosk
        if first == "api" and len(path_parts) == 3 and path_parts[1] == "kiosk" and path_parts[2] == "workers":
            self._handle_kiosk_workers()
            return

        # GET /api/kiosk/state?worker_id=... - current kiosk state for a worker
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
            return  # Error already sent
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
    
    def start(self, background: bool = True) -> None:
        """Start the server."""
        handler = DataStoreHandler
        handler.data_dir = data_dir()
        handler.kiosk_service = self.kiosk_service if self.kiosk_service is not None else KioskService()
        
        self._server = HTTPServer((self.host, self.port), handler)
        self._running = True
        
        actual_port = self._server.server_port if self._server is not None else self.port
        print(f"TECH_modul Server started on http://{self.host}:{actual_port}")
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


def start_server(host: str = "0.0.0.0", port: int = 8000) -> DataServer:
    """Convenience function to start server."""
    server = DataServer(host, port)
    server.start(background=True)
    return server
