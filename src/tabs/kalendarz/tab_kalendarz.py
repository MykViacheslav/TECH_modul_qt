from __future__ import annotations



import calendar as _calendar

from dataclasses import replace

from datetime import date, datetime, timedelta

from typing import Callable



from PyQt6.QtCore import QDate, QMimeData, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QDrag

from PyQt6.QtWidgets import (
    QApplication,

    QCheckBox,

    QComboBox,

    QDateEdit,

    QDialog,

    QFormLayout,

    QFrame,

    QGridLayout,

    QHBoxLayout,

    QLabel,

    QLineEdit,

    QListWidget,

    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,

    QSizePolicy,

    QStackedWidget,

    QVBoxLayout,

    QWidget,

)



from src.domain.calendar_event import (

    EVENT_COLORS,

    EVENT_TYPE_LABELS,

    EVENT_TYPES,

    STATIONS,

    CalendarEvent,

)

from src.storage.calendar_event_store_json import CalendarEventStoreJson

from src.storage.order_store_json import OrderStoreJson

from src.widgets.pdf_reports import (

    ProductionCalendarData, 

    export_production_calendar,

    get_default_export_dir,

)

from src.storage.service_store_json import ServiceStoreJson

from src.storage.worker_store_json import WorkerStoreJson



MONTHS_PL = [

    "", "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",

    "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień",

]





ORDER_STAGE_DATE_RANGES: tuple[tuple[str, str], ...] = (
    ("date_wycena", "date_wycena_end"),
    ("date_projekt", "date_projekt_end"),
    ("date_probki", "date_probki_end"),
    ("date_zakup_mat", "date_zakup_mat_end"),
    ("date_produkcja", "date_produkcja_end"),
    ("date_lakiernia", ""),
    ("date_montaz", "date_montaz_end"),
    ("date_poprawki", "date_poprawki_end"),
)


def _parse_date(value: str) -> date | None:
    try:

        return date.fromisoformat(str(value or "").strip())

    except (ValueError, AttributeError):

        return None





def _event_date_range(event: CalendarEvent) -> tuple[date, date] | None:

    start = _parse_date(str(getattr(event, "date", "") or ""))

    if start is None:

        return None

    end_raw = str(getattr(event, "date_end", "") or "").strip()

    end = _parse_date(end_raw) if end_raw else start

    if end is None:

        end = start

    if end < start:

        end = start

    return start, end





def _event_spans_day(event: CalendarEvent, day: date) -> bool:

    rng = _event_date_range(event)

    if rng is None:

        return False

    start, end = rng

    return start <= day <= end





def _event_overlaps_period(event: CalendarEvent, period_start: date, period_end: date) -> bool:

    rng = _event_date_range(event)

    if rng is None:

        return False

    start, end = rng

    return start <= period_end and end >= period_start





def _is_virtual_service_event(event: CalendarEvent) -> bool:

    return str(getattr(event, "id", "") or "").startswith("svc_")





def _build_service_calendar_events() -> list[CalendarEvent]:
    try:

        services = ServiceStoreJson().list_services()

    except Exception:

        return []



    events: list[CalendarEvent] = []

    for svc in services:

        name = str(getattr(svc, "name", "") or "").strip()

        deadline = str(getattr(svc, "deadline", "") or "").strip()

        if not name or not _parse_date(deadline):

            continue

        service_id = str(getattr(svc, "service_id", "") or "").strip() or "svc"

        category = str(getattr(svc, "category", "") or "").strip()

        events.append(

            CalendarEvent(

                id=f"svc_{service_id}",

                event_type="zlecenie",

                station="Biuro",

                title=f"Usluga: {name}",

                date=deadline,

                date_end="",

                worker_name="",

                order_code=service_id,

                notes=f"Kategoria: {category}" if category else "",

            )

        )
    return events


def _chip_label(text: str, bg: str, fg: str = "#ffffff") -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(
        f"QLabel{{background:{bg};color:{fg};padding:3px 10px;border-radius:999px;"
        "font-size:10px;font-weight:800;}}"
    )
    return label




# ---------------------------------------------------------------------------

# Dialog: add / edit event

# ---------------------------------------------------------------------------



class EventDialog(QDialog):

    def __init__(

        self,

        preset_date: date | None,

        preset_station: str | None,

        store: CalendarEventStoreJson,

        worker_store: WorkerStoreJson | None = None,

        event: CalendarEvent | None = None,

        parent: QWidget | None = None,

    ) -> None:

        super().__init__(parent)

        self._store = store

        self._event = event

        is_new = event is None

        self.setWindowTitle("Dodaj zdarzenie" if is_new else "Edytuj zdarzenie")

        self.setModal(True)

        self.setMinimumWidth(420)



        root = QVBoxLayout(self)

        form = QFormLayout()

        form.setSpacing(10)

        root.addLayout(form)



        self.ed_title = QLineEdit(self)

        self.ed_title.setPlaceholderText("Nazwa zdarzenia…")

        form.addRow("Tytuł:", self.ed_title)



        self.cb_type = QComboBox(self)

        for et in EVENT_TYPES:

            self.cb_type.addItem(EVENT_TYPE_LABELS[et], et)

        form.addRow("Typ:", self.cb_type)



        self.cb_station = QComboBox(self)

        self.cb_station.addItem("(brak stanowiska)", "")

        for s in STATIONS:

            self.cb_station.addItem(s, s)

        form.addRow("Stanowisko:", self.cb_station)



        self.de_date = QDateEdit(self)

        self.de_date.setCalendarPopup(True)

        self.de_date.setDisplayFormat("yyyy-MM-dd")

        self.de_date.setMinimumDate(QDate(2026, 1, 1))

        current_date = QDate.currentDate()

        self.de_date.setDate(current_date if current_date >= self.de_date.minimumDate() else self.de_date.minimumDate())

        form.addRow("Data od:", self.de_date)



        self.de_date_end = QDateEdit(self)

        self.de_date_end.setCalendarPopup(True)

        self.de_date_end.setDisplayFormat("yyyy-MM-dd")

        self.de_date_end.setMinimumDate(QDate(2026, 1, 1))

        self.de_date_end.setDate(self.de_date.date())

        chk_multi = QCheckBox("Wielodniowy (okres)")

        chk_multi.setChecked(False)

        self.de_date_end.setEnabled(False)

        self.de_date_end.setVisible(False)

        chk_multi.toggled.connect(self.de_date_end.setEnabled)

        chk_multi.toggled.connect(self.de_date_end.setVisible)



        date_end_layout = QHBoxLayout()

        date_end_layout.addWidget(self.de_date_end)

        date_end_layout.addWidget(chk_multi)



        form.addRow("", chk_multi)

        form.addRow("Data do:", date_end_layout)



        self.cb_worker = QComboBox(self)

        self.cb_worker.setEditable(True)

        self.cb_worker.addItem("")

        if worker_store is not None:

            for name in worker_store.list_names():

                self.cb_worker.addItem(name)

        form.addRow("Pracownik:", self.cb_worker)



        self.ed_order = QLineEdit(self)

        self.ed_order.setPlaceholderText("opcjonalnie")

        form.addRow("Nr zamówienia:", self.ed_order)



        self.ed_notes = QLineEdit(self)

        form.addRow("Notatka:", self.ed_notes)



        btns = QHBoxLayout()

        self.btn_save = QPushButton("Zapisz")

        self.btn_save.setDefault(True)

        self.btn_save.setStyleSheet(

            "QPushButton{background:#2563eb;color:white;font-weight:700;"

            "padding:5px 14px;border-radius:6px;border:none;}"

            "QPushButton:hover{background:#1d4ed8;}"

        )

        self.btn_delete = QPushButton("Usuń")

        self.btn_delete.setVisible(not is_new)

        self.btn_delete.setStyleSheet("color:#dc2626; font-weight:700;")

        self.btn_cancel = QPushButton("Anuluj")

        btns.addWidget(self.btn_save)

        btns.addWidget(self.btn_delete)

        btns.addStretch()

        btns.addWidget(self.btn_cancel)

        root.addLayout(btns)



        # Pre-fill

        if not is_new and event is not None:

            self.ed_title.setText(event.title)

            idx = self.cb_type.findData(event.event_type)

            self.cb_type.setCurrentIndex(max(0, idx))

            idx_s = self.cb_station.findData(event.station)

            self.cb_station.setCurrentIndex(max(0, idx_s))

            d = _parse_date(event.date)

            if d:

                self.de_date.setDate(QDate(d.year, d.month, d.day))

            de = _parse_date(event.date_end)

            if de:

                self.de_date_end.setDate(QDate(de.year, de.month, de.day))

                self.de_date_end.setEnabled(True)

                self.de_date_end.setVisible(True)

                for child in self.de_date_end.parentWidget().findChildren(QCheckBox):

                    child.setChecked(True)

                    break

            self.cb_worker.setCurrentText(event.worker_name)

            self.ed_order.setText(event.order_code)

            self.ed_notes.setText(event.notes)

        else:

            if preset_date:

                self.de_date.setDate(QDate(preset_date.year, preset_date.month, preset_date.day))

            if preset_station:

                idx_s = self.cb_station.findData(preset_station)

                if idx_s >= 0:

                    self.cb_station.setCurrentIndex(idx_s)



        self.btn_save.clicked.connect(self._on_save)

        self.btn_delete.clicked.connect(self._on_delete)

        self.btn_cancel.clicked.connect(self.reject)



    def _on_save(self) -> None:
        title = self.ed_title.text().strip()

        if not title:

            self.ed_title.setFocus()

            return

        ev_type = str(self.cb_type.currentData() or "inne")

        station = str(self.cb_station.currentData() or "")

        date_str = self.de_date.date().toString("yyyy-MM-dd")

        date_end_str = self.de_date_end.date().toString("yyyy-MM-dd") if self.de_date_end.isEnabled() and self.de_date.date() != self.de_date_end.date() else ""

        worker = self.cb_worker.currentText().strip()

        order = self.ed_order.text().strip()

        notes = self.ed_notes.text().strip()

        if self._event is None:

            ev = CalendarEvent.new(

                ev_type, station, title, date_str, date_end=date_end_str,

                worker_name=worker, order_code=order, notes=notes,

            )

        else:

            ev = replace(

                self._event,

                event_type=ev_type, station=station, title=title, date=date_str,

                date_end=date_end_str, worker_name=worker, order_code=order, notes=notes,

            )

        try:
            self._store.save(ev)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Blad zapisu danych",
                f"Nie udalo sie zapisac wydarzenia.\n\nSzczegoly: {exc}",
            )
            return
        self.accept()

    def _on_delete(self) -> None:
        if self._event is not None:
            try:
                self._store.delete(self._event.id)
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Blad zapisu danych",
                    f"Nie udalo sie usunac wydarzenia.\n\nSzczegoly: {exc}",
                )
                return
        self.accept()




# ---------------------------------------------------------------------------

# Draggable event block

# ---------------------------------------------------------------------------



class EventBlock(QFrame):

    def __init__(

        self,

        event: CalendarEvent,

        on_edit: Callable[[CalendarEvent], None],

        parent: QWidget | None = None,

        compact: bool = False,

    ) -> None:

        super().__init__(parent)

        self._event = event

        self._on_edit = on_edit

        self._drag_start_pos = None

        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self.setMouseTracking(True)



        color = EVENT_COLORS.get(event.event_type, "#94a3b8")

        type_label = EVENT_TYPE_LABELS.get(event.event_type, event.event_type)



        if compact:
            self.setStyleSheet(
                f"QFrame{{background: {color}33; border-radius:6px; border:1px solid {color}66;}}"
            )
            layout = QHBoxLayout(self)
            layout.setContentsMargins(5, 2, 5, 2)
            text = f"{type_label}: {event.title}"
            lab = QLabel(text, self)
            lab.setStyleSheet(
                f"color:{color}; font-size:10px; background:transparent; font-weight:800;"
            )
            lab.setFixedHeight(18)
            layout.addWidget(lab)
        else:
            self.setStyleSheet(
                f"QFrame{{background: {color}22; border-radius:10px; border:1px solid {color}55;}}"
            )
            layout = QVBoxLayout(self)
            layout.setContentsMargins(8, 6, 8, 6)
            layout.setSpacing(2)
            title_lab = QLabel(event.title, self)
            title_lab.setStyleSheet(
                f"color: {color}; font-weight:900; font-size:11px; background:transparent;"
            )

            title_lab.setWordWrap(True)

            layout.addWidget(title_lab)



            parts = [type_label]

            if event.worker_name:

                parts.append(event.worker_name)

            if event.order_code:

                parts.append(f"#{event.order_code}")

            sub = QLabel(" | ".join(parts), self)

            sub.setStyleSheet(

                "color:rgba(255,255,255,0.85);font-size:10px;background:transparent;"

            )

            layout.addWidget(sub)



    def mousePressEvent(self, e) -> None:

        if e.button() == Qt.MouseButton.LeftButton:

            self._drag_start_pos = e.pos()

        super().mousePressEvent(e)



    def mouseDoubleClickEvent(self, e) -> None:

        if _is_virtual_service_event(self._event):

            return

        self._on_edit(self._event)



    def mouseMoveEvent(self, e) -> None:

        if _is_virtual_service_event(self._event):

            return

        if not (e.buttons() & Qt.MouseButton.LeftButton):

            return

        if self._drag_start_pos is None:

            return

        if (e.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():

            return

        drag = QDrag(self)

        mime = QMimeData()

        mime.setText(self._event.id)

        drag.setMimeData(mime)

        pixmap = self.grab()

        drag.setPixmap(pixmap)

        drag.setHotSpot(e.pos())

        drag.exec(Qt.DropAction.MoveAction)





# ---------------------------------------------------------------------------

# Droppable calendar cell

# ---------------------------------------------------------------------------



_STYLE_DEFAULT = "QFrame{{background:{bg}; border:1px solid rgba(59, 130, 246, 0.1); border-radius:12px;}}"
_STYLE_HOVER   = "QFrame{{background:rgba(59, 130, 246, 0.15); border:2px solid rgba(59, 130, 246, 0.5); border-radius:12px;}}"
_STYLE_SELECTED = "QFrame{{background:{bg}; border:2px solid #3b82f6; border-radius:12px;}}"




class CalendarCell(QFrame):

    def __init__(
        self,
        cell_date: date,
        station: str,
        store: CalendarEventStoreJson,
        on_change: Callable[[], None],
        on_add: Callable[[date, str], None],
        on_select: Callable[[date], None] | None = None,
        parent: QWidget | None = None,
        is_today: bool = False,
        compact: bool = False,
        selected: bool = False,
    ) -> None:
        super().__init__(parent)
        self._date = cell_date
        self._station = station
        self._store = store
        self._on_change = on_change
        self._on_add = on_add
        self._on_select = on_select
        self._compact = compact
        self._is_selected = bool(selected)
        self.setAcceptDrops(True)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        if is_today:
            bg = "#eef4ff"
        elif compact and cell_date.month != date.today().month:
            bg = "transparent"
        else:
            bg = "#ffffff"
        self._base_bg = bg
        self._default_style = self._build_default_style()
        self.setStyleSheet(self._default_style)


        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(3)


        if compact:

            day_lab = QLabel(str(cell_date.day), self)

            day_lab.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

            if is_today:
                day_lab.setStyleSheet(
                    "font-weight:800;color:#1d4ed8;background:transparent;font-size:12px;"
                )
            else:

                day_lab.setStyleSheet(

                    "font-weight:600;color:#374151;background:transparent;font-size:12px;"

                )

            outer.addWidget(day_lab)



        self._events_widget = QWidget(self)

        self._events_widget.setStyleSheet("background:transparent;")

        self._events_layout = QVBoxLayout(self._events_widget)

        self._events_layout.setContentsMargins(0, 0, 0, 0)

        self._events_layout.setSpacing(2)

        outer.addWidget(self._events_widget)

        outer.addStretch()



        if not compact:
            self.setMinimumHeight(106)
        else:
            self.setMinimumHeight(96)


    def set_events(

        self,

        events: list[CalendarEvent],

        on_edit: Callable[[CalendarEvent], None],

    ) -> None:

        while self._events_layout.count():

            item = self._events_layout.takeAt(0)

            if item.widget():

                item.widget().deleteLater()

        limit = 4 if self._compact else len(events)

        for ev in events[:limit]:

            block = EventBlock(ev, on_edit, self._events_widget, compact=self._compact)

            self._events_layout.addWidget(block)

        if self._compact and len(events) > limit:
            more = QLabel(f"+{len(events) - limit}", self._events_widget)
            more.setStyleSheet("color:#64748b;font-size:10px;background:transparent;")
            self._events_layout.addWidget(more)

    def _build_default_style(self) -> str:
        if self._is_selected:
            return _STYLE_SELECTED.format(bg=self._base_bg)
        return _STYLE_DEFAULT.format(bg=self._base_bg)

    def set_selected(self, selected: bool) -> None:
        self._is_selected = bool(selected)
        self._default_style = self._build_default_style()
        self.setStyleSheet(self._default_style)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton and self._on_select is not None:
            self._on_select(self._date)
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e) -> None:
        self._on_add(self._date, self._station)


    def dragEnterEvent(self, e) -> None:

        if e.mimeData().hasText():

            self.setStyleSheet(_STYLE_HOVER)

            e.acceptProposedAction()



    def dragLeaveEvent(self, e) -> None:

        self.setStyleSheet(self._default_style)



    def dragMoveEvent(self, e) -> None:

        e.acceptProposedAction()



    def dropEvent(self, e) -> None:
        self.setStyleSheet(self._default_style)
        event_id = e.mimeData().text().strip()
        ev = self._store.get(event_id)
        if ev is not None:
            updated = replace(ev, date=self._date.isoformat(), station=self._station)
            try:
                self._store.save(updated)
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Blad zapisu danych",
                    f"Nie udalo sie przeniesc wydarzenia.\n\nSzczegoly: {exc}",
                )
                return
            QTimer.singleShot(0, self._on_change)
        e.acceptProposedAction()




# ---------------------------------------------------------------------------

# Week grid

# ---------------------------------------------------------------------------



_DAY_NAMES_PL = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Nd"]





class WeekGrid(QScrollArea):
    def __init__(
        self,
        store: CalendarEventStoreJson,
        worker_store: WorkerStoreJson | None,
        on_change: Callable[[], None],
        on_day_selected: Callable[[date], None] | None = None,
        selected_date: date | None = None,
        service_events_provider: Callable[[], list[CalendarEvent]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._worker_store = worker_store
        self._on_change = on_change
        self._on_day_selected = on_day_selected
        self._selected_day = selected_date
        self._service_events_provider = service_events_provider or (lambda: [])
        self._filter_worker = ""

        self._filter_station = ""

        self._filter_event_type = ""

        today = date.today()

        self._week_start = today - timedelta(days=today.weekday())

        self.setWidgetResizable(True)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._rebuild()



    def navigate(self, weeks: int) -> None:

        self._week_start += timedelta(weeks=weeks)

        self._rebuild()



    def set_filters(self, worker: str, station: str, event_type: str) -> None:
        self._filter_worker = str(worker or "").strip().lower()
        self._filter_station = str(station or "").strip()
        self._filter_event_type = str(event_type or "").strip()
        self._rebuild()

    def set_selected_day(self, selected_day: date | None) -> None:
        self._selected_day = selected_day
        self._rebuild()

    def _handle_day_selected(self, selected_day: date) -> None:
        self._selected_day = selected_day
        self._rebuild()
        if self._on_day_selected is not None:
            self._on_day_selected(selected_day)


    def _event_matches_filters(self, event: CalendarEvent) -> bool:

        if self._filter_station and str(event.station or "") != self._filter_station:

            return False

        if self._filter_event_type and str(event.event_type or "") != self._filter_event_type:

            return False

        if self._filter_worker and self._filter_worker not in str(event.worker_name or "").strip().lower():

            return False

        return True



    def _rebuild(self) -> None:
        container = QWidget()
        container.setStyleSheet("background:transparent;")
        grid = QGridLayout(container)
        grid.setSpacing(2)
        grid.setContentsMargins(0, 0, 0, 0)


        today = date.today()

        days = [self._week_start + timedelta(days=i) for i in range(7)]



        # Column sizing: col 0 = station label, cols 1-7 = days

        grid.setColumnMinimumWidth(0, 90)

        for col in range(1, 8):

            grid.setColumnMinimumWidth(col, 140)

            grid.setColumnStretch(col, 1)



        # Corner

        corner = QLabel("", container)
        corner.setFixedHeight(46)
        corner.setStyleSheet("background:#eef3fb;border:1px solid #d3dfef;border-radius:8px;")
        grid.addWidget(corner, 0, 0)


        # Day headers

        for col, (d, name) in enumerate(zip(days, _DAY_NAMES_PL), 1):

            is_today = d == today

            text = f"{name}\n{d.strftime('%d.%m')}"

            lab = QLabel(text, container)
            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lab.setFixedHeight(46)
            is_weekend = d.weekday() >= 5
            if is_today:
                lab.setStyleSheet(
                    "background:#dbeafe;font-weight:900;color:#1d4ed8;border:1px solid #93c5fd;border-radius:8px;"
                )
            elif is_weekend:
                lab.setStyleSheet(
                    "background:#fef3c7;font-weight:800;color:#92400e;border:1px solid #fcd34d;border-radius:8px;"
                )
            else:
                lab.setStyleSheet(
                    "background:#eef3fb;font-weight:700;color:#334155;border:1px solid #d3dfef;border-radius:8px;"
                )
            grid.addWidget(lab, 0, col)


        # Load events once for the whole week

        all_events = self._store.list_events() + list(self._service_events_provider())

        week_start = days[0]

        week_end = days[-1]



        def event_in_week(ev: CalendarEvent) -> bool:

            return self._event_matches_filters(ev) and _event_overlaps_period(ev, week_start, week_end)



        week_events = [ev for ev in all_events if event_in_week(ev)]



        # Station rows

        for row, station in enumerate(STATIONS, 1):

            lab = QLabel(station, container)

            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lab.setFixedWidth(90)

            lab.setMinimumHeight(100)

            lab.setWordWrap(True)
            lab.setStyleSheet(
                "background:#e6edf7;font-weight:800;border:1px solid #ccd8e8;color:#1e293b;border-radius:8px;"
            )
            grid.addWidget(lab, row, 0)

            grid.setRowMinimumHeight(row, 100)

            grid.setRowStretch(row, 1)



            for col, d in enumerate(days, 1):

                is_today = d == today



                def event_on_day(ev: CalendarEvent, day: date) -> bool:

                    if ev.station != station:

                        return False

                    return _event_spans_day(ev, day)



                cell_events = [ev for ev in week_events if event_on_day(ev, d)]
                cell = CalendarCell(
                    d, station, self._store, self._on_change,
                    self._open_add, self._handle_day_selected, container,
                    is_today=is_today, compact=False, selected=(self._selected_day == d),
                )
                cell.set_events(cell_events, self._open_edit)
                grid.addWidget(cell, row, col)


        self.setWidget(container)



    def _open_add(self, d: date, station: str) -> None:

        dlg = EventDialog(d, station, self._store, self._worker_store, parent=self)

        dlg.exec()

        self._on_change()



    def _open_edit(self, event: CalendarEvent) -> None:

        if _is_virtual_service_event(event):

            return

        dlg = EventDialog(None, None, self._store, self._worker_store, event=event, parent=self)

        dlg.exec()

        self._on_change()





# ---------------------------------------------------------------------------

# Month grid

# ---------------------------------------------------------------------------



class MonthGrid(QScrollArea):
    def __init__(
        self,
        store: CalendarEventStoreJson,
        worker_store: WorkerStoreJson | None,
        on_change: Callable[[], None],
        on_day_selected: Callable[[date], None] | None = None,
        selected_date: date | None = None,
        service_events_provider: Callable[[], list[CalendarEvent]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._worker_store = worker_store
        self._on_change = on_change
        self._on_day_selected = on_day_selected
        self._selected_day = selected_date
        self._service_events_provider = service_events_provider or (lambda: [])
        self._filter_worker = ""

        self._filter_station = ""

        self._filter_event_type = ""

        today = date.today()

        self._year = today.year

        self._month = today.month

        self.setWidgetResizable(True)

        self._rebuild()



    def navigate(self, months: int) -> None:

        m = self._month + months

        y = self._year

        while m > 12:

            m -= 12

            y += 1

        while m < 1:

            m += 12

            y -= 1

        self._month = m

        self._year = y

        self._rebuild()



    def navigate_to_date(self, target_date: date | None) -> None:

        if target_date is None:

            return

        target_year = target_date.year

        target_month = target_date.month

        months_diff = (target_year - self._year) * 12 + (target_month - self._month)

        if months_diff != 0:

            self.navigate(months_diff)



    def set_filters(self, worker: str, station: str, event_type: str) -> None:
        self._filter_worker = str(worker or "").strip().lower()
        self._filter_station = str(station or "").strip()
        self._filter_event_type = str(event_type or "").strip()
        self._rebuild()

    def set_selected_day(self, selected_day: date | None) -> None:
        self._selected_day = selected_day
        self._rebuild()

    def _handle_day_selected(self, selected_day: date) -> None:
        self._selected_day = selected_day
        self._rebuild()
        if self._on_day_selected is not None:
            self._on_day_selected(selected_day)


    def _event_matches_filters(self, event: CalendarEvent) -> bool:

        if self._filter_station and str(event.station or "") != self._filter_station:

            return False

        if self._filter_event_type and str(event.event_type or "") != self._filter_event_type:

            return False

        if self._filter_worker and self._filter_worker not in str(event.worker_name or "").strip().lower():

            return False

        return True



    def _rebuild(self) -> None:
        container = QWidget()
        container.setStyleSheet("background:transparent;")
        grid = QGridLayout(container)
        grid.setSpacing(2)
        grid.setContentsMargins(0, 0, 0, 0)


        # Day-of-week header

        for col, name in enumerate(_DAY_NAMES_PL):
            lab = QLabel(name, container)
            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lab.setFixedHeight(36)
            if col >= 5:
                lab.setStyleSheet(
                    "background:#fef3c7;font-weight:800;color:#92400e;border:1px solid #fcd34d;border-radius:8px;"
                )
            else:
                lab.setStyleSheet(
                    "background:#eef3fb;font-weight:800;color:#334155;border:1px solid #d3dfef;border-radius:8px;"
                )
            grid.addWidget(lab, 0, col)
            grid.setColumnStretch(col, 1)


        first_day = date(self._year, self._month, 1)

        offset = first_day.weekday()

        today = date.today()

        first_visible_day = first_day - timedelta(days=offset)

        last_visible_day = first_visible_day + timedelta(days=41)

        cell_date = first_visible_day



        # Events shown in visible 6x7 month grid, including ranges that started in another month.

        all_events = self._store.list_events() + list(self._service_events_provider())

        month_events = [

            ev

            for ev in all_events

            if self._event_matches_filters(ev) and _event_overlaps_period(ev, first_visible_day, last_visible_day)

        ]



        for week_row in range(6):

            any_in_month = False

            for day_col in range(7):

                is_cur_month = cell_date.month == self._month

                if is_cur_month:

                    any_in_month = True

                is_today = cell_date == today



                def event_in_range(ev: CalendarEvent) -> bool:

                    return _event_spans_day(ev, cell_date)



                cell_events = [ev for ev in month_events if event_in_range(ev)]
                cell = CalendarCell(
                    cell_date, "", self._store, self._on_change,
                    self._open_add, self._handle_day_selected, container,
                    is_today=is_today, compact=True, selected=(self._selected_day == cell_date),
                )
                if not is_cur_month:
                    cell._base_bg = "#f4f4f5"
                    cell.set_selected(self._selected_day == cell_date)
                cell.set_events(cell_events, self._open_edit)
                grid.addWidget(cell, week_row + 1, day_col)

                grid.setRowMinimumHeight(week_row + 1, 100)

                grid.setRowStretch(week_row + 1, 1)

                cell_date += timedelta(days=1)



            # Stop after the row where the month ends

            if not any_in_month and week_row > 3:

                break



        self.setWidget(container)



    def _open_add(self, d: date, station: str) -> None:

        dlg = EventDialog(d, "", self._store, self._worker_store, parent=self)

        dlg.exec()

        self._on_change()



    def _open_edit(self, event: CalendarEvent) -> None:

        if _is_virtual_service_event(event):

            return

        dlg = EventDialog(None, None, self._store, self._worker_store, event=event, parent=self)

        dlg.exec()

        self._on_change()





# ---------------------------------------------------------------------------

# Main tab widget

# ---------------------------------------------------------------------------



class TabKalendarz(QWidget):
    sig_return_to_order_requested = pyqtSignal()

    def __init__(
        self,
        parent: QWidget | None = None,

        order_store=None,

        worker_store: WorkerStoreJson | None = None,

        calendar_store: CalendarEventStoreJson | None = None,

    ) -> None:

        super().__init__(parent)

        self._calendar_store = calendar_store or CalendarEventStoreJson()

        self._worker_store = worker_store or WorkerStoreJson()
        self._order_store = order_store or OrderStoreJson()
        self._current_view = "week"
        self._selected_order_day: date | None = None


        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 18)
        root.setSpacing(14)
        self.setObjectName("tab_calendar_root")
        self.setStyleSheet(
            "QWidget#tab_calendar_root{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #eef3fb,stop:1 #f8fbff);}"
            "QComboBox, QLineEdit, QListWidget{background:transparent;border:1px solid #cfdced;"
            "border-radius:10px;padding:6px 10px;color:#0f172a;font-size:12px;}"
            "QComboBox::drop-down{border:none;width:22px;}"
            "QListWidget{padding:4px;}"
            "QListWidget::item{padding:8px 9px;border-bottom:1px solid #eef2f7;}"
            "QListWidget::item:selected{background:#dbeafe;color:#0f172a;border-radius:8px;}"
            "QPushButton{background:transparent;border:1px solid #c9d6e8;border-radius:10px;"
            "padding:7px 12px;color:#12243b;font-size:12px;font-weight:700;}"
            "QPushButton:hover{background:#edf4fd;}"
        )


        # ── Header ──────────────────────────────────────────────────────────

        header = QHBoxLayout()
        title = QLabel("KALENDARZ")
        title.setStyleSheet("font-size:27px;font-weight:900;color:#0b1220;letter-spacing:0.2px;")
        header.addWidget(title)
        header.addStretch()


        self._btn_week = QPushButton("Tydzień")

        self._btn_month = QPushButton("Miesiąc")

        for btn in (self._btn_week, self._btn_month):
            btn.setCheckable(True)
            btn.setFixedHeight(34)
            btn.setStyleSheet(
                "QPushButton{padding:6px 16px;border:1px solid #c6d5ea;border-radius:999px;background:#f8fbff;}"
                "QPushButton:checked{background:#0b3a6e;color:#fff;border-color:#0b3a6e;font-weight:900;}"
            )
        self._btn_week.setChecked(True)

        header.addWidget(self._btn_week)

        header.addWidget(self._btn_month)

        root.addLayout(header)



        # ── Navigation bar ───────────────────────────────────────────────────

        nav_frame = QFrame(self); nav_frame.setProperty("uiCard", True)
        nav_frame.setObjectName("calendar_nav_frame")
        nav_frame.setStyleSheet(
            "QFrame#calendar_nav_frame{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #ffffff,stop:1 #f7faff);"
            "border:1px solid #cad9ec;border-radius:18px;}"
        )
        nav = QHBoxLayout(nav_frame)
        nav.setContentsMargins(14, 11, 14, 11)
        nav.setSpacing(10)
        self._btn_prev = QPushButton("<")
        self._btn_prev.setFixedWidth(36)
        self._btn_next = QPushButton(">")
        self._btn_next.setFixedWidth(36)
        self._btn_today = QPushButton("Dzis")
        self._btn_return_to_order = QPushButton("Wroc do zamowienia")
        self._btn_return_to_order.setVisible(False)
        self._btn_return_to_order.setEnabled(False)
        self._lab_period = QLabel("")
        self._lab_period.setStyleSheet("font-weight:900;font-size:16px;color:#0f172a;padding:0 12px;")

        self._btn_add = QPushButton("+ Dodaj zdarzenie")
        self._btn_add.setStyleSheet(
            "QPushButton{background:#0b3a6e;color:white;font-weight:900;"
            "padding:8px 16px;border-radius:10px;border:1px solid #082f57;}"
            "QPushButton:hover{background:#124a87;}"
        )
        
        self._btn_sync_orders = QPushButton("Z zamowien")
        self._btn_sync_orders.setToolTip("Synchronizuj kalendarz z zamówieniami")
        self._btn_sync_orders.setStyleSheet(
            "QPushButton{background:#198754;color:white;font-weight:800;"
            "padding:8px 12px;border-radius:10px;border:1px solid #146c43;}"
            "QPushButton:hover{background:#157347;}"
        )

        self._btn_export_pdf = QPushButton("PDF")
        self._btn_export_pdf.setToolTip("Eksportuj harmonogram do PDF")
        self._btn_export_pdf.setStyleSheet(
            "QPushButton{background:#0f766e;color:white;font-weight:800;"
            "padding:8px 12px;border-radius:10px;border:1px solid #115e59;}"
            "QPushButton:hover{background:#0d9488;}"
        )
        self._btn_export_pdf.clicked.connect(self._on_export_pdf)



        nav.addWidget(self._btn_prev)
        nav.addWidget(self._btn_today)
        nav.addWidget(self._btn_next)
        nav.addWidget(self._btn_return_to_order)
        nav.addWidget(self._lab_period, 1)
        nav.addWidget(self._btn_sync_orders)
        nav.addWidget(self._btn_export_pdf)

        nav.addWidget(self._btn_add)

        root.addWidget(nav_frame)


        # ── Event filters ───────────────────────────────────────────────────────

        filters_frame = QFrame(self); filters_frame.setProperty("uiCard", True)
        filters_frame.setObjectName("calendar_filters_frame")
        filters_frame.setStyleSheet(
            "QFrame#calendar_filters_frame{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #ffffff,stop:1 #f8fbff);"
            "border:1px solid #cad9ec;border-radius:18px;}"
        )
        filters_frame_lay = QVBoxLayout(filters_frame)
        filters_frame_lay.setContentsMargins(14, 12, 14, 12)
        filters_frame_lay.setSpacing(9)

        filters = QHBoxLayout()
        filters.setSpacing(8)


        self._cb_filter_type = QComboBox(self)

        self._cb_filter_type.addItem("Typ: wszystkie", "")

        for et in EVENT_TYPES:

            self._cb_filter_type.addItem(f"Typ: {EVENT_TYPE_LABELS[et]}", et)



        self._cb_filter_station = QComboBox(self)

        self._cb_filter_station.addItem("Stanowisko: wszystkie", "")

        for station in STATIONS:

            self._cb_filter_station.addItem(f"Stanowisko: {station}", station)



        self._ed_filter_worker = QLineEdit(self)

        self._ed_filter_worker.setPlaceholderText("Filtr pracownik (np. Jan)")



        self._btn_filter_clear = QPushButton("Wyczysc filtry")
        self._btn_clear_all_filters = QPushButton("Wyczysc wszystko")
        self._btn_filter_clear.setFixedHeight(34)
        self._btn_clear_all_filters.setFixedHeight(34)

        filters.addWidget(self._cb_filter_type)

        filters.addWidget(self._cb_filter_station)

        filters.addWidget(self._ed_filter_worker, 1)

        filters.addWidget(self._btn_filter_clear)

        filters.addWidget(self._btn_clear_all_filters)

        filters_frame_lay.addLayout(filters)


        self._lab_event_filter_chips = QLabel("")
        self._lab_event_filter_chips.setStyleSheet("color:#2f425a;font-size:12px;font-weight:700;background:transparent;")
        filters_frame_lay.addWidget(self._lab_event_filter_chips)


        # ── Legend ───────────────────────────────────────────────────────────

        legend = QHBoxLayout()

        legend.setSpacing(6)

        for et in EVENT_TYPES:

            color = EVENT_COLORS[et]

            lbl = QLabel(EVENT_TYPE_LABELS[et])
            lbl.setStyleSheet(
                f"background:{color};color:white;padding:4px 11px;"
                "border-radius:999px;font-size:10px;font-weight:800;"
            )
            legend.addWidget(lbl)
        legend.addStretch()
        filters_frame_lay.addLayout(legend)
        root.addWidget(filters_frame)


        # ── Stacked views ────────────────────────────────────────────────────

        self._stack = QStackedWidget()

        self._week_view = WeekGrid(
            self._calendar_store,
            self._worker_store,
            self._on_data_change,
            on_day_selected=self._on_calendar_day_selected,
            selected_date=self._selected_order_day,
            service_events_provider=_build_service_calendar_events,
        )
        self._month_view = MonthGrid(
            self._calendar_store,
            self._worker_store,
            self._on_data_change,
            on_day_selected=self._on_calendar_day_selected,
            selected_date=self._selected_order_day,
            service_events_provider=_build_service_calendar_events,
        )
        self._stack.addWidget(self._week_view)

        self._stack.addWidget(self._month_view)

        root.addWidget(self._stack, 1)



        # ── Order status panel ─────────────────────────────────────────────────

        status_frame = QFrame(self); status_frame.setProperty("uiCard", True)
        status_frame.setObjectName("calendar_status_frame")
        status_frame.setStyleSheet(
            "QFrame#calendar_status_frame{border:1px solid #cad9ec;border-radius:18px;"
            "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #ffffff,stop:1 #f8fbff);}"
        )
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(14, 12, 14, 12)
        status_layout.setSpacing(9)

        status_title = QLabel("Statusy zamowien i historia zmian")
        status_title.setStyleSheet("font-size:16px;font-weight:900;color:#0f172a;")
        status_layout.addWidget(status_title)


        status_filters = QHBoxLayout()

        self._cb_order_status = QComboBox(self)

        self._cb_order_status.addItem("Status: wszystkie", "")

        self._cb_order_stage = QComboBox(self)

        self._cb_order_stage.addItem("Etap: wszystkie", "")

        self._ed_order_worker = QLineEdit(self)

        self._ed_order_worker.setPlaceholderText("Pracownik zamowienia")

        self._btn_order_filter_clear = QPushButton("Wyczysc")
        self._btn_order_filter_clear.setFixedHeight(34)
        status_filters.addWidget(self._cb_order_status)

        status_filters.addWidget(self._cb_order_stage)

        status_filters.addWidget(self._ed_order_worker, 1)

        status_filters.addWidget(self._btn_order_filter_clear)

        status_layout.addLayout(status_filters)



        self._lab_order_filter_chips = QLabel("")
        self._lab_order_filter_chips.setStyleSheet("color:#2f425a;font-size:12px;font-weight:700;background:transparent;")
        status_layout.addWidget(self._lab_order_filter_chips)


        self._lab_order_stats = QLabel("-")

        self._lab_order_stats.setStyleSheet("color:#94a3b8;font-size:12px;font-weight:600;")
        status_layout.addWidget(self._lab_order_stats)



        lists_row = QHBoxLayout()

        lists_row.setSpacing(10)



        col_left = QVBoxLayout()

        left_title = QLabel("Zamowienia (po filtrach)")
        left_title.setStyleSheet("font-size:11px;font-weight:800;color:#94a3b8;")
        col_left.addWidget(left_title)
        self._lst_order_status = QListWidget(self)
        self._lst_order_status.setMinimumHeight(120)
        col_left.addWidget(self._lst_order_status)

        col_right = QVBoxLayout()
        right_title = QLabel("Ostatnie zmiany statusu")
        right_title.setStyleSheet("font-size:11px;font-weight:800;color:#94a3b8;")
        col_right.addWidget(right_title)
        self._lst_order_history = QListWidget(self)
        self._lst_order_history.setMinimumHeight(120)
        col_right.addWidget(self._lst_order_history)


        lists_row.addLayout(col_left, 1)

        lists_row.addLayout(col_right, 1)

        status_layout.addLayout(lists_row)



        root.addWidget(status_frame)



        # ── Connections ──────────────────────────────────────────────────────

        self._btn_week.clicked.connect(lambda: self._set_view("week"))

        self._btn_month.clicked.connect(lambda: self._set_view("month"))

        self._btn_prev.clicked.connect(self._navigate_prev)
        self._btn_next.clicked.connect(self._navigate_next)
        self._btn_today.clicked.connect(self._navigate_today)
        self._btn_return_to_order.clicked.connect(self.sig_return_to_order_requested.emit)
        self._btn_sync_orders.clicked.connect(self._sync_from_orders)
        self._btn_add.clicked.connect(self._add_event)

        self._cb_filter_type.currentIndexChanged.connect(self._on_event_filters_changed)

        self._cb_filter_station.currentIndexChanged.connect(self._on_event_filters_changed)

        self._ed_filter_worker.textChanged.connect(self._on_event_filters_changed)

        self._btn_filter_clear.clicked.connect(self._clear_event_filters)

        self._btn_clear_all_filters.clicked.connect(self._clear_all_filters)

        self._cb_order_status.currentIndexChanged.connect(self._refresh_order_status_panel)

        self._cb_order_stage.currentIndexChanged.connect(self._refresh_order_status_panel)

        self._ed_order_worker.textChanged.connect(self._refresh_order_status_panel)

        self._btn_order_filter_clear.clicked.connect(self._clear_order_filters)



        self._update_period_label()
        self._refresh_order_filter_choices()
        self._refresh_order_status_panel()
        self._refresh_filter_chip_labels()

    def set_return_to_order_enabled(self, enabled: bool) -> None:
        is_enabled = bool(enabled)
        self._btn_return_to_order.setVisible(is_enabled)
        self._btn_return_to_order.setEnabled(is_enabled)

    # ── View switching ───────────────────────────────────────────────────────


    def _set_view(self, view: str) -> None:

        self._current_view = view

        self._stack.setCurrentWidget(

            self._week_view if view == "week" else self._month_view

        )

        self._btn_week.setChecked(view == "week")

        self._btn_month.setChecked(view == "month")

        self._update_period_label()



    # ── Navigation ───────────────────────────────────────────────────────────



    def _navigate_prev(self) -> None:

        if self._current_view == "week":

            self._week_view.navigate(-1)

        else:

            self._month_view.navigate(-1)

        self._update_period_label()



    def _navigate_next(self) -> None:

        if self._current_view == "week":

            self._week_view.navigate(1)

        else:

            self._month_view.navigate(1)

        self._update_period_label()



    def _navigate_today(self) -> None:

        today = date.today()

        self._week_view._week_start = today - timedelta(days=today.weekday())

        self._week_view._rebuild()

        self._month_view._year = today.year

        self._month_view._month = today.month

        self._month_view._rebuild()

        self._update_period_label()



    def open_with_date(self, target_date: date | None) -> None:

        if target_date is None:

            return

        self._month_view.navigate_to_date(target_date)

        self._set_view("month")

        QTimer.singleShot(10, self._update_period_label)



    def _update_period_label(self) -> None:

        if self._current_view == "week":

            ws = self._week_view._week_start

            we = ws + timedelta(days=6)

            self._lab_period.setText(

                f"{ws.strftime('%d.%m')} – {we.strftime('%d.%m.%Y')}"

            )

        else:

            m = self._month_view._month

            y = self._month_view._year

            self._lab_period.setText(f"{MONTHS_PL[m]} {y}")



    # ── Data ─────────────────────────────────────────────────────────────────



    def _on_data_change(self) -> None:

        if self._current_view == "week":

            self._week_view._rebuild()

        else:

            self._month_view._rebuild()

        self._update_period_label()

        self._refresh_order_filter_choices()

        self._refresh_order_status_panel()



    def _on_event_filters_changed(self) -> None:

        self._week_view.set_filters(

            worker=self._ed_filter_worker.text().strip(),

            station=str(self._cb_filter_station.currentData() or ""),

            event_type=str(self._cb_filter_type.currentData() or ""),

        )

        self._month_view.set_filters(

            worker=self._ed_filter_worker.text().strip(),

            station=str(self._cb_filter_station.currentData() or ""),

            event_type=str(self._cb_filter_type.currentData() or ""),

        )

        self._update_period_label()

        self._refresh_filter_chip_labels()



    def _clear_event_filters(self) -> None:

        self._cb_filter_type.setCurrentIndex(0)

        self._cb_filter_station.setCurrentIndex(0)

        self._ed_filter_worker.clear()

        self._on_event_filters_changed()



    def _clear_all_filters(self) -> None:
        self._clear_event_filters()
        self._clear_order_filters()
        self._clear_selected_calendar_day()

    def _on_calendar_day_selected(self, selected_day: date) -> None:
        if self._selected_order_day == selected_day:
            self._selected_order_day = None
        else:
            self._selected_order_day = selected_day
        self._week_view.set_selected_day(self._selected_order_day)
        self._month_view.set_selected_day(self._selected_order_day)
        self._refresh_order_status_panel()

    def _clear_selected_calendar_day(self) -> None:
        if self._selected_order_day is None:
            return
        self._selected_order_day = None
        self._week_view.set_selected_day(None)
        self._month_view.set_selected_day(None)

    def _order_matches_selected_day(self, order, selected_day: date | None) -> bool:
        if selected_day is None:
            return True
        selected_iso = selected_day.isoformat()

        direct_date = str(getattr(order, "calendar_date", "") or "").strip()
        if direct_date == selected_iso:
            return True

        for start_field, end_field in ORDER_STAGE_DATE_RANGES:
            start_raw = str(getattr(order, start_field, "") or "").strip()
            if not start_raw:
                continue
            start = _parse_date(start_raw)
            if start is None:
                continue
            end = start
            if end_field:
                end_raw = str(getattr(order, end_field, "") or "").strip()
                end_parsed = _parse_date(end_raw) if end_raw else None
                if end_parsed is not None:
                    end = end_parsed
            if end < start:
                end = start
            if start <= selected_day <= end:
                return True
        return False


    def _refresh_order_filter_choices(self) -> None:

        try:

            orders = list(self._order_store.list_orders() or [])

        except Exception:

            orders = []



        current_status = str(self._cb_order_status.currentData() or "")

        current_stage = str(self._cb_order_stage.currentData() or "")



        statuses = sorted({str(getattr(order, "status", "") or "").strip() for order in orders if str(getattr(order, "status", "") or "").strip()})

        stages = sorted({str(getattr(order, "calendar_stage", "") or "").strip() for order in orders if str(getattr(order, "calendar_stage", "") or "").strip()})



        self._cb_order_status.blockSignals(True)

        self._cb_order_status.clear()

        self._cb_order_status.addItem("Status: wszystkie", "")

        for value in statuses:

            self._cb_order_status.addItem(f"Status: {value}", value)

        idx_status = self._cb_order_status.findData(current_status)

        self._cb_order_status.setCurrentIndex(idx_status if idx_status >= 0 else 0)

        self._cb_order_status.blockSignals(False)



        self._cb_order_stage.blockSignals(True)

        self._cb_order_stage.clear()

        self._cb_order_stage.addItem("Etap: wszystkie", "")

        for value in stages:

            self._cb_order_stage.addItem(f"Etap: {value}", value)

        idx_stage = self._cb_order_stage.findData(current_stage)

        self._cb_order_stage.setCurrentIndex(idx_stage if idx_stage >= 0 else 0)

        self._cb_order_stage.blockSignals(False)



    def _clear_order_filters(self) -> None:

        self._cb_order_status.setCurrentIndex(0)

        self._cb_order_stage.setCurrentIndex(0)

        self._ed_order_worker.clear()

        self._refresh_order_status_panel()



    def _refresh_filter_chip_labels(self) -> None:

        event_parts: list[str] = []

        event_type = str(self._cb_filter_type.currentData() or "").strip()

        event_station = str(self._cb_filter_station.currentData() or "").strip()

        event_worker = self._ed_filter_worker.text().strip()

        if event_type:

            event_parts.append(f"Typ: {EVENT_TYPE_LABELS.get(event_type, event_type)}")

        if event_station:

            event_parts.append(f"Stanowisko: {event_station}")

        if event_worker:

            event_parts.append(f"Pracownik: {event_worker}")

        self._lab_event_filter_chips.setText(

            "Aktywne filtry wydarzen: " + (" | ".join(event_parts) if event_parts else "brak")

        )



        order_parts: list[str] = []
        order_status = str(self._cb_order_status.currentData() or "").strip()
        order_stage = str(self._cb_order_stage.currentData() or "").strip()
        order_worker = self._ed_order_worker.text().strip()
        selected_day = self._selected_order_day.isoformat() if self._selected_order_day else ""
        if order_status:
            order_parts.append(f"Status: {order_status}")
        if order_stage:
            order_parts.append(f"Etap: {order_stage}")
        if order_worker:
            order_parts.append(f"Pracownik: {order_worker}")
        if selected_day:
            order_parts.append(f"Dzien: {selected_day}")
        self._lab_order_filter_chips.setText(
            "Aktywne filtry zamowien: " + (" | ".join(order_parts) if order_parts else "brak")
        )


    def _format_history_timestamp(self, raw: str) -> str:

        value = str(raw or "").strip()

        if not value:

            return "-"

        try:

            parsed = datetime.fromisoformat(value)

            return parsed.strftime("%d.%m.%Y %H:%M")

        except ValueError:

            return value



    def _refresh_order_status_panel(self) -> None:

        try:

            orders = list(self._order_store.list_orders() or [])

        except Exception:

            orders = []



        status_filter = str(self._cb_order_status.currentData() or "").strip()
        stage_filter = str(self._cb_order_stage.currentData() or "").strip()
        worker_filter = self._ed_order_worker.text().strip().lower()
        selected_day = self._selected_order_day

        filtered_orders = []
        for order in orders:
            status = str(getattr(order, "status", "") or "").strip()
            stage = str(getattr(order, "calendar_stage", "") or "").strip()
            worker = str(getattr(order, "worker_name", "") or "").strip()
            if status_filter and status != status_filter:
                continue
            if stage_filter and stage != stage_filter:
                continue
            if worker_filter and worker_filter not in worker.lower():
                continue
            if not self._order_matches_selected_day(order, selected_day):
                continue
            filtered_orders.append(order)

        self._lst_order_status.clear()
        if not filtered_orders:
            if selected_day is not None:
                self._lst_order_status.addItem(
                    QListWidgetItem(f"Brak zamowien dla dnia {selected_day.isoformat()} i wybranych filtrow.")
                )
            else:
                self._lst_order_status.addItem(QListWidgetItem("Brak zamowien dla wybranych filtrow."))
        else:

            for order in sorted(filtered_orders, key=lambda item: str(getattr(item, "code", "") or "")):

                code = str(getattr(order, "code", "") or "-")

                client = str(getattr(order, "client_name", "") or "-")

                status = str(getattr(order, "status", "") or "-")

                progress = int(round(float(getattr(order, "progress_percent", 0.0) or 0.0)))

                stage = str(getattr(order, "calendar_stage", "") or "-")

                calendar_date = str(getattr(order, "calendar_date", "") or "-")

                self._lst_order_status.addItem(

                    QListWidgetItem(

                        f"{code} | {client} | {status} ({progress}%) | etap: {stage} | termin: {calendar_date}"

                    )

                )



        history_rows: list[tuple[str, str]] = []

        for order in filtered_orders:

            order_code = str(getattr(order, "code", "") or "-")

            status_history = list(getattr(order, "status_history", []) or [])

            for entry in status_history:

                if not isinstance(entry, dict):

                    continue

                changed_at = str(entry.get("changed_at", "") or "").strip()

                from_status = str(entry.get("from_status", "") or "").strip() or "-"

                to_status = str(entry.get("to_status", "") or "").strip() or "-"

                changed_by = str(entry.get("changed_by", "") or "").strip() or "-"

                note = str(entry.get("note", "") or "").strip()

                line = f"[{self._format_history_timestamp(changed_at)}] {order_code}: {from_status} -> {to_status} (kto: {changed_by})"

                if note:

                    line += f" | {note}"

                history_rows.append((changed_at, line))



        history_rows.sort(key=lambda item: item[0], reverse=True)

        self._lst_order_history.clear()

        if not history_rows:

            self._lst_order_history.addItem(QListWidgetItem("Brak historii zmian statusu."))

        else:

            for _changed_at, line in history_rows[:30]:

                self._lst_order_history.addItem(QListWidgetItem(line))



        day_part = f" | Dzien: {selected_day.isoformat()}" if selected_day is not None else ""
        self._lab_order_stats.setText(
            f"Zamowienia: {len(filtered_orders)} / {len(orders)} | Zmiany statusu: {len(history_rows)}{day_part}"
        )
        self._refresh_filter_chip_labels()


    def _sync_from_orders(self) -> None:

        """Synchronize calendar with order dates."""

        from src.services.order_calendar_sync import OrderCalendarSync

        

        sync = OrderCalendarSync()

        count = sync.sync_all()

        self._on_data_change()

        

        # Show feedback

        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(

            self,

            "Synchronizacja",

            f"Zsynchronizowano kalendarz z zamówieniami.\n"

            f"Dodano/zaktualizowano: {count} zdarzeń.\n\n"

            f"Zadania pojawią się na kalendarzu i kioskach."

        )

    

    def _add_event(self) -> None:

        today = date.today()

        dlg = EventDialog(

            today, "", self._calendar_store, self._worker_store, parent=self

        )

        if dlg.exec():

            self._on_data_change()



    def _on_export_pdf(self) -> None:

        """Export current calendar view to PDF."""

        from PyQt6.QtWidgets import QFileDialog

        

        # Get current week/month range

        if self._current_view == "week":

            start_date = self._current_week_start

            end_date = start_date + timedelta(days=6)

        else:

            start_date = self._current_month_start

            end_date = self._get_next_month_start() - timedelta(days=1)

        

        # Get events for the period

        all_events = self._calendar_store.list_events()

        period_events = []

        for event in all_events:

            event_date = QDate.fromString(event.date, "yyyy-MM-dd").toPyDate()

            if start_date <= event_date <= end_date:

                period_events.append({

                    "day": self._get_day_name(event_date),

                    "order_code": event.order_code,

                    "client_name": getattr(event, "client_name", ""),

                    "station": event.station,

                    "status": event.status,

                })

        

        # Build data

        data = ProductionCalendarData(

            week_start=start_date.strftime("%Y-%m-%d"),

            week_end=end_date.strftime("%Y-%m-%d"),

            events=period_events,

        )

        

        # Export

        default_path = get_default_export_dir() / f"kalendarz_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

        file_path, _ = QFileDialog.getSaveFileName(

            self,

            "Eksport kalendarza PDF",

            str(default_path),

            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",

        )

        

        if file_path:

            try:

                export_production_calendar(data, Path(file_path).name)

                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.information(self, "Eksport", f"Kalendarz wyeksportowany do:\n{file_path}")

            except Exception as e:

                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.warning(self, "Błąd", f"Nie udało się wyeksportować:\n{str(e)}")



    def _get_day_name(self, d: date) -> str:

        """Get Polish day name."""

        days = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]

        return days[d.weekday()]



    def _get_next_month_start(self) -> date:

        """Get first day of next month."""

        first = self._current_month_start

        if first.month == 12:

            return date(first.year + 1, 1, 1)

        return date(first.year, first.month + 1, 1)



    def refresh_data(self) -> None:

        self._on_data_change()



