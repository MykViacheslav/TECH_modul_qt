import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.storage.material_store_json import MaterialStoreJson
from src.storage.material_usage_store_json import MaterialUsageStoreJson

class MaterialAdvancedService:
    def __init__(self):
        self._store = MaterialStoreJson()
        self._usage_store = MaterialUsageStoreJson()

    def deduct_material(self, material_id: str, quantity: float, order_id: str, note: str = "") -> bool:
        """Subtract quantity from stock and log usage."""
        db = self._store.load()
        rows = db.get("rows", [])
        
        target_row = None
        for row in rows:
            if str(row.get("id", "")) == material_id:
                target_row = row
                break
        
        if not target_row:
            return False
            
        try:
            current_stock = float(target_row.get("ilosc_magazyn", 0.0) or 0.0)
            if current_stock < quantity:
                # Still deduct, but record might go negative or we handle it
                pass
            
            new_stock = current_stock - quantity
            target_row["ilosc_magazyn"] = f"{max(0.0, new_stock):.2f}"
            
            # Log usage
            self._usage_store.log_usage(material_id, quantity, order_id, note)
            
            self._store.save(db)
            return True
        except Exception:
            return False

    def compare_prices(self, material_name: str, new_price: float) -> dict[str, Any]:
        """Compare new purchase price with history for a specific material name."""
        rows = self._store.list_materials()
        history = [r for r in rows if r.get("nazwa", "").lower().strip() == material_name.lower().strip()]
        
        if not history:
            return {"status": "new", "diff": 0.0, "previous_avg": 0.0}
            
        prices = []
        for h in history:
            try:
                prices.append(float(h.get("cena_zl", 0.0) or 0.0))
            except: pass
            
        if not prices:
            return {"status": "new", "diff": 0.0, "previous_avg": 0.0}
            
        avg_price = sum(prices) / len(prices)
        last_price = prices[-1]
        
        diff = new_price - last_price
        diff_percent = (diff / last_price * 100) if last_price != 0 else 0
        
        status = "normal"
        if diff > 0.05 * last_price: status = "more_expensive"
        elif diff < -0.05 * last_price: status = "cheaper"
        
        return {
            "status": status,
            "diff": round(diff, 2),
            "diff_percent": round(diff_percent, 1),
            "last_price": last_price,
            "avg_price": round(avg_price, 2)
        }

    def get_to_buy_list(self, threshold: float = 1.0) -> List[Dict[str, Any]]:
        """List materials with stock level below threshold."""
        rows = self._store.list_materials()
        to_buy = []
        for r in rows:
            try:
                stock = float(r.get("ilosc_magazyn", 0.0) or 0.0)
                if stock <= threshold:
                    to_buy.append(r)
            except: pass
        return to_buy

    @staticmethod
    def get_warehouse_types() -> List[str]:
        return ["glowny", "plyty_fronty", "okucia_akcesoria"]

    @staticmethod
    def get_purchase_channels() -> List[str]:
        return ["Faktura", "Gotówka", "Paragon"]
