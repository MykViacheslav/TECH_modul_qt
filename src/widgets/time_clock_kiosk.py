from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from PyQt6.QtCore import QDateTime, QTimer, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.domain.permissions import normalize_role
from src.domain.work_time_models import WorkTimeEntryDef
from src.domain.worker_models import WorkerDef
from src.domain.worker_qr import extract_worker_identifier, normalize_worker_id
from src.storage.work_time_session_store_json import WorkTimeSessionDef, WorkTimeSessionStoreJson
from src.storage.work_time_store_json import WorkTimeStoreJson
from src.storage.worker_store_json import WorkerStoreJson
from src.widgets.qr_utils import qr_pixmap_from_text, worker_qr_payload
from src.widgets.worker_qr_dialog import WorkerQrDialog


WORK_TYPE_OPTIONS = (
    "Produkcja",
    "Montaż",
    "Praca na miejscu",
    "Lakiernia",
    "Delegacja / wyjazd",
    "Projekt / wycena",
    "Zakup materiałów",
    "BHP / szkolenie",
    "Inne",
)


class TimeClockKioskWindow(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        worker_store: WorkerStoreJson | None = None,
        work_time_store: WorkTimeStoreJson | None = None,
        session_store: WorkTimeSessionStoreJson | None = None,
    ) -> None:
        super().__init__(parent)
        self._worker_store = worker_store if worker_store is not None else WorkerStoreJson()
        self._work_time_store = work_time_store if work_time_store is not None else WorkTimeStoreJson()
        self._session_store = session_store if session_store is not None else WorkTimeSessionStoreJson()

        self._current_worker: WorkerDef | None = None
        self._current_session: WorkTimeSessionDef | None = None
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start()

        self.setWindowTitle("TECH_modul - Rejestracja czasu")
        self.setMinimumSize(1100, 760)
        self._build_ui()
        self._tick_clock()
        self._refresh_session_ui()
        self.ed_scan.setFocus()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)

        title_box = QVBoxLayout()
        title = QLabel("REJESTRACJA CZASU", self)
        title.setStyleSheet("font-size: 28px; font-weight: 900; color:#10233f;")
        self.lab_clock = QLabel("", self)
        self.lab_clock.setStyleSheet("font-size: 16px; font-weight: 700; color:#334155;")
        self.lab_hint = QLabel("Skan QR pracownika i wybierz akcję.", self)
        self.lab_hint.setStyleSheet("color:#64748b; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(self.lab_clock)
        title_box.addWidget(self.lab_hint)
        header.addLayout(title_box, 2)

        self.lab_connection = QLabel("Gotowe", self)
        self.lab_connection.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lab_connection.setStyleSheet(
            "background:#ecfdf5; color:#166534; border:1px solid #bbf7d0; border-radius:14px; padding:12px 16px; font-weight:800;"
        )
        self.lab_connection.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        header.addWidget(self.lab_connection, 0, Qt.AlignmentFlag.AlignRight)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(16)

        left = self._panel("Skan QR", "Ustaw kartę w polu skanującego terminala.")
        left_layout = left.layout()
        assert isinstance(left_layout, QVBoxLayout)

        self.ed_scan = QLineEdit(self)
        self.ed_scan.setPlaceholderText("Skan QR lub wpisz ID pracownika i naciśnij Enter")
        self.ed_scan.setClearButtonEnabled(True)
        self.ed_scan.setMinimumHeight(52)
        self.ed_scan.setStyleSheet(
            "QLineEdit { font-size: 18px; padding: 10px 14px; border-radius: 14px; border: 1px solid #cbd5e1; background: #ffffff; }"
        )
        self.ed_scan.returnPressed.connect(self._on_scan_entered)
        left_layout.addWidget(self.ed_scan)

        self.lab_scan_status = QLabel("Czekam na skan...", self)
        self.lab_scan_status.setWordWrap(True)
        self.lab_scan_status.setStyleSheet("color:#475569; font-size: 14px; font-weight: 600;")
        left_layout.addWidget(self.lab_scan_status)

        self.lab_worker_name = QLabel("Brak pracownika", self)
        self.lab_worker_name.setStyleSheet("font-size: 24px; font-weight: 900; color:#0f172a;")
        left_layout.addWidget(self.lab_worker_name)

        self.lab_worker_meta = QLabel("ID: - | Rola: -", self)
        self.lab_worker_meta.setStyleSheet("color:#64748b; font-size: 13px;")
        left_layout.addWidget(self.lab_worker_meta)

        self.lab_worker_qr = QLabel(self)
        self.lab_worker_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lab_worker_qr.setMinimumHeight(280)
        self.lab_worker_qr.setStyleSheet("background:#ffffff; border:1px solid #dbe4ee; border-radius:18px;")
        left_layout.addWidget(self.lab_worker_qr, 1)

        self.btn_show_qr = QPushButton("Pokaż QR pracownika", self)
        self.btn_show_qr.setMinimumHeight(46)
        self.btn_show_qr.clicked.connect(self._open_worker_qr_dialog)
        left_layout.addWidget(self.btn_show_qr)

        self.btn_clear = QPushButton("Wyczyść wybór", self)
        self.btn_clear.setMinimumHeight(46)
        self.btn_clear.clicked.connect(self._clear_selected_worker)
        left_layout.addWidget(self.btn_clear)

        body.addWidget(left, 1)

        right = self._panel("Akcje", "Wybierz rodzaj pracy i odbij odpowiednią akcję.")
        right_layout = right.layout()
        assert isinstance(right_layout, QVBoxLayout)

        form_row = QHBoxLayout()
        type_label = QLabel("Rodzaj pracy", self)
        type_label.setStyleSheet("font-weight:700; color:#0f172a;")
        self.cb_work_type = QComboBox(self)
        for item in WORK_TYPE_OPTIONS:
            self.cb_work_type.addItem(item)
        self.cb_work_type.setMinimumHeight(44)
        self.cb_work_type.setCurrentText("Produkcja")
        form_row.addWidget(type_label)
        form_row.addWidget(self.cb_work_type, 1)
        right_layout.addLayout(form_row)

        self.btn_start = self._action_button("Start pracy", "#0f766e")
        self.btn_break_start = self._action_button("Przerwa start", "#b45309")
        self.btn_break_end = self._action_button("Przerwa koniec", "#2563eb")
        self.btn_finish = self._action_button("Koniec pracy", "#be123c")
        self.btn_start.clicked.connect(self._start_session)
        self.btn_break_start.clicked.connect(self._start_break)
        self.btn_break_end.clicked.connect(self._end_break)
        self.btn_finish.clicked.connect(self._finish_session)

        right_layout.addWidget(self.btn_start)
        right_layout.addWidget(self.btn_break_start)
        right_layout.addWidget(self.btn_break_end)
        right_layout.addWidget(self.btn_finish)

        summary_box = self._info_box("Status")
        summary_layout = summary_box.layout()
        assert isinstance(summary_layout, QVBoxLayout)
        self.lab_session_state = QLabel("Brak aktywnej sesji.", self)
        self.lab_session_state.setWordWrap(True)
        self.lab_session_state.setStyleSheet("font-size: 16px; font-weight: 700; color:#0f172a;")
        self.lab_session_details = QLabel("", self)
        self.lab_session_details.setWordWrap(True)
        self.lab_session_details.setStyleSheet("color:#475569; font-size: 13px;")
        summary_layout.addWidget(self.lab_session_state)
        summary_layout.addWidget(self.lab_session_details)
        right_layout.addWidget(summary_box)

        tip = QLabel(
            "Wskazówka: skaner QR zwykle działa jak klawiatura. Po skanie kodu aplikacja sama go przyjmie po Enterze.",
            self,
        )
        tip.setWordWrap(True)
        tip.setStyleSheet("color:#64748b; font-size: 12px;")
        right_layout.addWidget(tip)

        right_layout.addStretch(1)
        body.addWidget(right, 1)

        root.addLayout(body, 1)

        footer = QLabel(
            "Dane zapisują się do istniejącego modułu Czas pracy. Jeden wpis dzienny może sumować kilka wejść i wyjść.",
            self,
        )
        footer.setWordWrap(True)
        footer.setStyleSheet(
            "background:#f8fafc; border:1px solid #e2e8f0; border-radius:14px; padding:12px 14px; color:#475569;"
        )
        root.addWidget(footer)

    def _panel(self, title: str, subtitle: str) -> QFrame:
        frame = QFrame(self)
        frame.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #dbe4ee; border-radius:20px; }"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        lab_title = QLabel(title, frame)
        lab_title.setStyleSheet("font-size: 18px; font-weight: 900; color:#122033;")
        lab_subtitle = QLabel(subtitle, frame)
        lab_subtitle.setWordWrap(True)
        lab_subtitle.setStyleSheet("color:#64748b; font-size: 12px;")
        layout.addWidget(lab_title)
        layout.addWidget(lab_subtitle)
        return frame

    def _info_box(self, title: str) -> QFrame:
        frame = QFrame(self)
        frame.setStyleSheet(
            "QFrame { background:#f8fafc; border:1px solid #dbe4ee; border-radius:16px; }"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        lab_title = QLabel(title, frame)
        lab_title.setStyleSheet("font-size: 14px; font-weight: 800; color:#122033;")
        layout.addWidget(lab_title)
        return frame

    def _action_button(self, title: str, accent: str) -> QPushButton:
        btn = QPushButton(title, self)
        btn.setMinimumHeight(54)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{"
            f"border: none;"
            f"border-radius: 16px;"
            f"background: {accent};"
            f"color: #ffffff;"
            f"font-size: 16px;"
            f"font-weight: 900;"
            f"text-align: left;"
            f"padding: 0 16px;"
            f"}}"
            f"QPushButton:hover {{ background: {self._hover_color(accent)}; }}"
            f"QPushButton:disabled {{ background:#cbd5e1; color:#ffffff; }}"
        )
        return btn

    def _hover_color(self, color: str) -> str:
        mapping = {
            "#0f766e": "#115e59",
            "#b45309": "#92400e",
            "#2563eb": "#1d4ed8",
            "#be123c": "#9f1239",
        }
        return mapping.get(color, color)

    def _tick_clock(self) -> None:
        self.lab_clock.setText(QDateTime.currentDateTime().toString("dddd, dd.MM.yyyy  HH:mm:ss"))

    def _on_scan_entered(self) -> None:
        raw = self.ed_scan.text().strip()
        if not raw:
            return
        worker = self._worker_store.resolve_identifier(raw)
        if worker is None:
            worker_id, worker_name = extract_worker_identifier(raw)
            if worker_id:
                self._set_status(f"Nie znaleziono pracownika dla ID {worker_id}.", ok=False)
            elif worker_name:
                self._set_status(f"Nie znaleziono pracownika: {worker_name}.", ok=False)
            else:
                self._set_status("Nie rozpoznano kodu QR.", ok=False)
            self.lab_worker_name.setText("Brak pracownika")
            self.lab_worker_meta.setText("ID: - | Rola: -")
            self.lab_worker_qr.setPixmap(qr_pixmap_from_text("Brak pracownika", size=280))
            self._current_worker = None
            self._current_session = None
            self._refresh_session_ui()
            return

        self._current_worker = worker
        worker_id = str(getattr(worker, "worker_id", "") or "").strip()
        worker_name = str(getattr(worker, "name", "") or "").strip()
        role = normalize_role(str(getattr(worker, "role", "") or ""))
        payload = worker_qr_payload(worker_id, worker_name)
        self.lab_worker_name.setText(worker_name or "Pracownik")
        self.lab_worker_meta.setText(f"ID: {worker_id or '-'} | Rola: {role or '-'}")
        self.lab_worker_qr.setPixmap(qr_pixmap_from_text(payload, size=280))

        self._current_session = self._session_store.get(worker_id)
        if self._current_session is None:
            self._set_status(f"Wybrano {worker_name}.", ok=True)
        else:
            self._set_status(f"Wybrano {worker_name}. Sesja już istnieje.", ok=True)
        self._refresh_session_ui()
        self.ed_scan.selectAll()

    def _clear_selected_worker(self) -> None:
        self._current_worker = None
        self._current_session = None
        self.ed_scan.clear()
        self.lab_worker_name.setText("Brak pracownika")
        self.lab_worker_meta.setText("ID: - | Rola: -")
        self.lab_worker_qr.setPixmap(qr_pixmap_from_text("Skan QR pracownika", size=280))
        self._set_status("Wyczyszczono wybór.", ok=True)
        self.ed_scan.setFocus()
        self._refresh_session_ui()

    def _selected_work_type(self) -> str:
        return self.cb_work_type.currentText().strip() or "Produkcja"

    def _require_worker(self) -> WorkerDef | None:
        if self._current_worker is None:
            self._set_status("Najpierw zeskanuj pracownika.", ok=False)
            return None
        return self._current_worker

    def _start_session(self) -> None:
        worker = self._require_worker()
        if worker is None:
            return
        worker_id = str(getattr(worker, "worker_id", "") or "").strip()
        current = self._session_store.get(worker_id)
        if current is not None and not self._session_finished(current):
            self._set_status("Ta sesja już jest aktywna.", ok=False)
            self._current_session = current
            self._refresh_session_ui()
            return

        now = datetime.now()
        session = WorkTimeSessionDef(
            worker_id=worker_id,
            worker_name=str(getattr(worker, "name", "") or "").strip(),
            work_type=self._selected_work_type(),
            started_at_iso=now.isoformat(timespec="seconds"),
            break_total_minutes=0.0,
            last_action_iso=now.isoformat(timespec="seconds"),
        )
        self._session_store.set(session)
        self._current_session = session
        self._set_status(f"Start pracy zapisany dla {session.worker_name}.", ok=True)
        self._refresh_session_ui()

    def _start_break(self) -> None:
        worker = self._require_worker()
        if worker is None:
            return
        session = self._session_store.get(str(getattr(worker, "worker_id", "") or "").strip())
        if session is None:
            self._set_status("Najpierw rozpocznij pracę.", ok=False)
            return
        if session.break_started_at_iso:
            self._set_status("Przerwa już trwa.", ok=False)
            return
        now = datetime.now().isoformat(timespec="seconds")
        session.break_started_at_iso = now
        session.last_action_iso = now
        self._session_store.set(session)
        self._current_session = session
        self._set_status("Przerwa rozpoczęta.", ok=True)
        self._refresh_session_ui()

    def _end_break(self) -> None:
        worker = self._require_worker()
        if worker is None:
            return
        session = self._session_store.get(str(getattr(worker, "worker_id", "") or "").strip())
        if session is None:
            self._set_status("Brak aktywnej sesji.", ok=False)
            return
        if not session.break_started_at_iso:
            self._set_status("Przerwa nie jest aktywna.", ok=False)
            return
        now = datetime.now()
        try:
            started = datetime.fromisoformat(session.break_started_at_iso)
            session.break_total_minutes = float(session.break_total_minutes or 0.0) + max((now - started).total_seconds() / 60.0, 0.0)
        except ValueError:
            session.break_total_minutes = float(session.break_total_minutes or 0.0)
        session.break_started_at_iso = ""
        session.last_action_iso = now.isoformat(timespec="seconds")
        self._session_store.set(session)
        self._current_session = session
        self._set_status("Przerwa zakończona.", ok=True)
        self._refresh_session_ui()

    def _finish_session(self) -> None:
        worker = self._require_worker()
        if worker is None:
            return
        worker_id = str(getattr(worker, "worker_id", "") or "").strip()
        session = self._session_store.get(worker_id)
        if session is None:
            self._set_status("Brak aktywnej sesji do zamknięcia.", ok=False)
            return

        now = datetime.now()
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
            entry_id="",
            day=int(now.day),
            date_iso=now.date().isoformat(),
            work_type=str(session.work_type or self._selected_work_type()).strip(),
            start_time=started.strftime("%H:%M"),
            end_time=now.strftime("%H:%M"),
            hours=round(net_minutes / 60.0, 2),
            overtime_hours=0.0,
            extra_pay=0.0,
            project_code="",
            note="Rejestracja z kiosku QR",
        )
        year = now.year
        month = now.month
        result = self._work_time_store.upsert_day_entry(str(getattr(worker, "name", "") or "").strip(), year, month, entry)
        if result.ok:
            self._session_store.delete(worker_id)
            self._current_session = None
        else:
            self._current_session = session
        self._set_status(result.message_pl, ok=result.ok)
        self._refresh_session_ui()

    def _session_finished(self, session: WorkTimeSessionDef) -> bool:
        return not bool(session.started_at_iso)

    def _refresh_session_ui(self) -> None:
        session = self._current_session
        if session is None and self._current_worker is not None:
            session = self._session_store.get(normalize_worker_id(str(getattr(self._current_worker, "worker_id", "") or "")))
            self._current_session = session

        if session is None:
            self.lab_session_state.setText("Brak aktywnej sesji.")
            self.lab_session_details.setText("Zeskanuj pracownika i rozpocznij pracę.")
            self.btn_break_start.setEnabled(False)
            self.btn_break_end.setEnabled(False)
            self.btn_finish.setEnabled(False)
            self.btn_start.setEnabled(True)
            return

        break_state = "aktywna" if session.break_started_at_iso else "nieaktywna"
        details = (
            f"Pracownik: {session.worker_name or '-'}\n"
            f"Rodzaj: {session.work_type or '-'}\n"
            f"Start: {session.started_at_iso or '-'}\n"
            f"Przerwa: {break_state}\n"
            f"Przerwy razem: {float(session.break_total_minutes or 0.0):.0f} min"
        )
        self.lab_session_state.setText("Sesja aktywna")
        self.lab_session_details.setText(details)
        self.btn_break_start.setEnabled(not bool(session.break_started_at_iso))
        self.btn_break_end.setEnabled(bool(session.break_started_at_iso))
        self.btn_finish.setEnabled(True)
        self.btn_start.setEnabled(False)

    def _open_worker_qr_dialog(self) -> None:
        worker = self._current_worker
        if worker is None:
            QMessageBox.information(self, "QR pracownika", "Najpierw wybierz pracownika.")
            return
        dialog = WorkerQrDialog(worker, self)
        dialog.exec()

    def _set_status(self, message: str, ok: bool) -> None:
        self.lab_scan_status.setText(str(message or ""))
        if ok:
            self.lab_connection.setText("Gotowe")
            self.lab_connection.setStyleSheet(
                "background:#ecfdf5; color:#166534; border:1px solid #bbf7d0; border-radius:14px; padding:12px 16px; font-weight:800;"
            )
        else:
            self.lab_connection.setText("Sprawdź skan")
            self.lab_connection.setStyleSheet(
                "background:#fef2f2; color:#991b1b; border:1px solid #fecaca; border-radius:14px; padding:12px 16px; font-weight:800;"
            )
