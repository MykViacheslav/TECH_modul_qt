from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Dict

from src.integrations.telegram_checklist import (
    _api_base,
    _post_json,
    _load_state,
    _save_state,
    _CALLBACK_PREFIX,
    _STATE_DONE,
    _STATE_TODO,
    _STATE_PARTIAL
)
from src.domain.order_models import OrderDef
from src.domain.worker_models import WorkerDef

# New prefix for production production callbacks to avoid collision with shopping
_PROD_CALLBACK_PREFIX = "prodhub"


def send_production_status_checklist(
    bot_token: str,
    chat_id: str,
    orders: List[OrderDef],
    title: str = "TECH_modul - Status Produkcji"
) -> Dict[str, Any]:
    """
    Sends a message to Telegram with a list of active orders and their production status buttons.
    Each button toggles the production/montaz stage.
    """
    # Filter only active or recent orders to avoid spamming
    selected_orders = [o for o in orders if o.status not in ("Zakonczone", "Anulowane")][:15]
    
    state_items: List[Dict[str, Any]] = []
    for order in selected_orders:
        status_norm = str(order.status or "").strip().lower()
        state = _STATE_DONE if status_norm == "zakonczone" else (_STATE_PARTIAL if status_norm == "w produkcji" else _STATE_TODO)
        
        label = f"{order.order_name or order.id} ({order.client_name or '-'})"
        state_items.append({
            "order_id": str(order.id or order.order_id),
            "label": label,
            "state": state,
            "progress": float(order.progress_percent or 0.0)
        })

    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    list_id = f"P{stamp[-8:]}"
    
    text_lines = [
        f"🏭 {title}",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "Statusy zlecen:"
    ]
    for idx, it in enumerate(state_items, start=1):
        mark = "✅" if it["state"] == _STATE_DONE else ("🟡" if it["state"] == _STATE_PARTIAL else "⚪")
        text_lines.append(f"{idx}. {mark} {it['label']} [{it['progress']:.0f}%]")
    
    text_lines.append("")
    text_lines.append("Kliknij numer, aby zmienic status zlecenia.")

    # Build keyboard
    keyboard: List[List[Dict[str, str]]] = []
    row: List[Dict[str, str]] = []
    for idx, it in enumerate(state_items):
        mark = "✅" if it["state"] == _STATE_DONE else ("🟡" if it["state"] == _STATE_PARTIAL else "⚪")
        row.append({
            "text": f"{idx+1} {mark}",
            "callback_data": f"{_PROD_CALLBACK_PREFIX}|{list_id}|{idx}"
        })
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    payload = {
        "chat_id": str(chat_id),
        "text": "\n".join(text_lines),
        "reply_markup": {"inline_keyboard": keyboard}
    }
    
    result = _post_json(bot_token, "sendMessage", payload)
    message_id = int(result.get("message_id", 0))
    
    # Save to local state for syncing back
    state = _load_state()
    lists = state.get("lists", {})
    lists[list_id] = {
        "list_id": list_id,
        "kind": "production",
        "chat_id": str(chat_id),
        "message_id": message_id,
        "items": state_items,
        "updated_at": datetime.now().isoformat()
    }
    state["lists"] = lists
    _save_state(state)
    
    return {"list_id": list_id, "message_id": message_id}


def send_worker_attendance_poll(
    bot_token: str,
    chat_id: str,
    workers: List[WorkerDef],
    title: str = "TECH_modul - Rejestracja Czasu"
) -> Dict[str, Any]:
    """
    Sends a message with employee names as buttons. 
    Clicking a button logs start/end of work in the system.
    """
    text = (
        f"👥 {title}\n"
        f"Kto dzisiaj pracuje? Kliknij swoje imie, aby 'odbic karte'.\n"
        f"Aktualny czas: {datetime.now().strftime('%H:%M')}"
    )
    
    keyboard: List[List[Dict[str, str]]] = []
    for w in workers:
        if not w.name: continue
        keyboard.append([{
            "text": f"👤 {w.name}",
            "callback_data": f"worktime|punch|{w.worker_id}"
        }])
        
    payload = {
        "chat_id": str(chat_id),
        "text": text,
        "reply_markup": {"inline_keyboard": keyboard}
    }
    
    return _post_json(bot_token, "sendMessage", payload)
