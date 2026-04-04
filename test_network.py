"""
Test lokalny serwera i klienta TECH_modul.
Uruchom ten skrypt aby przetestować czy sieć działa.
"""

import json
import os
import sys
import threading
import time
from urllib.request import urlopen, Request
from urllib.error import URLError

# Setup environment
os.environ['TECH_MODUL_DATA_DIR'] = 'data'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.server.data_server import DataServer


def test_health_check(port: int = 8000) -> bool:
    """Test if server is responding."""
    try:
        response = urlopen(f"http://127.0.0.1:{port}/api/health", timeout=5)
        data = json.loads(response.read())
        print(f"[OK] Health check: {data}")
        return True
    except Exception as e:
        print(f"[FAIL] Health check failed: {e}")
        return False


def test_list_stores(port: int = 8000) -> bool:
    """Test listing data stores."""
    try:
        response = urlopen(f"http://127.0.0.1:{port}/api/", timeout=5)
        data = json.loads(response.read())
        print(f"[OK] Stores: {data.get('stores', [])}")
        return True
    except Exception as e:
        print(f"[FAIL] List stores failed: {e}")
        return False


def test_create_and_read(port: int = 8000) -> bool:
    """Test creating and reading data."""
    store_name = "test_store"
    test_data = {"id": "test_1", "name": "Test Item", "value": 42}
    
    try:
        # Create
        url = f"http://127.0.0.1:{port}/api/{store_name}"
        data = json.dumps({"data": test_data}).encode("utf-8")
        request = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        response = urlopen(request, timeout=5)
        result = json.loads(response.read())
        print(f"[OK] Create: {result}")
        
        # Read
        response = urlopen(f"http://127.0.0.1:{port}/api/{store_name}/test_1", timeout=5)
        result = json.loads(response.read())
        print(f"[OK] Read: {result}")
        
        return True
    except Exception as e:
        print(f"[FAIL] Create/Read failed: {e}")
        return False


def main():
    print("=" * 50)
    print("TEST LOKALNY SERWERA TECH_modul")
    print("=" * 50)
    print()
    
    # Start server in background
    print("1. Uruchamianie serwera na localhost:8000...")
    server = DataServer(host="127.0.0.1", port=8000)
    server.start(background=True)
    time.sleep(1)  # Wait for server to start
    print()
    
    # Run tests
    print("2. Testowanie endpointów...")
    print()
    
    success = True
    success &= test_health_check()
    success &= test_list_stores()
    success &= test_create_and_read()
    
    print()
    print("=" * 50)
    if success:
        print("[OK] WSZYSTKIE TESTY PRZESZLY!")
        print()
        print("Teraz mozesz:")
        print("1. Odrebny terminal: python src/app/main.py")
        print("2. Ustawienia -> Siec -> http://127.0.0.1:8000")
        print("3. Test polaczenia OK")
    else:
        print("[FAIL] NIEKTORE TESTY NIE PRZESZLY")
    print("=" * 50)
    
    # Stop server
    print()
    input("Naciśnij Enter aby zatrzymać serwer...")
    server.stop()


if __name__ == "__main__":
    main()
