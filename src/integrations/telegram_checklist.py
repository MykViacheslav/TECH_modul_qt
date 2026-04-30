from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.domain.shopping_models import ShoppingItemDef
from src.storage.data_paths import data_dir
from src.storage.safe_json_io import read_json_file, write_json_atomic


_CALLBACK_PREFIX = "shopchk"
_PROD_CALLBACK_PREFIX = "prodhub"
_WORKTIME_CALLBACK_PREFIX = "worktime"
_MAX_ITEMS_PER_MESSAGE = 40
_STATE_TODO = "todo"
_STATE_PARTIAL = "partial"
_STATE_DONE = "done"


def _state_path() -> Path:
    path = data_dir() / "telegram_checklists.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        write_json_atomic(path, {"last_update_id": 0, "lists": {}}, ensure_ascii=False, indent=2)
    return path


def _api_base(bot_token: str) -> str:
    token = str(bot_token or "").strip()
    if not token:
        raise ValueError("Brak Telegram Bot Token.")
    return f"https://api.telegram.org/bot{token}"


def _post_json(bot_token: str, method: str, payload: dict[str, Any]) -> Any:
    base = _api_base(bot_token)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(
        f"{base}/{method}",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=25) as res:
            raw = res.read().decode("utf-8", errors="replace")
            obj = json.loads(raw) if raw else {}
    except HTTPError as exc:
        details = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
            obj = json.loads(body) if body else {}
            details = str(obj.get("description", "") or "").strip()
        except Exception:
            details = ""
        suffix = f" ({details})" if details else ""
        raise RuntimeError(f"Telegram HTTP {exc.code}: {exc.reason}{suffix}") from exc
    except URLError as exc:
        raise RuntimeError(f"Brak polaczenia z Telegram: {exc.reason}") from exc

    if not bool(obj.get("ok", False)):
        raise RuntimeError(str(obj.get("description", "Blad Telegram API")))
    return obj.get("result")


def _load_state() -> dict[str, Any]:
    data = read_json_file(_state_path(), default={"last_update_id": 0, "lists": {}}, expected_type=dict)
    lists = data.get("lists")
    if not isinstance(lists, dict):
        lists = {}
    return {
        "last_update_id": int(data.get("last_update_id", 0) or 0),
        "lists": lists,
    }


def _save_state(state: dict[str, Any]) -> None:
    write_json_atomic(_state_path(), state, ensure_ascii=False, indent=2)


def _item_label(item: ShoppingItemDef) -> str:
    name = str(item.material_name or item.material_id or "Pozycja").strip()
    qty = float(item.quantity_needed or 0.0)
    unit = str(item.unit or "").strip()
    qty_txt = f"{qty:.2f}".rstrip("0").rstrip(".")
    if unit:
        return f"{name} ({qty_txt} {unit})"
    return f"{name} ({qty_txt})"


def _truncate_text(text: str, max_len: int) -> str:
    src = str(text or "").strip()
    if len(src) <= max_len:
        return src
    return src[: max(1, max_len - 3)].rstrip() + "..."


def _normalize_item_state(raw_state: Any, raw_checked: Any = False) -> str:
    value = str(raw_state or "").strip().lower()
    if value in {_STATE_TODO, "open", "new"}:
        return _STATE_TODO
    if value in {_STATE_PARTIAL, "part", "ordered", "zamowiono"}:
        return _STATE_PARTIAL
    if value in {_STATE_DONE, "done", "checked", "zakupiono"}:
        return _STATE_DONE
    return _STATE_DONE if bool(raw_checked) else _STATE_TODO


def _state_mark_text(state: str) -> str:
    norm = _normalize_item_state(state)
    if norm == _STATE_DONE:
        return "✅"
    if norm == _STATE_PARTIAL:
        return "🟨"
    return "⬜"


def _state_mark_button(state: str) -> str:
    norm = _normalize_item_state(state)
    if norm == _STATE_DONE:
        return "✅"
    if norm == _STATE_PARTIAL:
        return "🟨"
    return "⬜"


def _next_state(state: str) -> str:
    norm = _normalize_item_state(state)
    if norm == _STATE_TODO:
        return _STATE_PARTIAL
    if norm == _STATE_PARTIAL:
        return _STATE_DONE
    return _STATE_TODO


def _build_message_text(title: str, items: list[dict[str, Any]], total_source_count: int) -> str:
    done = sum(
        1
        for it in items
        if _normalize_item_state(it.get("state"), it.get("checked", False)) == _STATE_DONE
    )
    partial = sum(
        1
        for it in items
        if _normalize_item_state(it.get("state"), it.get("checked", False)) == _STATE_PARTIAL
    )
    lines = [
        f"🧾 {str(title or 'Lista zakupow')}",
        f"✅ Kupione: {done}/{len(items)}   🟨 Czesciowo: {partial}",
    ]
    if total_source_count > len(items):
        lines.append(f"Pokazano pierwsze {len(items)} z {total_source_count} pozycji.")
    lines.append("")
    for idx, item in enumerate(items, start=1):
        mark = _state_mark_text(_normalize_item_state(item.get("state"), item.get("checked", False)))
        label = _truncate_text(str(item.get("label", "") or f"Pozycja {idx}"), 64)
        lines.append(f"{idx}. {mark} {label}")
    lines.append("")
    lines.append("Kliknij numer pozycji w przyciskach ponizej.")
    lines.append("Cykl: ⬜ -> 🟨 -> ✅ -> ⬜")
    lines.append("🟨 = hurtownia ma tylko czesc ilosci.")
    return "\n".join(lines)


def _build_markup(list_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    keyboard: list[list[dict[str, str]]] = []
    row: list[dict[str, str]] = []
    for idx, item in enumerate(items):
        mark = _state_mark_button(_normalize_item_state(item.get("state"), item.get("checked", False)))
        row.append(
            {
                "text": f"{idx + 1} {mark}",
                "callback_data": f"{_CALLBACK_PREFIX}|{list_id}|{idx}",
            }
        )
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append(
        [
            {
                "text": "↩ Cofnij",
                "callback_data": f"{_CALLBACK_PREFIX}|{list_id}|u",
            },
            {
                "text": "🔄 Odswiez",
                "callback_data": f"{_CALLBACK_PREFIX}|{list_id}|r",
            },
        ]
    )
    return {"inline_keyboard": keyboard}


def send_shopping_checklist_message(
    bot_token: str,
    chat_id: str,
    items: list[ShoppingItemDef],
    title: str = "TECH_modul - lista zakupow",
) -> dict[str, Any]:
    selected = list(items)[:_MAX_ITEMS_PER_MESSAGE]
    state_items: list[dict[str, Any]] = []
    for item in selected:
        status = str(getattr(item, "status", "") or "").strip().lower()
        state = _STATE_DONE if status == "zakupiono" else (_STATE_PARTIAL if status == "zamowiono" else _STATE_TODO)
        state_items.append(
            {
                "item_id": str(item.item_id or "").strip(),
                "label": _item_label(item),
                "state": state,
                "checked": state == _STATE_DONE,
            }
        )

    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    list_id = f"L{stamp[-8:]}"
    text = _build_message_text(title=title, items=state_items, total_source_count=len(items))
    markup = _build_markup(list_id=list_id, items=state_items)

    payload = {
        "chat_id": str(chat_id or "").strip(),
        "text": text,
        "reply_markup": markup,
    }
    result = _post_json(bot_token=bot_token, method="sendMessage", payload=payload)
    if not isinstance(result, dict):
        raise RuntimeError("Telegram nie zwrocil danych wiadomosci checklisty.")
    message_id = int(result.get("message_id", 0) or 0)
    if message_id <= 0:
        raise RuntimeError("Telegram nie zwrocil message_id dla checklisty.")

    state = _load_state()
    lists = dict(state.get("lists", {}) or {})
    lists[list_id] = {
        "list_id": list_id,
        "chat_id": str(chat_id or "").strip(),
        "message_id": message_id,
        "title": str(title or "").strip(),
        "source_count": len(items),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "items": state_items,
        "history": [],
    }
    state["lists"] = lists
    _save_state(state)
    return {"list_id": list_id, "message_id": message_id}


def _answer_callback(bot_token: str, callback_query_id: str, text: str = "") -> bool:
    payload: dict[str, Any] = {"callback_query_id": str(callback_query_id or "").strip()}
    if str(text or "").strip():
        payload["text"] = str(text).strip()
    try:
        _post_json(bot_token=bot_token, method="answerCallbackQuery", payload=payload)
        return True
    except Exception:
        # Callback might already be expired - do not block checklist sync.
        return False


def _edit_checklist_message(bot_token: str, list_state: dict[str, Any]) -> None:
    list_id = str(list_state.get("list_id", "") or "").strip()
    chat_id = str(list_state.get("chat_id", "") or "").strip()
    message_id = int(list_state.get("message_id", 0) or 0)
    title = str(list_state.get("title", "TECH_modul - lista zakupow") or "TECH_modul - lista zakupow")
    items = list(list_state.get("items", []) or [])
    source_count = int(list_state.get("source_count", len(items)) or len(items))
    text = _build_message_text(title=title, items=items, total_source_count=source_count)
    markup = _build_markup(list_id=list_id, items=items)
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "reply_markup": markup,
    }
    _post_json(bot_token=bot_token, method="editMessageText", payload=payload)


def sync_telegram_hub_callbacks(bot_token: str) -> dict[str, Any]:
    state = _load_state()
    last_update_id = int(state.get("last_update_id", 0) or 0)
    lists = dict(state.get("lists", {}) or {})

    result = _post_json(
        bot_token=bot_token,
        method="getUpdates",
        payload={"offset": last_update_id + 1, "timeout": 0},
    )
    updates = result if isinstance(result, list) else []

    applied_shopping: list[dict[str, Any]] = []
    applied_other: list[dict[str, Any]] = []
    max_update_id = last_update_id

    for upd in updates:
        if not isinstance(upd, dict):
            continue
        update_id = int(upd.get("update_id", 0) or 0)
        if update_id > max_update_id:
            max_update_id = update_id

        cq = upd.get("callback_query")
        if not isinstance(cq, dict):
            continue
        data = str(cq.get("data", "") or "").strip()
        
        # Dispatch by prefix
        if data.startswith(f"{_CALLBACK_PREFIX}|"):
            # Existing shopping logic
            parts = data.split("|")
            if len(parts) != 3: continue
            _, list_id, selector = parts
            list_state = lists.get(list_id)
            if not isinstance(list_state, dict):
                _answer_callback(bot_token, cq.get("id", ""), "Lista wygasla")
                continue
            
            items = list(list_state.get("items", []) or [])
            changed = False
            history = list(list_state.get("history", []) or [])
            
            if selector == "u" and history:
                last = history.pop()
                idx = int(last.get("idx", -1))
                prev = _normalize_item_state(last.get("prev_state"), last.get("prev_checked", False))
                if 0 <= idx < len(items):
                    items[idx]["state"] = prev
                    items[idx]["checked"] = (prev == _STATE_DONE)
                    changed = True
                    applied_shopping.append({"item_id": items[idx].get("item_id"), "state": prev})
            elif selector != "r" and selector != "u":
                try: idx = int(selector)
                except: idx = -1
                if 0 <= idx < len(items):
                    curr = _normalize_item_state(items[idx].get("state"), items[idx].get("checked", False))
                    nxt = _next_state(curr)
                    items[idx]["state"] = nxt
                    items[idx]["checked"] = (nxt == _STATE_DONE)
                    history.append({"idx": idx, "prev_state": curr, "new_state": nxt})
                    changed = True
                    applied_shopping.append({"item_id": items[idx].get("item_id"), "state": nxt})
            
            if changed:
                list_state["items"] = items
                list_state["history"] = history[-50:]
                list_state["updated_at"] = datetime.now().isoformat()
                _edit_checklist_message(bot_token, list_state)
                lists[list_id] = list_state
            _answer_callback(bot_token, cq.get("id", ""), "Zaktualizowano")

        elif data.startswith(f"{_PROD_CALLBACK_PREFIX}|"):
            # Production stage logic
            parts = data.split("|")
            if len(parts) != 3: continue
            _, list_id, selector = parts
            list_state = lists.get(list_id)
            if not isinstance(list_state, dict):
                _answer_callback(bot_token, cq.get("id", ""), "Lista wygasla")
                continue
            
            items = list(list_state.get("items", []) or [])
            try: idx = int(selector)
            except: idx = -1
            
            if 0 <= idx < len(items):
                curr = items[idx].get("state", _STATE_TODO)
                nxt = _STATE_DONE if curr != _STATE_DONE else _STATE_TODO
                items[idx]["state"] = nxt
                list_state["items"] = items
                list_state["updated_at"] = datetime.now().isoformat()
                
                # Update visual representation for Telegram
                title = str(list_state.get("title", "Status Produkcji"))
                text_lines = [f"🏭 {title}", f"Aktualizacja: {datetime.now().strftime('%H:%M')}", "", "Statusy:"]
                for i, it in enumerate(items, start=1):
                    mark = "✅" if it["state"] == _STATE_DONE else "⚪"
                    text_lines.append(f"{i}. {mark} {it['label']}")
                
                payload = {
                    "chat_id": list_state["chat_id"],
                    "message_id": list_state["message_id"],
                    "text": "\n".join(text_lines),
                    "reply_markup": cq.get("message", {}).get("reply_markup")
                }
                _post_json(bot_token, "editMessageText", payload)
                
                applied_other.append({"type": "production", "order_id": items[idx].get("order_id"), "state": nxt})
                lists[list_id] = list_state
            _answer_callback(bot_token, cq.get("id", ""), "Status zmieniony")

        elif data.startswith(f"{_WORKTIME_CALLBACK_PREFIX}|"):
            # Attendance logic
            parts = data.split("|")
            if len(parts) == 3 and parts[1] == "punch":
                worker_id = parts[2]
                applied_other.append({"type": "worktime_punch", "worker_id": worker_id})
                _answer_callback(bot_token, cq.get("id", ""), "Odbito karte!")

    state["last_update_id"] = max_update_id
    state["lists"] = lists
    _save_state(state)
    return {
        "processed_updates": len(updates),
        "applied": applied_shopping,
        "applied_other": applied_other
    }


def collect_latest_item_checks() -> dict[str, bool]:
    """Return latest known checkbox state by shopping item_id across saved Telegram lists."""
    state = _load_state()
    lists = state.get("lists", {})
    if not isinstance(lists, dict):
        return {}

    merged: dict[str, tuple[str, bool]] = {}
    for list_state in lists.values():
        if not isinstance(list_state, dict):
            continue
        updated_at = str(list_state.get("updated_at", "") or "")
        for item in list(list_state.get("items", []) or []):
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("item_id", "") or "").strip()
            if not item_id:
                continue
            state = _normalize_item_state(item.get("state"), item.get("checked", False))
            checked = state == _STATE_DONE
            prev = merged.get(item_id)
            if prev is None or updated_at >= prev[0]:
                merged[item_id] = (updated_at, checked)

    return {item_id: checked for item_id, (_stamp, checked) in merged.items()}


def collect_latest_item_states() -> dict[str, str]:
    """Return latest known tri-state by shopping item_id: todo/partial/done."""
    state = _load_state()
    lists = state.get("lists", {})
    if not isinstance(lists, dict):
        return {}

    merged: dict[str, tuple[str, str]] = {}
    for list_state in lists.values():
        if not isinstance(list_state, dict):
            continue
        updated_at = str(list_state.get("updated_at", "") or "")
        for item in list(list_state.get("items", []) or []):
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("item_id", "") or "").strip()
            if not item_id:
                continue
            tri_state = _normalize_item_state(item.get("state"), item.get("checked", False))
            prev = merged.get(item_id)
            if prev is None or updated_at >= prev[0]:
                merged[item_id] = (updated_at, tri_state)

    return {item_id: tri_state for item_id, (_stamp, tri_state) in merged.items()}
