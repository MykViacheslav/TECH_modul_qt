from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.core.finance_operations_followup_history_store import FinanceOperationsFollowupHistoryStore
from src.storage.data_paths import data_dir


OFFICE_STATUS_VALUES: dict[str, str] = {
    "nowe": "Nowe",
    "przekazane_do_fakturowania": "Przekazane do fakturowania",
    "zafakturowane": "Zafakturowane",
    "oplacone": "Oplacone",
    "rozliczone": "Rozliczone",
    "zamkniete_biurowo": "Zamkniete biurowo",
    "domkniete_finansowo": "Domkniete finansowo",
}

NEXT_ACTION_TYPE_VALUES: dict[str, str] = {
    "brak": "Brak",
    "kontakt_z_klientem": "Kontakt z klientem",
    "sprawdzenie_platnosci": "Sprawdzenie platnosci",
    "sprawdzenie_faktury": "Sprawdzenie faktury",
    "kontakt_wewnetrzny": "Kontakt wewnetrzny",
    "powrot_do_tematu": "Powrot do tematu",
    "inne": "Inne",
}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _parse_date_any(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    # ISO timestamp "2026-04-11T10:22:00"
    try:
        if "T" in text:
            return datetime.fromisoformat(text).date()
    except Exception:
        pass
    # ISO date "2026-04-11"
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _save_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
        fh.write("\n")
    os.replace(tmp, path)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return {"records": []}
    except Exception:
        return {"records": []}
    if not raw.strip():
        return {"records": []}
    try:
        payload = json.loads(raw)
    except Exception:
        return {"records": []}
    if not isinstance(payload, dict):
        return {"records": []}
    rows = payload.get("records", [])
    if not isinstance(rows, list):
        payload["records"] = []
    return payload


class FinanceOperationsFollowupStore:
    def __init__(
        self,
        path: Path | None = None,
        history_store: FinanceOperationsFollowupHistoryStore | None = None,
    ) -> None:
        base = data_dir()
        self._path = path if path is not None else base / "finance_operations_followup.json"
        self._history_store = history_store or FinanceOperationsFollowupHistoryStore()
        self._ensure_file()

    @property
    def history_store(self) -> FinanceOperationsFollowupHistoryStore:
        return self._history_store

    def _ensure_file(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            _save_json_atomic(self._path, {"records": []})

    def _read_payload(self) -> dict[str, Any]:
        return _load_json(self._path)

    def _write_payload(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = _now_iso()
        _save_json_atomic(self._path, payload)

    def list_records(self) -> list[dict]:
        payload = self._read_payload()
        rows = payload.get("records", [])
        if not isinstance(rows, list):
            return []
        out = [dict(x) for x in rows if isinstance(x, dict)]
        out.sort(key=lambda x: str(x.get("updated_at", "")), reverse=True)
        return out

    def get_record(self, point_id: str) -> dict | None:
        pid = str(point_id or "").strip()
        if not pid:
            return None
        for row in self.list_records():
            if str(row.get("point_id", "") or "").strip() == pid:
                return dict(row)
        return None

    def _upsert(self, record: dict[str, Any]) -> dict:
        payload = self._read_payload()
        rows = payload.get("records", [])
        if not isinstance(rows, list):
            rows = []
        pid = str(record.get("point_id", "") or "").strip()
        replaced = False
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            if str(row.get("point_id", "") or "").strip() == pid:
                rows[i] = dict(record)
                replaced = True
                break
        if not replaced:
            rows.append(dict(record))
        payload["records"] = rows
        self._write_payload(payload)
        return dict(record)

    def upsert_record(
        self,
        point_id: str,
        office_status: str,
        office_note: str = "",
        updated_by: str = "",
        invoice_number: str = "",
        invoice_date: str = "",
        linked_invoice_id: str = "",
        linked_invoice_source: str = "",
        invoice_status: str = "",
        payment_status: str = "",
        paid_amount: float = 0.0,
        payment_date: str = "",
        payment_method: str = "",
        payment_note: str = "",
        next_action_date: str | None = None,
        next_action_type: str | None = None,
        next_action_note: str | None = None,
        snoozed_until: str | None = None,
        needs_contact: bool | None = None,
        needs_check: bool | None = None,
        financially_closed: bool | None = None,
        log_history: bool = True,
    ) -> dict:
        pid = str(point_id or "").strip()
        if not pid:
            return {}
        status = str(office_status or "nowe").strip().lower()
        if status not in OFFICE_STATUS_VALUES:
            status = "nowe"
        existing = self.get_record(pid) or {}
        invoice_status_norm = str(invoice_status or "").strip().lower()
        if not invoice_status_norm:
            if status in {"przekazane_do_fakturowania", "zafakturowane"}:
                invoice_status_norm = status
            else:
                invoice_status_norm = str(existing.get("invoice_status", "brak") or "brak").strip().lower()
        if invoice_status_norm not in {"brak", "przekazane_do_fakturowania", "zafakturowane"}:
            invoice_status_norm = "brak"
        payment_status_norm = str(payment_status or "").strip().lower()
        if not payment_status_norm:
            if status == "oplacone":
                payment_status_norm = "oplacone"
            elif status == "zafakturowane":
                payment_status_norm = "oczekuje_na_platnosc"
            else:
                payment_status_norm = str(existing.get("payment_status", "brak") or "brak").strip().lower()
        if payment_status_norm not in {"brak", "oczekuje_na_platnosc", "oplacone"}:
            payment_status_norm = "brak"
        if next_action_type is None:
            next_action_type_norm = str(existing.get("next_action_type", "brak") or "brak").strip().lower()
        else:
            next_action_type_norm = str(next_action_type or "").strip().lower()
            if not next_action_type_norm:
                next_action_type_norm = "brak"
        if next_action_type_norm not in NEXT_ACTION_TYPE_VALUES:
            next_action_type_norm = "brak"
        paid_amount_value = float(paid_amount or existing.get("paid_amount", 0.0) or 0.0)
        if next_action_date is None:
            next_action_date_value = str(existing.get("next_action_date", "") or "").strip()
        else:
            next_action_date_value = str(next_action_date or "").strip()
        if next_action_note is None:
            next_action_note_value = str(existing.get("next_action_note", "") or "").strip()
        else:
            next_action_note_value = str(next_action_note or "").strip()
        if snoozed_until is None:
            snoozed_until_value = str(existing.get("snoozed_until", "") or "").strip()
        else:
            snoozed_until_value = str(snoozed_until or "").strip()
        needs_contact_value = bool(needs_contact) if needs_contact is not None else bool(existing.get("needs_contact", False))
        needs_check_value = bool(needs_check) if needs_check is not None else bool(existing.get("needs_check", False))
        closed_value = bool(financially_closed) if financially_closed is not None else bool(
            existing.get("financially_closed", False) or status == "domkniete_finansowo"
        )
        rec = {
            "point_id": pid,
            "office_status": status,
            "office_note": str(office_note or existing.get("office_note", "") or "").strip(),
            "updated_at": _now_iso(),
            "updated_by": str(updated_by or "").strip(),
            "sent_to_invoicing": status in {"przekazane_do_fakturowania", "zafakturowane", "oplacone", "rozliczone", "zamkniete_biurowo", "domkniete_finansowo"},
            "settled": status in {"rozliczone", "zamkniete_biurowo", "domkniete_finansowo"},
            "office_closed": status in {"zamkniete_biurowo", "domkniete_finansowo"},
            "invoice_status": invoice_status_norm,
            "invoice_number": str(invoice_number or existing.get("invoice_number", "") or "").strip(),
            "invoice_date": str(invoice_date or existing.get("invoice_date", "") or "").strip(),
            "linked_invoice_id": str(linked_invoice_id or existing.get("linked_invoice_id", "") or "").strip(),
            "linked_invoice_source": str(linked_invoice_source or existing.get("linked_invoice_source", "") or "").strip(),
            "payment_status": payment_status_norm,
            "paid_amount": paid_amount_value,
            "payment_date": str(payment_date or existing.get("payment_date", "") or "").strip(),
            "payment_method": str(payment_method or existing.get("payment_method", "") or "").strip(),
            "payment_note": str(payment_note or existing.get("payment_note", "") or "").strip(),
            "next_action_date": next_action_date_value,
            "next_action_type": next_action_type_norm,
            "next_action_note": next_action_note_value,
            "snoozed_until": snoozed_until_value,
            "needs_contact": needs_contact_value,
            "needs_check": needs_check_value,
            "financially_closed": closed_value,
        }
        updated = self._upsert(rec)
        if log_history:
            self._log_upsert_change(existing, updated, updated_by)
        return updated

    def mark_sent_to_invoicing(self, point_id: str, note: str = "", updated_by: str = "") -> dict:
        prev = self.get_record(point_id) or {}
        rec = self.upsert_record(
            point_id=point_id,
            office_status="przekazane_do_fakturowania",
            office_note=note,
            updated_by=updated_by,
            invoice_status="przekazane_do_fakturowania",
            log_history=False,
        )
        self._append_history("mark_sent_to_invoicing", prev, rec, note=note, updated_by=updated_by)
        return rec

    def mark_invoiced(
        self,
        point_id: str,
        invoice_number: str = "",
        invoice_date: str = "",
        linked_invoice_id: str = "",
        linked_invoice_source: str = "manual",
        note: str = "",
        updated_by: str = "",
    ) -> dict:
        prev = self.get_record(point_id) or {}
        rec = self.upsert_record(
            point_id=point_id,
            office_status="zafakturowane",
            office_note=note,
            updated_by=updated_by,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            linked_invoice_id=linked_invoice_id,
            linked_invoice_source=linked_invoice_source,
            invoice_status="zafakturowane",
            log_history=False,
        )
        self._append_history("mark_invoiced", prev, rec, note=note, updated_by=updated_by)
        return rec

    def mark_settled(self, point_id: str, note: str = "", updated_by: str = "") -> dict:
        prev = self.get_record(point_id) or {}
        rec = self.upsert_record(
            point_id=point_id,
            office_status="rozliczone",
            office_note=note,
            updated_by=updated_by,
            log_history=False,
        )
        self._append_history("mark_settled", prev, rec, note=note, updated_by=updated_by)
        return rec

    def mark_office_closed(self, point_id: str, note: str = "", updated_by: str = "") -> dict:
        prev = self.get_record(point_id) or {}
        rec = self.upsert_record(
            point_id=point_id,
            office_status="zamkniete_biurowo",
            office_note=note,
            updated_by=updated_by,
            log_history=False,
        )
        self._append_history("mark_office_closed", prev, rec, note=note, updated_by=updated_by)
        return rec

    def mark_paid(
        self,
        point_id: str,
        paid_amount: float = 0.0,
        payment_date: str = "",
        payment_method: str = "",
        note: str = "",
        updated_by: str = "",
    ) -> dict:
        prev = self.get_record(point_id) or {}
        rec = self.upsert_record(
            point_id=point_id,
            office_status="oplacone",
            office_note=note,
            updated_by=updated_by,
            payment_status="oplacone",
            paid_amount=paid_amount,
            payment_date=payment_date,
            payment_method=payment_method,
            payment_note=note,
            log_history=False,
        )
        self._append_history("mark_paid", prev, rec, note=note, updated_by=updated_by)
        return rec

    def mark_financially_closed(self, point_id: str, note: str = "", updated_by: str = "") -> dict:
        prev = self.get_record(point_id) or {}
        rec = self.upsert_record(
            point_id=point_id,
            office_status="domkniete_finansowo",
            office_note=note,
            updated_by=updated_by,
            financially_closed=True,
            log_history=False,
        )
        self._append_history("mark_financially_closed", prev, rec, note=note, updated_by=updated_by)
        return rec

    def set_next_action(
        self,
        point_id: str,
        next_action_date: str = "",
        next_action_type: str = "brak",
        next_action_note: str = "",
        needs_contact: bool = False,
        needs_check: bool = False,
        updated_by: str = "",
    ) -> dict:
        prev = self.get_record(point_id) or {}
        rec = self.upsert_record(
            point_id=point_id,
            office_status=str(prev.get("office_status", "nowe") or "nowe"),
            office_note=str(prev.get("office_note", "") or ""),
            updated_by=updated_by,
            invoice_number=str(prev.get("invoice_number", "") or ""),
            invoice_date=str(prev.get("invoice_date", "") or ""),
            linked_invoice_id=str(prev.get("linked_invoice_id", "") or ""),
            linked_invoice_source=str(prev.get("linked_invoice_source", "") or ""),
            invoice_status=str(prev.get("invoice_status", "") or ""),
            payment_status=str(prev.get("payment_status", "") or ""),
            paid_amount=float(prev.get("paid_amount", 0.0) or 0.0),
            payment_date=str(prev.get("payment_date", "") or ""),
            payment_method=str(prev.get("payment_method", "") or ""),
            payment_note=str(prev.get("payment_note", "") or ""),
            next_action_date=next_action_date,
            next_action_type=next_action_type,
            next_action_note=next_action_note,
            needs_contact=needs_contact,
            needs_check=needs_check,
            snoozed_until=str(prev.get("snoozed_until", "") or ""),
            financially_closed=bool(prev.get("financially_closed", False)),
            log_history=False,
        )
        self._append_history("set_next_action", prev, rec, note=next_action_note, updated_by=updated_by)
        return rec

    def snooze_record(
        self,
        point_id: str,
        snoozed_until: str,
        note: str = "",
        updated_by: str = "",
    ) -> dict:
        prev = self.get_record(point_id) or {}
        rec = self.upsert_record(
            point_id=point_id,
            office_status=str(prev.get("office_status", "nowe") or "nowe"),
            office_note=note or str(prev.get("office_note", "") or ""),
            updated_by=updated_by,
            invoice_number=str(prev.get("invoice_number", "") or ""),
            invoice_date=str(prev.get("invoice_date", "") or ""),
            linked_invoice_id=str(prev.get("linked_invoice_id", "") or ""),
            linked_invoice_source=str(prev.get("linked_invoice_source", "") or ""),
            invoice_status=str(prev.get("invoice_status", "") or ""),
            payment_status=str(prev.get("payment_status", "") or ""),
            paid_amount=float(prev.get("paid_amount", 0.0) or 0.0),
            payment_date=str(prev.get("payment_date", "") or ""),
            payment_method=str(prev.get("payment_method", "") or ""),
            payment_note=str(prev.get("payment_note", "") or ""),
            next_action_date=str(prev.get("next_action_date", "") or ""),
            next_action_type=str(prev.get("next_action_type", "brak") or "brak"),
            next_action_note=str(prev.get("next_action_note", "") or ""),
            needs_contact=bool(prev.get("needs_contact", False)),
            needs_check=bool(prev.get("needs_check", False)),
            snoozed_until=snoozed_until,
            financially_closed=bool(prev.get("financially_closed", False)),
            log_history=False,
        )
        self._append_history("snooze_record", prev, rec, note=note or snoozed_until, updated_by=updated_by)
        return rec

    def clear_snooze(self, point_id: str, updated_by: str = "") -> dict:
        prev = self.get_record(point_id) or {}
        rec = self.upsert_record(
            point_id=point_id,
            office_status=str(prev.get("office_status", "nowe") or "nowe"),
            office_note=str(prev.get("office_note", "") or ""),
            updated_by=updated_by,
            invoice_number=str(prev.get("invoice_number", "") or ""),
            invoice_date=str(prev.get("invoice_date", "") or ""),
            linked_invoice_id=str(prev.get("linked_invoice_id", "") or ""),
            linked_invoice_source=str(prev.get("linked_invoice_source", "") or ""),
            invoice_status=str(prev.get("invoice_status", "") or ""),
            payment_status=str(prev.get("payment_status", "") or ""),
            paid_amount=float(prev.get("paid_amount", 0.0) or 0.0),
            payment_date=str(prev.get("payment_date", "") or ""),
            payment_method=str(prev.get("payment_method", "") or ""),
            payment_note=str(prev.get("payment_note", "") or ""),
            next_action_date=str(prev.get("next_action_date", "") or ""),
            next_action_type=str(prev.get("next_action_type", "brak") or "brak"),
            next_action_note=str(prev.get("next_action_note", "") or ""),
            needs_contact=bool(prev.get("needs_contact", False)),
            needs_check=bool(prev.get("needs_check", False)),
            snoozed_until="",
            financially_closed=bool(prev.get("financially_closed", False)),
            log_history=False,
        )
        self._append_history("clear_snooze", prev, rec, note="usunieto odlozenie", updated_by=updated_by)
        return rec

    def _append_history(
        self,
        action_type: str,
        old: dict[str, Any],
        new: dict[str, Any],
        note: str = "",
        updated_by: str = "",
    ) -> None:
        pid = str(new.get("point_id", "") or old.get("point_id", "") or "").strip()
        if not pid:
            return
        self._history_store.append_record(
            point_id=pid,
            action_type=action_type,
            created_by=str(updated_by or new.get("updated_by", "") or "").strip(),
            old_office_status=str(old.get("office_status", "") or ""),
            new_office_status=str(new.get("office_status", "") or ""),
            old_invoice_status=str(old.get("invoice_status", "") or ""),
            new_invoice_status=str(new.get("invoice_status", "") or ""),
            old_payment_status=str(old.get("payment_status", "") or ""),
            new_payment_status=str(new.get("payment_status", "") or ""),
            invoice_number=str(new.get("invoice_number", "") or ""),
            invoice_date=str(new.get("invoice_date", "") or ""),
            paid_amount=float(new.get("paid_amount", 0.0) or 0.0),
            payment_date=str(new.get("payment_date", "") or ""),
            payment_method=str(new.get("payment_method", "") or ""),
            note=str(note or new.get("office_note", "") or "").strip(),
        )

    def _log_upsert_change(self, old: dict[str, Any], new: dict[str, Any], updated_by: str) -> None:
        pid = str(new.get("point_id", "") or old.get("point_id", "") or "").strip()
        if not pid:
            return
        office_note_changed = str(old.get("office_note", "") or "") != str(new.get("office_note", "") or "")
        invoice_changed = any(
            str(old.get(key, "") or "") != str(new.get(key, "") or "")
            for key in ("invoice_number", "invoice_date", "linked_invoice_id", "linked_invoice_source")
        )
        payment_changed = (
            str(old.get("payment_status", "") or "") != str(new.get("payment_status", "") or "")
            or float(old.get("paid_amount", 0.0) or 0.0) != float(new.get("paid_amount", 0.0) or 0.0)
            or str(old.get("payment_date", "") or "") != str(new.get("payment_date", "") or "")
            or str(old.get("payment_method", "") or "") != str(new.get("payment_method", "") or "")
            or str(old.get("payment_note", "") or "") != str(new.get("payment_note", "") or "")
        )
        next_action_changed = any(
            str(old.get(key, "") or "") != str(new.get(key, "") or "")
            for key in ("next_action_date", "next_action_type", "next_action_note", "needs_contact", "needs_check")
        )
        snooze_changed = str(old.get("snoozed_until", "") or "") != str(new.get("snoozed_until", "") or "")
        if invoice_changed:
            self._append_history("update_invoice_data", old, new, note=str(new.get("office_note", "") or ""), updated_by=updated_by)
        if payment_changed:
            self._append_history("update_payment_data", old, new, note=str(new.get("payment_note", "") or ""), updated_by=updated_by)
        if next_action_changed:
            self._append_history("set_next_action", old, new, note=str(new.get("next_action_note", "") or ""), updated_by=updated_by)
        if snooze_changed:
            if str(new.get("snoozed_until", "") or "").strip():
                self._append_history("snooze_record", old, new, note=str(new.get("snoozed_until", "") or ""), updated_by=updated_by)
            else:
                self._append_history("clear_snooze", old, new, note="usunieto odlozenie", updated_by=updated_by)
        if office_note_changed and not invoice_changed and not payment_changed:
            self._append_history("save_office_note", old, new, note=str(new.get("office_note", "") or ""), updated_by=updated_by)

    def get_last_activity_at(self, point_id: str) -> str:
        pid = str(point_id or "").strip()
        if not pid:
            return ""
        hist = self._history_store.list_for_point(pid)
        if hist:
            return str(hist[0].get("created_at", "") or "")
        rec = self.get_record(pid) or {}
        return str(rec.get("updated_at", "") or "")

    def get_days_since_last_activity(self, point_id: str, today: date | None = None) -> int:
        pid = str(point_id or "").strip()
        if not pid:
            return 0
        today_d = today or date.today()
        last = _parse_date_any(self.get_last_activity_at(pid))
        if last is None:
            return 0
        delta = (today_d - last).days
        return max(0, int(delta))

    def compute_office_priority(self, row: dict, today: date | None = None) -> str:
        today_d = today or date.today()
        days = int(row.get("days_since_last_activity", 0) or 0)
        if days <= 0:
            pid = str(row.get("point_id", "") or "")
            days = self.get_days_since_last_activity(pid, today=today_d)
        office_status = str(row.get("office_status", "nowe") or "nowe")
        blocks_payment = bool(row.get("blocks_payment", False)) or float(row.get("estimated_payment_unlock", 0.0) or 0.0) > 0
        amount = float(row.get("estimated_payment_unlock", 0.0) or 0.0)
        if office_status == "domkniete_finansowo":
            return "niski"
        if blocks_payment and amount >= 5000.0 and days > 7:
            return "krytyczny"
        if office_status == "przekazane_do_fakturowania" and days > 7:
            return "krytyczny"
        if days > 14 and office_status not in {"domkniete_finansowo", "zamkniete_biurowo"}:
            return "krytyczny"
        if (
            bool(row.get("ready_to_invoice", False))
            or bool(row.get("requires_settlement", False))
            or bool(row.get("requires_confirmation", False))
            or days > 7
            or office_status in {"przekazane_do_fakturowania", "zafakturowane"}
        ):
            return "wysoki"
        if office_status in {"oplacone", "rozliczone", "zamkniete_biurowo"} and days <= 3:
            return "niski"
        return "normalny"

    def compute_action_flags(self, row: dict, today: date | None = None) -> dict[str, Any]:
        today_d = today or date.today()
        office_status = str(row.get("office_status", "nowe") or "nowe")
        is_closed = bool(row.get("financially_closed", False)) or office_status == "domkniete_finansowo"
        next_action_date = str(row.get("next_action_date", "") or "").strip()
        next_action_type = str(row.get("next_action_type", "brak") or "brak").strip().lower()
        snoozed_until = str(row.get("snoozed_until", "") or "").strip()
        next_date = _parse_date_any(next_action_date)
        snooze_date = _parse_date_any(snoozed_until)
        is_snoozed = bool(snooze_date is not None and today_d < snooze_date and not is_closed)
        action_due_today = bool(next_date is not None and next_date <= today_d and not is_closed and not is_snoozed)
        action_overdue = bool(next_date is not None and next_date < today_d and not is_closed and not is_snoozed)
        action_type_label = NEXT_ACTION_TYPE_VALUES.get(next_action_type, next_action_type)
        if next_date is not None and next_action_type != "brak":
            next_action_label = f"{action_type_label} - {next_date.isoformat()}"
        elif next_date is not None:
            next_action_label = f"{next_date.isoformat()}"
        elif next_action_type != "brak":
            next_action_label = action_type_label
        else:
            next_action_label = "Brak"
        return {
            "action_due_today": action_due_today,
            "action_overdue": action_overdue,
            "is_snoozed": is_snoozed,
            "next_action_label": next_action_label,
        }

    def build_office_queue(self, rows: list[dict], today: date | None = None) -> list[dict]:
        today_d = today or date.today()
        out: list[dict] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            point_id = str(item.get("point_id", "") or "")
            office_status = str(item.get("office_status", "nowe") or "nowe")
            last_activity = self.get_last_activity_at(point_id)
            days_since = self.get_days_since_last_activity(point_id, today=today_d)
            if days_since <= 0:
                # fallback for imported rows without follow-up history/state
                fallback = _parse_date_any(str(item.get("last_visit_at", "") or ""))
                if fallback is not None:
                    days_since = max(0, (today_d - fallback).days)
                    last_activity = str(item.get("last_visit_at", "") or "")
            is_closed = bool(item.get("financially_closed", False)) or office_status == "domkniete_finansowo"
            is_stale = (not is_closed) and days_since > 3
            action_flags = self.compute_action_flags(item, today=today_d)
            needs_attention_today = (
                office_status == "nowe"
                or (office_status == "przekazane_do_fakturowania" and days_since > 3)
                or (office_status == "zafakturowane" and str(item.get("payment_status", "brak")) != "oplacone")
                or (office_status == "oplacone" and not is_closed)
                or is_stale
            )
            if bool(action_flags.get("is_snoozed", False)):
                needs_attention_today = False
            if bool(action_flags.get("action_due_today", False)):
                needs_attention_today = True
            item["last_activity_at"] = last_activity
            item["days_since_last_activity"] = int(days_since)
            item["is_stale"] = bool(is_stale)
            item["needs_attention_today"] = bool(needs_attention_today)
            item.update(action_flags)
            item["office_priority"] = self.compute_office_priority(item, today=today_d)
            if item["office_priority"] == "krytyczny":
                reason = "Wysoka kwota i brak reakcji lub dlugi zastoj."
            elif item["office_priority"] == "wysoki":
                reason = "Wymaga obslugi biurowej lub dlugo czeka."
            elif item["office_priority"] == "niski":
                reason = "Temat blisko finalnego domkniecia."
            else:
                reason = "Standardowa obsluga."
            item["office_priority_reason"] = reason
            out.append(item)

        priority_rank = {"krytyczny": 3, "wysoki": 2, "normalny": 1, "niski": 0}

        def _sort_key(x: dict) -> tuple:
            return (
                1 if bool(x.get("action_overdue", False)) else 0,
                1 if bool(x.get("action_due_today", False)) else 0,
                1 if bool(x.get("needs_attention_today", False)) else 0,
                priority_rank.get(str(x.get("office_priority", "normalny")), 1),
                int(x.get("days_since_last_activity", 0) or 0),
                float(x.get("estimated_payment_unlock", 0.0) or 0.0),
            )

        out.sort(key=_sort_key, reverse=True)
        return out

    def get_agenda_buckets(
        self,
        rows: list[dict] | None = None,
        today: date | None = None,
    ) -> dict[str, list[dict]]:
        today_d = today or date.today()
        tomorrow = date.fromordinal(today_d.toordinal() + 1)
        queue_rows = self.build_office_queue(rows or [], today=today_d)
        buckets: dict[str, list[dict]] = {
            "today": [],
            "tomorrow": [],
            "overdue": [],
            "snoozed": [],
        }
        for row in queue_rows:
            office_status = str(row.get("office_status", "nowe") or "nowe")
            is_closed = bool(row.get("financially_closed", False)) or office_status == "domkniete_finansowo"
            if bool(row.get("is_snoozed", False)):
                buckets["snoozed"].append(row)
                continue
            if is_closed:
                continue
            next_date = _parse_date_any(str(row.get("next_action_date", "") or ""))
            if bool(row.get("action_overdue", False)):
                buckets["overdue"].append(row)
            if next_date is not None and next_date == tomorrow:
                buckets["tomorrow"].append(row)
            if bool(row.get("action_due_today", False)):
                buckets["today"].append(row)

        priority_rank = {"krytyczny": 3, "wysoki": 2, "normalny": 1, "niski": 0}

        def _bucket_sort(x: dict) -> tuple:
            return (
                priority_rank.get(str(x.get("office_priority", "normalny")), 1),
                float(x.get("estimated_payment_unlock", 0.0) or 0.0),
                int(x.get("days_since_last_activity", 0) or 0),
            )

        for key in buckets:
            buckets[key].sort(key=_bucket_sort, reverse=True)
        return buckets

    def merge_with_operations_rows(self, rows: list[dict]) -> list[dict]:
        records_by_point = {
            str(x.get("point_id", "") or "").strip(): dict(x)
            for x in self.list_records()
            if str(x.get("point_id", "") or "").strip()
        }
        out: list[dict] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            merged = dict(row)
            pid = str(merged.get("point_id", "") or "").strip()
            follow = records_by_point.get(pid, {})
            office_status = str(follow.get("office_status", "nowe") or "nowe").strip().lower()
            if office_status not in OFFICE_STATUS_VALUES:
                office_status = "nowe"
            merged["office_status"] = office_status
            merged["office_note"] = str(follow.get("office_note", "") or "")
            merged["office_updated_at"] = str(follow.get("updated_at", "") or "")
            merged["office_updated_by"] = str(follow.get("updated_by", "") or "")
            merged["sent_to_invoicing"] = bool(follow.get("sent_to_invoicing", office_status in {"przekazane_do_fakturowania", "zafakturowane", "oplacone", "rozliczone", "zamkniete_biurowo", "domkniete_finansowo"}))
            merged["settled"] = bool(follow.get("settled", office_status in {"rozliczone", "zamkniete_biurowo", "domkniete_finansowo"}))
            merged["office_closed"] = bool(follow.get("office_closed", office_status in {"zamkniete_biurowo", "domkniete_finansowo"}))
            merged["invoice_status"] = str(follow.get("invoice_status", "brak") or "brak")
            merged["invoice_number"] = str(follow.get("invoice_number", "") or "")
            merged["invoice_date"] = str(follow.get("invoice_date", "") or "")
            merged["linked_invoice_id"] = str(follow.get("linked_invoice_id", "") or "")
            merged["linked_invoice_source"] = str(follow.get("linked_invoice_source", "") or "")
            merged["payment_status"] = str(follow.get("payment_status", "brak") or "brak")
            merged["paid_amount"] = float(follow.get("paid_amount", 0.0) or 0.0)
            merged["payment_date"] = str(follow.get("payment_date", "") or "")
            merged["payment_method"] = str(follow.get("payment_method", "") or "")
            merged["payment_note"] = str(follow.get("payment_note", "") or "")
            merged["next_action_date"] = str(follow.get("next_action_date", "") or "")
            merged["next_action_type"] = str(follow.get("next_action_type", "brak") or "brak")
            merged["next_action_note"] = str(follow.get("next_action_note", "") or "")
            merged["snoozed_until"] = str(follow.get("snoozed_until", "") or "")
            merged["needs_contact"] = bool(follow.get("needs_contact", False))
            merged["needs_check"] = bool(follow.get("needs_check", False))
            merged["financially_closed"] = bool(follow.get("financially_closed", office_status == "domkniete_finansowo"))
            out.append(merged)
        return out
