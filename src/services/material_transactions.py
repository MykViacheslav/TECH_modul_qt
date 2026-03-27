"""
Material transaction engine for TECH_modul.
Tracks all material movements: Reserve → Take (spisanie) → Purchase → Receive (przyjęcie).
Each operation is a transaction with history (who, when, what).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from src.storage.data_paths import data_dir


# === Transaction types ===
TRANSACTION_TYPES = {
    "RESERVE": "rezerwacja",      # Zarezerwuj materiał dla zamówienia
    "TAKE": "pobranie",           # Spisz materiał z magazynu (użyj)
    "PURCHASE": "zakup",          # Utwórz zamówienie zakupu
    "RECEIVE": "przyjecie",       # Przyjmij materiał na magazyn
    "RETURN": "zwrot",            # Zwrot niewykorzystanego materiału
    "ADJUST": "korekta",          # Korekta stanu magazynowego
    "CORRECTION": "korekta_ręczna",  # Ręczna korekta przez administratora
}

TRANSACTION_STATUSES = {
    "PENDING": "oczekuje",        # Utworzony, czeka na akceptację
    "COMPLETED": "zakończony",    # Zrealizowany
    "CANCELLED": "anulowany",     # Anulowany
    "REJECTED": "odrzucony",      # Odrzucony
}


@dataclass
class MaterialTransaction:
    """Single material transaction record."""
    
    id: str = field(default_factory=lambda: str(uuid4())[:12])
    transaction_type: str = ""    # RESERVE, TAKE, PURCHASE, RECEIVE, RETURN, ADJUST
    material_id: str = ""         # ID materiału w bazie
    material_name: str = ""       # Nazwa materiału
    quantity: float = 0.0         # Ilość (+ dodatnia, - ujemna)
    unit: str = "szt"             # Jednostka: szt, mb, m2, kg, etc.
    
    # Context
    order_code: str = ""          # Powiązane zamówienie (opcjonalnie)
    worker_name: str = ""         # Kto wykonał
    notes: str = ""               # Notatki/opis
    
    # Status
    status: str = "oczekuje"      # oczekuje, zakończony, anulowany, odrzucony
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    completed_at: str = ""
    
    # For purchases
    supplier: str = ""
    expected_date: str = ""
    price_per_unit: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MaterialTransaction':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class MaterialTransactionStore:
    """
    Storage for material transactions.
    Provides history tracking and stock calculations.
    """
    
    def __init__(self, data_dir_path: Optional[Path] = None):
        self._data_dir = data_dir_path or data_dir()
        self._transactions_file = self._data_dir / "material_transactions.json"
        self._stock_file = self._data_dir / "material_stock.json"
    
    def _load_transactions(self) -> list[dict]:
        """Load all transactions from file."""
        if not self._transactions_file.exists():
            return []
        try:
            data = json.loads(self._transactions_file.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []
    
    def _save_transactions(self, transactions: list[dict]) -> None:
        """Save transactions to file."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._transactions_file.write_text(
            json.dumps(transactions, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    def _load_stock(self) -> dict:
        """Load current stock levels."""
        if not self._stock_file.exists():
            return {}
        try:
            return json.loads(self._stock_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
    
    def _save_stock(self, stock: dict) -> None:
        """Save stock levels."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._stock_file.write_text(
            json.dumps(stock, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    # === Core operations ===
    
    def create_transaction(self, transaction: MaterialTransaction) -> MaterialTransaction:
        """Create a new transaction."""
        transactions = self._load_transactions()
        transaction.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        transactions.append(transaction.to_dict())
        self._save_transactions(transactions)
        return transaction
    
    def get_transaction(self, transaction_id: str) -> Optional[MaterialTransaction]:
        """Get transaction by ID."""
        transactions = self._load_transactions()
        for t in transactions:
            if t.get("id") == transaction_id:
                return MaterialTransaction.from_dict(t)
        return None
    
    def list_transactions(
        self,
        material_id: Optional[str] = None,
        order_code: Optional[str] = None,
        transaction_type: Optional[str] = None,
        status: Optional[str] = None,
        worker_name: Optional[str] = None,
    ) -> list[MaterialTransaction]:
        """List transactions with optional filters."""
        transactions = self._load_transactions()
        result = []
        
        for t in transactions:
            if material_id and t.get("material_id") != material_id:
                continue
            if order_code and t.get("order_code") != order_code:
                continue
            if transaction_type and t.get("transaction_type") != transaction_type:
                continue
            if status and t.get("status") != status:
                continue
            if worker_name and t.get("worker_name") != worker_name:
                continue
            result.append(MaterialTransaction.from_dict(t))
        
        return result
    
    def complete_transaction(self, transaction_id: str, worker_name: str) -> bool:
        """Mark transaction as completed and update stock."""
        transactions = self._load_transactions()
        
        for i, t in enumerate(transactions):
            if t.get("id") != transaction_id:
                continue
            
            transactions[i]["status"] = "zakończony"
            transactions[i]["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Update stock for RECEIVE and ADJUST
            if t.get("transaction_type") in ("RECEIVE", "ADJUST", "RETURN"):
                self._update_stock(t.get("material_id", ""), t.get("quantity", 0))
            elif t.get("transaction_type") == "TAKE":
                self._update_stock(t.get("material_id", ""), -abs(t.get("quantity", 0)))
            
            self._save_transactions(transactions)
            return True
        
        return False
    
    def cancel_transaction(self, transaction_id: str, reason: str = "") -> bool:
        """Cancel a pending transaction."""
        transactions = self._load_transactions()
        
        for i, t in enumerate(transactions):
            if t.get("id") != transaction_id:
                continue
            if t.get("status") != "oczekuje":
                return False  # Can only cancel pending
            
            transactions[i]["status"] = "anulowany"
            transactions[i]["notes"] = f"{t.get('notes', '')}\nAnulowano: {reason}".strip()
            
            self._save_transactions(transactions)
            return True
        
        return False
    
    # === Stock management ===
    
    def _update_stock(self, material_id: str, change: float) -> None:
        """Update stock level for a material."""
        stock = self._load_stock()
        current = stock.get(material_id, 0.0)
        stock[material_id] = current + change
        self._save_stock(stock)
    
    def get_stock(self, material_id: str) -> float:
        """Get current stock level for a material."""
        stock = self._load_stock()
        return stock.get(material_id, 0.0)
    
    def get_all_stock(self) -> dict[str, float]:
        """Get all stock levels."""
        return self._load_stock()
    
    # === History ===
    
    def get_material_history(self, material_id: str) -> list[MaterialTransaction]:
        """Get full transaction history for a material."""
        return self.list_transactions(material_id=material_id)
    
    def get_order_materials(self, order_code: str) -> list[MaterialTransaction]:
        """Get all material transactions for an order."""
        return self.list_transactions(order_code=order_code)
    
    # === Quick actions for alarms ===
    
    def reserve_material(
        self,
        material_id: str,
        material_name: str,
        quantity: float,
        order_code: str,
        worker_name: str,
        notes: str = "",
    ) -> MaterialTransaction:
        """Quick action: Reserve material for order."""
        tx = MaterialTransaction(
            transaction_type="RESERVE",
            material_id=material_id,
            material_name=material_name,
            quantity=quantity,
            order_code=order_code,
            worker_name=worker_name,
            notes=notes,
            status="oczekuje",
        )
        return self.create_transaction(tx)
    
    def take_material(
        self,
        material_id: str,
        material_name: str,
        quantity: float,
        order_code: str,
        worker_name: str,
        notes: str = "",
    ) -> MaterialTransaction:
        """Quick action: Take (spisz) material from stock."""
        tx = MaterialTransaction(
            transaction_type="TAKE",
            material_id=material_id,
            material_name=material_name,
            quantity=-abs(quantity),  # Negative - removing from stock
            order_code=order_code,
            worker_name=worker_name,
            notes=notes,
            status="oczekuje",
        )
        result = self.create_transaction(tx)
        # Auto-complete take (spisanie)
        self.complete_transaction(result.id, worker_name)
        return result
    
    def create_purchase(
        self,
        material_id: str,
        material_name: str,
        quantity: float,
        supplier: str,
        expected_date: str,
        worker_name: str,
        order_code: str = "",
        price_per_unit: float = 0.0,
    ) -> MaterialTransaction:
        """Quick action: Create purchase order."""
        tx = MaterialTransaction(
            transaction_type="PURCHASE",
            material_id=material_id,
            material_name=material_name,
            quantity=quantity,
            supplier=supplier,
            expected_date=expected_date,
            price_per_unit=price_per_unit,
            order_code=order_code,
            worker_name=worker_name,
            notes=f"Zakup od: {supplier}",
            status="oczekuje",
        )
        return self.create_transaction(tx)
    
    def receive_material(
        self,
        material_id: str,
        material_name: str,
        quantity: float,
        worker_name: str,
        purchase_id: str = "",
        notes: str = "",
    ) -> MaterialTransaction:
        """Quick action: Receive material to stock."""
        tx = MaterialTransaction(
            transaction_type="RECEIVE",
            material_id=material_id,
            material_name=material_name,
            quantity=abs(quantity),  # Positive - adding to stock
            worker_name=worker_name,
            notes=f"Przyjęcie {f'(zakup: {purchase_id})' if purchase_id else ''} {notes}",
            status="oczekuje",
        )
        result = self.create_transaction(tx)
        # Auto-complete receive
        self.complete_transaction(result.id, worker_name)
        return result
    
    # === Statistics ===
    
    def get_pending_purchases(self) -> list[MaterialTransaction]:
        """Get all pending purchase orders."""
        return [
            t for t in self.list_transactions(transaction_type="PURCHASE", status="oczekuje")
        ]
    
    def get_low_stock_alerts(self, threshold: float = 10.0) -> list[dict]:
        """Get materials with low stock."""
        stock = self._load_stock()
        alerts = []
        for material_id, level in stock.items():
            if level < threshold:
                alerts.append({
                    "material_id": material_id,
                    "stock_level": level,
                    "threshold": threshold,
                })
        return alerts


# Convenience functions
def quick_take(material_id: str, material_name: str, qty: float, order: str, worker: str) -> MaterialTransaction:
    """Quick spisanie material."""
    store = MaterialTransactionStore()
    return store.take_material(material_id, material_name, qty, order, worker)


def quick_purchase(material_id: str, material_name: str, qty: float, supplier: str, worker: str) -> MaterialTransaction:
    """Quick zakup material."""
    store = MaterialTransactionStore()
    return store.create_purchase(material_id, material_name, qty, supplier, "", worker)
