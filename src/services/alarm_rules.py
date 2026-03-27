"""
Plug-in style alarm check rules for AlarmService.

Each rule is a function that takes context and returns List[AlarmDef].
Rules can be registered with AlarmService.register_rule().
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List

from src.domain.alarm_models import AlarmDef, new_alarm_id
from src.storage.alarm_store_json import AlarmStoreJson
from src.storage.data_paths import data_dir
from src.storage.order_store_json import OrderStoreJson
from src.storage.service_store_json import ServiceStoreJson


def check_material_stock_for_order(context: Any = None) -> List[AlarmDef]:
    """
    Check material availability for a specific order or all active orders.
    
    Context can be:
    - None: checks all active orders
    - dict with "order_code": checks specific order
    """
    alarms: List[AlarmDef] = []
    store = AlarmStoreJson()
    order_store = OrderStoreJson()
    existing_alarms = store.list_alarms()
    
    # Load material database
    material_rows = _load_material_rows()
    by_id: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    for row in material_rows:
        mat_id = str(row.get("id", "") or "").strip()
        name = str(row.get("nazwa", "") or "").strip()
        if mat_id:
            by_id[mat_id] = row
        if name:
            by_name[name.lower()] = row
    
    # Get orders to check
    orders = order_store.list_orders()
    if isinstance(context, dict) and "order_code" in context:
        order_code = context["order_code"]
        orders = [o for o in orders if str(getattr(o, "order_id", "") or "") == order_code]
    
    for order in orders:
        order_code = str(getattr(order, "order_id", "") or getattr(order, "code", "") or "").strip()
        if not order_code:
            continue
        
        status = str(getattr(order, "status", "") or "").strip().lower()
        if status not in {"zaakceptowane", "zakup materialow", "w produkcji", "lakiernia", "montaz"}:
            continue
        
        # Check material_choices
        raw_choices = getattr(order, "material_choices", [])
        choices = [x for x in raw_choices if isinstance(x, dict)]
        final_choices = [x for x in choices if str(x.get("status", "") or "").strip().lower() == "wybrane finalnie"]
        
        for choice in final_choices:
            mat_name = str(choice.get("material_name", "") or "").strip()
            mat_id = str(choice.get("material_id", "") or "").strip()
            qty_needed = _safe_float(choice.get("qty", 0.0))
            
            if qty_needed <= 0:
                continue
            
            # Find material in database
            key = mat_id if mat_id else mat_name.lower()
            source_row = by_id.get(key) if key in by_id else by_name.get(key.lower())
            
            if not source_row:
                # Material not in database
                title = f"Zamówienie {order_code} - brak materiału w bazie: {mat_name}"
                if not _alarm_exists(existing_alarms, title, "materialy"):
                    alarms.append(AlarmDef(
                        alarm_id=new_alarm_id(),
                        category="materialy",
                        severity="ostrzezenie",
                        title=title,
                        description=f"Materiał '{mat_name}' nie istnieje w bazie materiałów.",
                        related_order=order_code,
                        related_material=mat_name or mat_id,
                        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ))
                continue
            
            stock = _safe_float(source_row.get("ilosc_magazyn", source_row.get("ilosc", 0.0)))
            
            if stock < qty_needed:
                missing = qty_needed - stock
                title = f"Zamówienie {order_code} - brak materiału: {mat_name}"
                if not _alarm_exists(existing_alarms, title, "materialy"):
                    alarms.append(AlarmDef(
                        alarm_id=new_alarm_id(),
                        category="materialy",
                        severity="krytyczny",
                        title=title,
                        description=f"Potrzeba {qty_needed:.2f}, na magazynie {stock:.2f}, brakuje {missing:.2f}",
                        related_order=order_code,
                        related_material=mat_name or mat_id,
                        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ))
    
    return alarms


def check_deadline_conflict(context: Any = None) -> List[AlarmDef]:
    """
    Check for deadline conflicts across orders and services.
    
    Context can be:
    - None: checks all orders/services
    - dict with "order_code": checks specific order
    """
    alarms: List[AlarmDef] = []
    store = AlarmStoreJson()
    order_store = OrderStoreJson()
    service_store = ServiceStoreJson()
    existing_alarms = store.list_alarms()
    today = datetime.now().date()
    
    # Check order deadlines
    orders = order_store.list_orders()
    if isinstance(context, dict) and "order_code" in context:
        order_code = context["order_code"]
        orders = [o for o in orders if str(getattr(o, "order_id", "") or "") == order_code]
    
    for order in orders:
        order_code = str(getattr(order, "order_id", "") or "").strip()
        if not order_code:
            continue
        
        for stage, date_field in (
            ("Projekt", "date_projekt"),
            ("Zakup materiałów", "date_zakup_mat"),
            ("Produkcja", "date_produkcja"),
            ("Montaż", "date_montaz"),
        ):
            date_str = str(getattr(order, date_field, "") or "").strip()
            if not date_str:
                continue
            
            try:
                stage_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            
            days_until = (stage_date - today).days
            
            if days_until < 0:
                title = f"{order_code} - {stage} zaległy"
                if not _alarm_exists(existing_alarms, title, "terminy"):
                    alarms.append(AlarmDef(
                        alarm_id=new_alarm_id(),
                        category="terminy",
                        severity="krytyczny",
                        title=title,
                        description=f"Etap '{stage}' zamówienia {order_code} jest zaległy o {-days_until} dni.",
                        related_order=order_code,
                        due_date=date_str,
                        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ))
            elif 0 < days_until <= 3:
                title = f"{order_code} - {stage} za {days_until} dni"
                if not _alarm_exists(existing_alarms, title, "terminy"):
                    alarms.append(AlarmDef(
                        alarm_id=new_alarm_id(),
                        category="terminy",
                        severity="ostrzezenie",
                        title=title,
                        description=f"Etap '{stage}' zamówienia {order_code} za {days_until} dni.",
                        related_order=order_code,
                        due_date=date_str,
                        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ))
    
    # Check service deadlines
    services = service_store.list_services()
    for svc in services:
        service_name = str(getattr(svc, "name", "") or "").strip()
        service_id = str(getattr(svc, "service_id", "") or "").strip()
        deadline = str(getattr(svc, "deadline", "") or "").strip()
        
        if not service_name or not deadline:
            continue
        
        try:
            deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
        except ValueError:
            continue
        
        days_until = (deadline_date - today).days
        
        if days_until < 0:
            title = f"Usługa {service_name} - termin zaległy"
            if not _alarm_exists(existing_alarms, title, "terminy"):
                alarms.append(AlarmDef(
                    alarm_id=new_alarm_id(),
                    category="terminy",
                    severity="krytyczny",
                    title=title,
                    description=f"Termin usługi '{service_name}' minął {-days_until} dni temu.",
                    related_order=service_id,
                    due_date=deadline,
                    created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ))
        elif 0 < days_until <= 3:
            title = f"Usługa {service_name} - termin za {days_until} dni"
            if not _alarm_exists(existing_alarms, title, "terminy"):
                alarms.append(AlarmDef(
                    alarm_id=new_alarm_id(),
                    category="terminy",
                    severity="ostrzezenie",
                    title=title,
                    description=f"Termin usługi '{service_name}' za {days_until} dni.",
                    related_order=service_id,
                    due_date=deadline,
                    created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ))
    
    return alarms


def check_worker_overload(context: Any = None) -> List[AlarmDef]:
    """
    Check for worker overload based on assigned orders.
    
    Context can be:
    - None: checks all workers
    - dict with "worker_name": checks specific worker
    """
    alarms: List[AlarmDef] = []
    store = AlarmStoreJson()
    order_store = OrderStoreJson()
    existing_alarms = store.list_alarms()
    today = datetime.now().date()
    
    # Count orders per worker
    worker_orders: dict[str, list] = {}
    for order in order_store.list_orders():
        worker = str(getattr(order, "worker_name", "") or "").strip()
        if not worker:
            continue
        
        status = str(getattr(order, "status", "") or "").strip().lower()
        if status in {"zakończone", "zamknięte", "anulowane"}:
            continue
        
        worker_orders.setdefault(worker, []).append(order)
    
    # Check specific worker if context provided
    if isinstance(context, dict) and "worker_name" in context:
        worker_name = context["worker_name"]
        worker_orders = {worker_name: worker_orders.get(worker_name, [])}
    
    # Threshold: more than 5 active orders is overload
    OVERLOAD_THRESHOLD = 5
    
    for worker_name, orders in worker_orders.items():
        if len(orders) >= OVERLOAD_THRESHOLD:
            # Count overdue orders
            overdue_count = 0
            for order in orders:
                for date_field in ("date_montaz", "date_produkcja", "date_projekt"):
                    date_str = str(getattr(order, date_field, "") or "").strip()
                    if not date_str:
                        continue
                    try:
                        if datetime.strptime(date_str, "%Y-%m-%d").date() < today:
                            overdue_count += 1
                            break
                    except ValueError:
                        continue
            
            if overdue_count > 0:
                severity = "krytyczny" if overdue_count >= 2 else "ostrzezenie"
                title = f"Pracownik {worker_name} - przeciążenie ({len(orders)} zleceń)"
                if not _alarm_exists(existing_alarms, title, "pracownicy"):
                    alarms.append(AlarmDef(
                        alarm_id=new_alarm_id(),
                        category="pracownicy",
                        severity=severity,
                        title=title,
                        description=f"Pracownik ma {len(orders)} aktywnych zleceń, w tym {overdue_count} zaległych.",
                        related_worker=worker_name,
                        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ))
    
    return alarms


def update_inventory_on_order_confirm(context: Any = None) -> List[AlarmDef]:
    """
    Update inventory when an order is confirmed/started.
    
    Context must be:
    - dict with "order_code": the order being confirmed
    - dict with "order_code" and "action": "confirm" or "release"
    
    Returns list of alarms for materials that couldn't be deducted.
    """
    alarms: List[AlarmDef] = []
    
    if not isinstance(context, dict) or "order_code" not in context:
        return alarms
    
    order_code = context["order_code"]
    action = context.get("action", "confirm")
    
    order_store = OrderStoreJson()
    material_path = data_dir() / "baza_materialu.json"
    
    # Find the order
    order = None
    for o in order_store.list_orders():
        if str(getattr(o, "order_id", "") or "") == order_code:
            order = o
            break
    
    if not order:
        return alarms
    
    # Load material database
    try:
        raw = json.loads(material_path.read_text(encoding="utf-8")) if material_path.exists() else {}
        material_data = raw if isinstance(raw, dict) else {}
        rows = material_data.get("rows", [])
    except Exception:
        rows = []
    
    # Build index
    by_id: dict[str, int] = {}
    by_name: dict[str, int] = {}
    for i, row in enumerate(rows):
        mat_id = str(row.get("id", "") or "").strip()
        name = str(row.get("nazwa", "") or "").strip()
        if mat_id:
            by_id[mat_id] = i
        if name:
            by_name[name.lower()] = i
    
    # Get material choices
    raw_choices = getattr(order, "material_choices", [])
    choices = [x for x in raw_choices if isinstance(x, dict)]
    
    if action == "confirm":
        # Deduct materials from inventory
        for choice in choices:
            mat_name = str(choice.get("material_name", "") or "").strip()
            mat_id = str(choice.get("material_id", "") or "").strip()
            qty = _safe_float(choice.get("qty", 0.0))
            status = str(choice.get("status", "") or "").strip().lower()
            
            if qty <= 0 or status != "wybrane finalnie":
                continue
            
            # Find material
            key = mat_id if mat_id else mat_name.lower()
            row_idx = by_id.get(key) if key in by_id else by_name.get(key.lower())
            
            if row_idx is None:
                title = f"Zamówienie {order_code} - brak materiału w bazie: {mat_name}"
                alarms.append(AlarmDef(
                    alarm_id=new_alarm_id(),
                    category="materialy",
                    severity="ostrzezenie",
                    title=title,
                    description=f"Nie można odjąć '{mat_name}' - nie ma w bazie.",
                    related_order=order_code,
                    related_material=mat_name or mat_id,
                    created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ))
                continue
            
            row = rows[row_idx]
            current_stock = _safe_float(row.get("ilosc_magazyn", row.get("ilosc", 0.0)))
            new_stock = max(0.0, current_stock - qty)
            rows[row_idx]["ilosc_magazyn"] = new_stock
            
            if new_stock <= 0:
                title = f"Material {mat_name} - wyczerpany po zamówieniu {order_code}"
                alarms.append(AlarmDef(
                    alarm_id=new_alarm_id(),
                    category="materialy",
                    severity="krytyczny",
                    title=title,
                    description=f"Zamówienie {order_code} zużyło ostatnie sztuki materiału '{mat_name}'.",
                    related_order=order_code,
                    related_material=mat_name or mat_id,
                    created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ))
        
        # Save updated material database
        try:
            material_data["rows"] = rows
            material_path.write_text(json.dumps(material_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"Failed to save material database: {e}")
    
    elif action == "release":
        # Release materials back to inventory (order cancelled)
        for choice in choices:
            mat_name = str(choice.get("material_name", "") or "").strip()
            mat_id = str(choice.get("material_id", "") or "").strip()
            qty = _safe_float(choice.get("qty", 0.0))
            status = str(choice.get("status", "") or "").strip().lower()
            
            if qty <= 0 or status != "wybrane finalnie":
                continue
            
            key = mat_id if mat_id else mat_name.lower()
            row_idx = by_id.get(key) if key in by_id else by_name.get(key.lower())
            
            if row_idx is not None:
                current_stock = _safe_float(rows[row_idx].get("ilosc_magazyn", rows[row_idx].get("ilosc", 0.0)))
                rows[row_idx]["ilosc_magazyn"] = current_stock + qty
        
        # Save updated material database
        try:
            material_data["rows"] = rows
            material_path.write_text(json.dumps(material_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"Failed to save material database: {e}")
    
    return alarms


def check_payment_overdue(context: Any = None) -> List[AlarmDef]:
    """
    Check for overdue payments and cash flow issues.
    """
    alarms: List[AlarmDef] = []
    store = AlarmStoreJson()
    order_store = OrderStoreJson()
    existing_alarms = store.list_alarms()
    today = datetime.now().date()
    
    for order in order_store.list_orders():
        order_code = str(getattr(order, "order_id", "") or "").strip()
        if not order_code:
            continue
        
        # Check for unpaid orders with montaz date in the past
        montaz_date_str = str(getattr(order, "date_montaz", "") or "").strip()
        if not montaz_date_str:
            continue
        
        try:
            montaz_date = datetime.strptime(montaz_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        
        if montaz_date < today:
            status = str(getattr(order, "status", "") or "").strip().lower()
            # Check if order is marked as paid
            payment_status = str(getattr(order, "payment_status", "") or "").strip().lower()
            
            if status == "montaz" and payment_status not in {"zapłacono", "zaplacono", "opłacono", "oplacono"}:
                days_overdue = (today - montaz_date).days
                title = f"Zamówienie {order_code} - brak płatności po montażu"
                if not _alarm_exists(existing_alarms, title, "platnosci"):
                    alarms.append(AlarmDef(
                        alarm_id=new_alarm_id(),
                        category="platnosci",
                        severity="krytyczny",
                        title=title,
                        description=f"Montaż odbył się {days_overdue} dni temu, brak potwierdzenia płatności.",
                        related_order=order_code,
                        due_date=montaz_date_str,
                        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ))
    
    return alarms


# --- Helper functions ---

def _safe_float(value: Any) -> float:
    """Convert value to float safely."""
    raw = str(value or "").strip().replace(" ", "").replace(",", ".")
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _alarm_exists(existing_alarms: list, title: str, category: str) -> bool:
    """Check if an unresolved alarm with same title and category exists."""
    for alarm in existing_alarms:
        if alarm.is_resolved:
            continue
        if alarm.title == title and alarm.category == category:
            return True
    return False


def _load_material_rows() -> list[dict[str, Any]]:
    """Load material rows from JSON file."""
    path = data_dir() / "baza_materialu.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        rows = raw.get("rows", []) if isinstance(raw, dict) else []
        return [dict(x) for x in rows if isinstance(x, dict)]
    except Exception:
        return []


def register_default_rules(service) -> None:
    """
    Register all default alarm rules with an AlarmService instance.
    
    Usage:
        from src.services.alarm_service import AlarmService
        from src.services.alarm_rules import register_default_rules
        
        service = AlarmService.instance()
        register_default_rules(service)
    """
    service.register_rule(check_material_stock_for_order, "Sprawdź dostępność materiałów")
    service.register_rule(check_deadline_conflict, "Sprawdź konflikty terminów")
    service.register_rule(check_worker_overload, "Sprawdź przeciążenie pracowników")
    service.register_rule(check_payment_overdue, "Sprawdź zaległe płatności")
    # Note: update_inventory_on_order_confirm is NOT registered by default
    # because it modifies data and should be called explicitly when confirming orders
