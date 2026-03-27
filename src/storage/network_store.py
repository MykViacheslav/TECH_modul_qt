"""
Network storage client for TECH_modul multi-computer setup.
Connects to a central HTTP server to read/write data.
"""

from __future__ import annotations

import json
from typing import Any, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

from src.storage.data_paths import data_dir


class NetworkConfig:
    """Configuration for network connection."""
    
    _instance: Optional['NetworkConfig'] = None
    
    def __new__(cls) -> 'NetworkConfig':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self._server_url: str = ""
        self._enabled: bool = False
        self._load_config()
    
    def _load_config(self) -> None:
        """Load network configuration from file."""
        config_path = data_dir() / "network_config.json"
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                self._server_url = config.get("server_url", "")
                self._enabled = config.get("enabled", False)
            except Exception:
                pass
    
    def save_config(self) -> None:
        """Save network configuration to file."""
        config_path = data_dir() / "network_config.json"
        config = {
            "server_url": self._server_url,
            "enabled": self._enabled,
        }
        try:
            config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    
    @property
    def server_url(self) -> str:
        return self._server_url
    
    @server_url.setter
    def server_url(self, value: str) -> None:
        self._server_url = value.rstrip("/")
        self.save_config()
    
    @property
    def enabled(self) -> bool:
        return self._enabled and bool(self._server_url)
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        self.save_config()
    
    def test_connection(self) -> tuple[bool, str]:
        """Test connection to server."""
        if not self._server_url:
            return False, "No server URL configured"
        
        try:
            response = urlopen(f"{self._server_url}/api/health", timeout=5)
            data = json.loads(response.read())
            return True, f"Connected! Status: {data.get('status', 'ok')}"
        except HTTPError as e:
            return False, f"HTTP Error: {e.code}"
        except URLError as e:
            return False, f"Connection failed: {e.reason}"
        except Exception as e:
            return False, f"Error: {e}"


class NetworkStore:
    """
    Network-backed data store that communicates with central server.
    Falls back to local storage if network is unavailable.
    """
    
    def __init__(self, store_name: str):
        self._store_name = store_name
        self._config = NetworkConfig()
        self._local_cache: dict[str, Any] = {}
    
    def _api_url(self, endpoint: str = "") -> str:
        """Build API URL."""
        base = self._config.server_url
        return f"{base}/api/{self._store_name}/{endpoint}".rstrip("/")
    
    def _make_request(self, method: str, url: str, data: Optional[dict] = None) -> Optional[dict]:
        """Make HTTP request to server."""
        try:
            headers = {"Content-Type": "application/json; charset=utf-8"}
            body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
            
            request = Request(url, data=body, headers=headers, method=method)
            response = urlopen(request, timeout=10)
            return json.loads(response.read())
        except HTTPError as e:
            print(f"HTTP Error {e.code}: {e.reason}")
            return None
        except URLError as e:
            print(f"Connection error: {e.reason}")
            return None
        except Exception as e:
            print(f"Request error: {e}")
            return None
    
    def list_items(self) -> list[dict]:
        """List all items from store."""
        if not self._config.enabled:
            return []
        
        result = self._make_request("GET", self._api_url())
        if result and "data" in result:
            return result["data"]
        return []
    
    def get_item(self, item_id: str) -> Optional[dict]:
        """Get specific item by ID."""
        if not self._config.enabled:
            return None
        
        result = self._make_request("GET", self._api_url(item_id))
        if result and "data" in result:
            return result["data"]
        return None
    
    def save_item(self, item: dict) -> bool:
        """Create or update item."""
        if not self._config.enabled:
            return False
        
        result = self._make_request("POST", self._api_url(), {"data": item})
        return result is not None and result.get("ok", False)
    
    def delete_item(self, item_id: str) -> bool:
        """Delete item by ID."""
        if not self._config.enabled:
            return False
        
        result = self._make_request("DELETE", self._api_url(item_id))
        return result is not None and result.get("ok", False)
    
    def is_available(self) -> bool:
        """Check if network storage is available."""
        if not self._config.enabled:
            return False
        success, _ = self._config.test_connection()
        return success


class HybridStore:
    """
    Storage that uses network when available, falls back to local JSON.
    Implements sync between local and network storage.
    """
    
    def __init__(self, store_name: str):
        self._store_name = store_name
        self._network = NetworkStore(store_name)
        self._local_file = data_dir() / f"{store_name}.json"
    
    def _load_local(self) -> list[dict]:
        """Load data from local file."""
        if not self._local_file.exists():
            return []
        try:
            data = json.loads(self._local_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                # Try common keys
                for key in ["items", "rows", "data", "orders", "alarms", "workers", "clients"]:
                    if key in data and isinstance(data[key], list):
                        return data[key]
            return []
        except Exception:
            return []
    
    def _save_local(self, items: list[dict]) -> None:
        """Save data to local file."""
        self._local_file.parent.mkdir(parents=True, exist_ok=True)
        self._local_file.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    def list_items(self) -> list[dict]:
        """List all items (network or local)."""
        if self._network.is_available():
            return self._network.list_items()
        return self._load_local()
    
    def get_item(self, item_id: str) -> Optional[dict]:
        """Get item (network or local)."""
        if self._network.is_available():
            return self._network.get_item(item_id)
        
        # Fallback to local
        for item in self._load_local():
            item_id_field = item.get("id") or item.get("code") or item.get("order_id") or item.get("worker_id") or item.get("name") or item.get("alarm_id")
            if str(item_id_field) == str(item_id):
                return item
        return None
    
    def save_item(self, item: dict) -> bool:
        """Save item (network and local)."""
        # Always save locally first
        items = self._load_local()
        item_id = item.get("id") or item.get("code") or item.get("order_id") or item.get("worker_id") or item.get("name") or item.get("alarm_id")
        
        found = False
        for i, existing in enumerate(items):
            existing_id = existing.get("id") or existing.get("code") or existing.get("order_id") or existing.get("worker_id") or existing.get("name") or existing.get("alarm_id")
            if str(existing_id) == str(item_id):
                items[i] = item
                found = True
                break
        
        if not found:
            items.append(item)
        
        self._save_local(items)
        
        # Also save to network if available
        if self._network.is_available():
            self._network.save_item(item)
        
        return True
    
    def sync_to_network(self) -> int:
        """Sync local changes to network. Returns count of synced items."""
        if not self._network.is_available():
            return 0
        
        count = 0
        for item in self._load_local():
            if self._network.save_item(item):
                count += 1
        return count
    
    def sync_from_network(self) -> int:
        """Download data from network to local. Returns count of synced items."""
        if not self._network.is_available():
            return 0
        
        items = self._network.list_items()
        if items:
            self._save_local(items)
            return len(items)
        return 0
