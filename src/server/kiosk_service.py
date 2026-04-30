from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from src.domain.work_time_models import WorkTimeEntryDef, new_entry_id
from src.domain.worker_models import WorkerDef
from src.domain.worker_qr import extract_worker_identifier, normalize_worker_id
from src.storage.work_time_session_store_json import WorkTimeSessionDef, WorkTimeSessionStoreJson
from src.storage.work_time_store_json import WorkTimeStoreJson
from src.storage.worker_store_json import WorkerStoreJson


def _now_iso(now: datetime) -> str:
    return now.isoformat(timespec="seconds")


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return float(default)


@dataclass(frozen=True)
class KioskResult:
    ok: bool
    message: str
    worker: dict | None = None
    session: dict | None = None
    entry: dict | None = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "message": self.message,
            "worker": self.worker,
            "session": self.session,
            "entry": self.entry,
        }


class KioskService:
    def __init__(
        self,
        worker_store: WorkerStoreJson | None = None,
        work_time_store: WorkTimeStoreJson | None = None,
        session_store: WorkTimeSessionStoreJson | None = None,
        now_func: Callable[[], datetime] | None = None,
    ) -> None:
        self._worker_store = worker_store if worker_store is not None else WorkerStoreJson()
        self._work_time_store = work_time_store if work_time_store is not None else WorkTimeStoreJson()
        self._session_store = session_store if session_store is not None else WorkTimeSessionStoreJson()
        self._now_func = now_func if now_func is not None else datetime.now

    def list_workers(self) -> list[dict]:
        sessions = {
            session.worker_id: session
            for session in self._session_store.list_sessions()
            if str(getattr(session, "worker_id", "") or "").strip()
        }
        workers = []
        for worker in self._worker_store.list_workers():
            worker_dict = self._worker_dict(worker)
            session = sessions.get(worker_dict["worker_id"])
            worker_dict["session"] = self._session_dict(session) if session is not None else None
            worker_dict["active"] = session is not None
            workers.append(worker_dict)
        return workers

    def resolve_scan(self, qr_text: str) -> KioskResult:
        worker = self._worker_store.resolve_identifier(qr_text)
        if worker is None:
            worker_id, worker_name = extract_worker_identifier(qr_text)
            if worker_id:
                return KioskResult(False, f"Nie znaleziono pracownika dla ID {worker_id}.")
            if worker_name:
                return KioskResult(False, f"Nie znaleziono pracownika: {worker_name}.")
            return KioskResult(False, "Nie rozpoznano QR.")

        worker_dict = self._worker_dict(worker)
        session = self._session_store.get(worker_dict["worker_id"])
        return KioskResult(
            True,
            f"Wybrano {worker_dict['name']}.",
            worker=worker_dict,
            session=self._session_dict(session) if session is not None else None,
        )

    def get_state(self, worker_id: str) -> KioskResult:
        worker = self._worker_store.get_by_worker_id(worker_id)
        if worker is None:
            return KioskResult(False, "Nie znaleziono pracownika.")
        session = self._session_store.get(normalize_worker_id(worker_id))
        return KioskResult(
            True,
            "OK",
            worker=self._worker_dict(worker),
            session=self._session_dict(session) if session is not None else None,
        )

    def perform_action(
        self,
        worker_id: str,
        action: str,
        work_type: str = "",
        project_code: str = "",
        order_id: str = "",
        workstation: str = "",
        note: str = "",
    ) -> KioskResult:
        worker = self._worker_store.get_by_worker_id(worker_id)
        if worker is None:
            return KioskResult(False, "Nie znaleziono pracownika.")

        worker_id_norm = normalize_worker_id(worker_id)
        action_norm = self._normalize_action(action)
        now = self._now_func()
        now_iso = _now_iso(now)
        worker_dict = self._worker_dict(worker)
        project_code_norm = str(project_code or "").strip()
        order_id_norm = str(order_id or "").strip()
        note_norm = str(note or "").strip()
        workstation_norm = self._normalize_workstation(workstation, fallback=work_type)
        work_type_norm = str(work_type or "Produkcja").strip() or "Produkcja"

        if action_norm == "start":
            current = self._session_store.get(worker_id_norm)
            if current is not None and current.started_at_iso and not current.break_started_at_iso:
                return KioskResult(True, "Sesja już jest aktywna.", worker=worker_dict, session=self._session_dict(current))
            session = WorkTimeSessionDef(
                worker_id=worker_id_norm,
                worker_name=worker_dict["name"],
                work_type=work_type_norm,
                project_code=project_code_norm,
                order_id=order_id_norm,
                workstation=workstation_norm,
                note=note_norm,
                started_at_iso=now_iso,
                break_total_minutes=0.0,
                last_action_iso=now_iso,
            )
            self._session_store.set(session)
            return KioskResult(True, "Start pracy zapisany.", worker=worker_dict, session=self._session_dict(session))

        session = self._session_store.get(worker_id_norm)
        if session is None:
            return KioskResult(False, "Brak aktywnej sesji.", worker=worker_dict)
        if project_code_norm:
            session.project_code = project_code_norm
        if order_id_norm:
            session.order_id = order_id_norm
        if workstation_norm:
            session.workstation = workstation_norm
        if note_norm:
            session.note = note_norm

        if action_norm == "break_start":
            if session.break_started_at_iso:
                return KioskResult(False, "Przerwa już trwa.", worker=worker_dict, session=self._session_dict(session))
            session.break_started_at_iso = now_iso
            session.last_action_iso = now_iso
            self._session_store.set(session)
            return KioskResult(True, "Przerwa rozpoczęta.", worker=worker_dict, session=self._session_dict(session))

        if action_norm == "break_end":
            if not session.break_started_at_iso:
                return KioskResult(False, "Przerwa nie jest aktywna.", worker=worker_dict, session=self._session_dict(session))
            try:
                started = datetime.fromisoformat(session.break_started_at_iso)
                session.break_total_minutes = float(session.break_total_minutes or 0.0) + max((now - started).total_seconds() / 60.0, 0.0)
            except ValueError:
                pass
            session.break_started_at_iso = ""
            session.last_action_iso = now_iso
            self._session_store.set(session)
            return KioskResult(True, "Przerwa zakończona.", worker=worker_dict, session=self._session_dict(session))

        if action_norm == "finish":
            return self._finish_session(worker, session, now)

        return KioskResult(False, f"Nieznana akcja: {action_norm}.", worker=worker_dict, session=self._session_dict(session))

    def _normalize_action(self, action: str) -> str:
        raw = str(action or "").strip().lower().replace("-", " ").replace("_", " ")
        raw = " ".join(raw.split())
        aliases = {
            "start": "start",
            "start pracy": "start",
            "rozpocznij": "start",
            "przerwa start": "break_start",
            "start przerwy": "break_start",
            "break start": "break_start",
            "breakstart": "break_start",
            "przerwa koniec": "break_end",
            "koniec przerwy": "break_end",
            "break end": "break_end",
            "breakend": "break_end",
            "koniec": "finish",
            "stop": "finish",
            "finish": "finish",
            "zakończ": "finish",
            "zakoncz": "finish",
            "end": "finish",
        }
        return aliases.get(raw, raw)

    def _finish_session(self, worker: WorkerDef, session: WorkTimeSessionDef, now: datetime) -> KioskResult:
        worker_dict = self._worker_dict(worker)
        if session.break_started_at_iso:
            try:
                started_break = datetime.fromisoformat(session.break_started_at_iso)
                session.break_total_minutes = float(session.break_total_minutes or 0.0) + max((now - started_break).total_seconds() / 60.0, 0.0)
            except ValueError:
                pass
            session.break_started_at_iso = ""

        try:
            started = datetime.fromisoformat(session.started_at_iso)
        except ValueError:
            started = now

        gross_minutes = max((now - started).total_seconds() / 60.0, 0.0)
        net_minutes = max(gross_minutes - float(session.break_total_minutes or 0.0), 0.0)

        entry = WorkTimeEntryDef(
            entry_id=new_entry_id(),
            day=int(now.day),
            date_iso=now.date().isoformat(),
            work_type=str(session.work_type or "Produkcja").strip() or "Produkcja",
            start_time=started.strftime("%H:%M"),
            end_time=now.strftime("%H:%M"),
            hours=round(net_minutes / 60.0, 2),
            overtime_hours=0.0,
            extra_pay=0.0,
            project_code=str(session.project_code or "").strip(),
            note=self._build_entry_note(session),
        )

        result = self._work_time_store.upsert_day_entry(worker_dict["name"], now.year, now.month, entry)
        if result.ok:
            self._session_store.delete(worker_dict["worker_id"])
            return KioskResult(True, result.message_pl, worker=worker_dict, entry=entry.to_dict())

        session.last_action_iso = _now_iso(now)
        self._session_store.set(session)
        return KioskResult(False, result.message_pl, worker=worker_dict, session=self._session_dict(session))

    def _worker_dict(self, worker: WorkerDef) -> dict:
        return {
            "name": str(getattr(worker, "name", "") or "").strip(),
            "worker_id": normalize_worker_id(str(getattr(worker, "worker_id", "") or "")),
            "pin_code": str(getattr(worker, "pin_code", "") or "").strip(),
            "role": str(getattr(worker, "role", "") or "").strip(),
            "hourly_rate": _safe_float(getattr(worker, "hourly_rate", 0.0)),
            "pay_mode": str(getattr(worker, "pay_mode", "") or "").strip(),
        }

    def _session_dict(self, session: WorkTimeSessionDef | None) -> dict | None:
        if session is None:
            return None
        return {
            "worker_id": str(getattr(session, "worker_id", "") or "").strip(),
            "worker_name": str(getattr(session, "worker_name", "") or "").strip(),
            "work_type": str(getattr(session, "work_type", "") or "").strip(),
            "project_code": str(getattr(session, "project_code", "") or "").strip(),
            "order_id": str(getattr(session, "order_id", "") or "").strip(),
            "workstation": str(getattr(session, "workstation", "") or "").strip(),
            "note": str(getattr(session, "note", "") or "").strip(),
            "started_at_iso": str(getattr(session, "started_at_iso", "") or "").strip(),
            "break_started_at_iso": str(getattr(session, "break_started_at_iso", "") or "").strip(),
            "break_total_minutes": float(getattr(session, "break_total_minutes", 0.0) or 0.0),
            "last_action_iso": str(getattr(session, "last_action_iso", "") or "").strip(),
        }

    def _normalize_workstation(self, workstation: str, *, fallback: str = "") -> str:
        raw = str(workstation or fallback or "").strip()
        if not raw:
            return ""
        token = raw.lower()
        aliases = {
            "cnc": "CNC",
            "oklejanie": "Oklejanie",
            "lakiernia": "Lakiernia",
            "montaz": "Montaz",
            "montaż": "Montaz",
            "biuro": "Biuro",
            "produkcja": "Produkcja",
        }
        return aliases.get(token, raw)

    def _build_entry_note(self, session: WorkTimeSessionDef) -> str:
        parts = ["Rejestracja z kiosku web"]
        if str(session.order_id or "").strip():
            parts.append(f"order_id={str(session.order_id).strip()}")
        if str(session.workstation or "").strip():
            parts.append(f"workstation={str(session.workstation).strip()}")
        if str(session.note or "").strip():
            parts.append(f"note={str(session.note).strip()}")
        return " | ".join(parts)
