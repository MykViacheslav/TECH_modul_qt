from __future__ import annotations

import math
from datetime import date
from typing import Callable

from PyQt6.QtCore import QPoint, QRect, QRectF, Qt, QTimer, pyqtProperty
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from src.storage.company_expenses_store_json import CompanyExpensesStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.storage.worker_store_json import WorkerStoreJson
from src.storage.alarm_store_json import AlarmStoreJson
from src.storage.service_store_json import ServiceStoreJson


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(value: float) -> str:
    """Format PLN value with thousands separator."""
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f} M zł"
    if abs(value) >= 1_000:
        return f"{value:,.0f} zł".replace(",", " ")
    return f"{value:.0f} zł"


# ---------------------------------------------------------------------------
# KPI card with animated counter
# ---------------------------------------------------------------------------

class KpiCard(QFrame):
    def __init__(
        self,
        title: str,
        accent: str,
        icon: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._accent = accent
        self._target = 0.0
        self._displayed = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

        self.setFixedHeight(112)
        self.setMinimumWidth(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            f"QFrame {{background:#ffffff; border-radius:14px;"
            f"border-top:4px solid {accent}; border-left:1px solid #e2e8f0;"
            f"border-right:1px solid #e2e8f0; border-bottom:1px solid #e2e8f0;}}"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(4)

        top = QHBoxLayout()
        lab_title = QLabel(title)
        lab_title.setStyleSheet("font-size:11px;font-weight:700;color:#64748b;background:transparent;border:none;")
        top.addWidget(lab_title)
        top.addStretch()
        if icon:
            lab_icon = QLabel(icon)
            lab_icon.setStyleSheet(
                f"font-size:18px;background:{accent}18;border-radius:8px;"
                "padding:2px 6px;border:none;"
            )
            top.addWidget(lab_icon)
        lay.addLayout(top)

        self._lab_value = QLabel("0 zł")
        self._lab_value.setStyleSheet(
            "font-size:26px;font-weight:800;color:#0f172a;background:transparent;border:none;"
        )
        lay.addWidget(self._lab_value)

        self._lab_sub = QLabel("")
        self._lab_sub.setStyleSheet("font-size:11px;color:#94a3b8;background:transparent;border:none;")
        lay.addWidget(self._lab_sub)

    def set_value(self, value: float, sub: str = "", animate: bool = True) -> None:
        self._target = value
        self._lab_sub.setText(sub)
        if not animate or abs(value - self._displayed) < 1:
            self._displayed = value
            self._lab_value.setText(_fmt(value))
            return
        self._timer.start()

    def set_value_int(self, value: int, sub: str = "") -> None:
        self._lab_value.setText(str(value))
        self._lab_sub.setText(sub)

    def set_raw_text(self, text: str, sub: str = "") -> None:
        self._lab_value.setText(text)
        self._lab_sub.setText(sub)

    def _tick(self) -> None:
        diff = self._target - self._displayed
        if abs(diff) < 1:
            self._displayed = self._target
            self._lab_value.setText(_fmt(self._displayed))
            self._timer.stop()
            return
        self._displayed += diff * 0.15
        self._lab_value.setText(_fmt(self._displayed))


# ---------------------------------------------------------------------------
# Horizontal bar chart (orders by payment)
# ---------------------------------------------------------------------------

class HBarChart(QWidget):
    """Horizontal bar chart: one row per order, paid (green) + pending (amber)."""

    BAR_H = 22
    ROW_H = 34
    LABEL_W = 130
    RIGHT_PAD = 40

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data: list[tuple[str, float, float]] = []  # (label, paid, pending)
        self._hovered = -1
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data: list[tuple[str, float, float]]) -> None:
        self._data = data[:12]
        h = max(120, len(self._data) * self.ROW_H + 40)
        self.setMinimumHeight(h)
        self.update()

    def mouseMoveEvent(self, e) -> None:
        y = e.pos().y() - 20
        row = y // self.ROW_H
        if 0 <= row < len(self._data):
            if row != self._hovered:
                self._hovered = row
                self.update()
            label, paid, pending = self._data[row]
            tip = f"<b>{label}</b><br>Wpłacono: <b>{_fmt(paid)}</b><br>Oczekiwane: <b>{_fmt(pending)}</b>"
            QToolTip.showText(e.globalPosition().toPoint(), tip, self)
        else:
            self._hovered = -1
            self.update()

    def leaveEvent(self, e) -> None:
        self._hovered = -1
        self.update()

    def paintEvent(self, e) -> None:
        if not self._data:
            p = QPainter(self)
            p.setPen(QColor("#94a3b8"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Brak danych o płatnościach")
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        chart_w = w - self.LABEL_W - self.RIGHT_PAD
        max_val = max((paid + pending) for _, paid, pending in self._data) or 1.0

        for i, (label, paid, pending) in enumerate(self._data):
            y = 20 + i * self.ROW_H
            bar_y = y + (self.ROW_H - self.BAR_H) // 2

            # Hover highlight
            if i == self._hovered:
                p.fillRect(0, y, w, self.ROW_H, QColor("#f1f5f9"))

            # Label
            p.setPen(QColor("#1e293b"))
            p.setFont(QFont("", 9, QFont.Weight.Medium))
            label_rect = QRect(4, y, self.LABEL_W - 8, self.ROW_H)
            p.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       label[:18] + ("…" if len(label) > 18 else ""))

            total = paid + pending
            bar_total_w = int(chart_w * total / max_val)
            paid_w = int(bar_total_w * paid / total) if total > 0 else 0

            x0 = self.LABEL_W

            # Background track
            track = QRect(x0, bar_y, chart_w, self.BAR_H)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#f1f5f9"))
            p.drawRoundedRect(track, 4, 4)

            # Pending bar
            if total > 0:
                pend_rect = QRect(x0, bar_y, bar_total_w, self.BAR_H)
                p.setBrush(QColor("#fde68a"))
                p.drawRoundedRect(pend_rect, 4, 4)

            # Paid bar
            if paid_w > 0:
                paid_rect = QRect(x0, bar_y, paid_w, self.BAR_H)
                g = QLinearGradient(paid_rect.topLeft(), paid_rect.topRight())
                g.setColorAt(0, QColor("#16a34a"))
                g.setColorAt(1, QColor("#4ade80"))
                p.setBrush(QBrush(g))
                p.drawRoundedRect(paid_rect, 4, 4)

            # Value label
            p.setPen(QColor("#374151"))
            p.setFont(QFont("", 8))
            val_x = x0 + bar_total_w + 4
            p.drawText(QRect(val_x, bar_y, self.RIGHT_PAD + 20, self.BAR_H),
                       Qt.AlignmentFlag.AlignVCenter, _fmt(paid) if paid > 0 else "—")

        # Legend
        legend_y = self.height() - 18
        p.setFont(QFont("", 8))
        p.setBrush(QColor("#16a34a"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRect(self.LABEL_W, legend_y, 12, 10), 2, 2)
        p.setPen(QColor("#374151"))
        p.drawText(self.LABEL_W + 16, legend_y + 9, "Wpłacono")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#fde68a"))
        p.drawRoundedRect(QRect(self.LABEL_W + 90, legend_y, 12, 10), 2, 2)
        p.setPen(QColor("#374151"))
        p.drawText(self.LABEL_W + 106, legend_y + 9, "Oczekiwane")


# ---------------------------------------------------------------------------
# Donut chart
# ---------------------------------------------------------------------------

DONUT_COLORS = [
    "#2563eb", "#16a34a", "#d97706", "#dc2626",
    "#7c3aed", "#0891b2", "#65a30d", "#be185d",
    "#ea580c", "#475569",
]


class DonutChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data: list[tuple[str, float]] = []
        self._hovered = -1
        self.setMouseTracking(True)
        self.setMinimumSize(220, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data: list[tuple[str, float]]) -> None:
        self._data = [(lbl, val) for lbl, val in data if val > 0]
        self.update()

    def _hit_test(self, pos: QPoint) -> int:
        if not self._data:
            return -1
        total = sum(v for _, v in self._data)
        if total == 0:
            return -1
        cx = self.width() / 2
        cy = self.height() / 2
        r = min(cx, cy) * 0.85
        dx, dy = pos.x() - cx, pos.y() - cy
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < r * 0.45 or dist > r:
            return -1
        angle = math.degrees(math.atan2(dy, dx)) + 90
        if angle < 0:
            angle += 360
        start = 0.0
        for i, (_, val) in enumerate(self._data):
            span = 360.0 * val / total
            if start <= angle < start + span:
                return i
            start += span
        return -1

    def mouseMoveEvent(self, e) -> None:
        hit = self._hit_test(e.pos())
        if hit != self._hovered:
            self._hovered = hit
            self.update()
        if hit >= 0:
            lbl, val = self._data[hit]
            total = sum(v for _, v in self._data)
            pct = 100 * val / total if total > 0 else 0
            QToolTip.showText(
                e.globalPosition().toPoint(),
                f"<b>{lbl}</b><br>{_fmt(val)}  ({pct:.0f}%)",
                self,
            )

    def leaveEvent(self, e) -> None:
        self._hovered = -1
        self.update()

    def paintEvent(self, e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        if not self._data:
            p.setPen(QColor("#94a3b8"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Brak danych")
            return

        total = sum(v for _, v in self._data)
        if total == 0:
            return

        cx, cy = w / 2, h / 2
        r = min(cx, cy) * 0.82
        inner = r * 0.50

        start = -90.0
        for i, (lbl, val) in enumerate(self._data):
            span = 360.0 * val / total
            color = QColor(DONUT_COLORS[i % len(DONUT_COLORS)])
            explode = 4 if i == self._hovered else 0

            # Explode effect: shift slice outward
            mid_angle = math.radians(start + span / 2)
            ex = math.cos(mid_angle) * explode
            ey = math.sin(mid_angle) * explode

            rect = QRectF(cx - r + ex, cy - r + ey, 2 * r, 2 * r)

            path = QPainterPath()
            path.moveTo(cx + ex + inner * math.cos(math.radians(start)),
                        cy + ey + inner * math.sin(math.radians(start)))
            path.arcTo(rect, -start, -span)
            inner_rect = QRectF(cx - inner + ex, cy - inner + ey, 2 * inner, 2 * inner)
            path.arcTo(inner_rect, -(start + span), span)
            path.closeSubpath()

            p.setPen(QPen(QColor("#ffffff"), 2))
            p.setBrush(color.lighter(115) if i == self._hovered else color)
            p.drawPath(path)

            start += span

        # Center text
        p.setPen(QColor("#1e293b"))
        p.setFont(QFont("", 9, QFont.Weight.Bold))
        p.drawText(QRectF(cx - 40, cy - 18, 80, 18),
                   Qt.AlignmentFlag.AlignCenter, "Koszty")
        p.setFont(QFont("", 11, QFont.Weight.ExtraBold))
        p.drawText(QRectF(cx - 50, cy, 100, 20),
                   Qt.AlignmentFlag.AlignCenter, _fmt(total))


# ---------------------------------------------------------------------------
# Compact legend widget for donut
# ---------------------------------------------------------------------------

class ChartLegend(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 4)
        self._layout.setSpacing(4)

    def set_data(self, data: list[tuple[str, float]]) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        total = sum(v for _, v in data if v > 0)
        for i, (lbl, val) in enumerate(data):
            if val <= 0:
                continue
            row = QHBoxLayout()
            row.setSpacing(6)
            dot = QLabel("●")
            dot.setStyleSheet(
                f"color:{DONUT_COLORS[i % len(DONUT_COLORS)]};"
                "font-size:14px;background:transparent;"
            )
            dot.setFixedWidth(16)
            name = QLabel(lbl)
            name.setStyleSheet("font-size:11px;color:#374151;background:transparent;")
            name.setWordWrap(True)
            pct = f"{100 * val / total:.0f}%" if total > 0 else ""
            pct_lab = QLabel(pct)
            pct_lab.setStyleSheet("font-size:11px;color:#64748b;background:transparent;")
            pct_lab.setFixedWidth(36)
            row.addWidget(dot)
            row.addWidget(name, 1)
            row.addWidget(pct_lab)
            container = QWidget()
            container.setLayout(row)
            self._layout.addWidget(container)
        self._layout.addStretch()


# ---------------------------------------------------------------------------
# Section box
# ---------------------------------------------------------------------------

def _section(title: str, parent: QWidget | None = None) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame(parent)
    frame.setStyleSheet(
        "QFrame{background:#ffffff;border:1px solid #e2e8f0;border-radius:14px;}"
    )
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(16, 12, 16, 12)
    lay.setSpacing(8)
    lbl = QLabel(title)
    lbl.setStyleSheet(
        "font-size:13px;font-weight:800;color:#0f172a;background:transparent;border:none;"
    )
    lay.addWidget(lbl)
    return frame, lay


# ---------------------------------------------------------------------------
# Main tab
# ---------------------------------------------------------------------------

class TabDashboard(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        order_store: OrderStoreJson | None = None,
        expenses_store: CompanyExpensesStoreJson | None = None,
        worker_store: WorkerStoreJson | None = None,
    ) -> None:
        super().__init__(parent)
        self._order_store = order_store or OrderStoreJson()
        self._expenses_store = expenses_store or CompanyExpensesStoreJson()
        self._worker_store = worker_store or WorkerStoreJson()
        self._service_store = ServiceStoreJson()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        root = QVBoxLayout(content)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("DASHBOARD FIRMY")
        title.setStyleSheet("font-size:24px;font-weight:900;color:#0f172a;")
        sub = QLabel("Przegląd finansowy · zlecenia · koszty")
        sub.setStyleSheet("font-size:12px;color:#64748b;")
        left = QVBoxLayout()
        left.setSpacing(2)
        left.addWidget(title)
        left.addWidget(sub)
        hdr.addLayout(left, 1)
        self._btn_refresh = QPushButton("⟳  Odśwież")
        self._btn_refresh.setStyleSheet(
            "QPushButton{background:#0f172a;color:#fff;font-weight:700;padding:7px 18px;"
            "border-radius:8px;border:none;font-size:13px;}"
            "QPushButton:hover{background:#1e293b;}"
        )
        hdr.addWidget(self._btn_refresh)
        root.addLayout(hdr)

        # ── KPI cards ────────────────────────────────────────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        self._card_income = KpiCard("Wpłynęło od klientów", "#16a34a", "💰")
        self._card_pending = KpiCard("Oczekuje wpłaty", "#d97706", "⏳")
        self._card_costs = KpiCard("Koszty miesięczne", "#dc2626", "📉")
        self._card_real_hour = KpiCard("Realna rob.-godz.", "#7c3aed", "⏱️")
        self._card_orders = KpiCard("Aktywne zlecenia", "#2563eb", "📋")
        self._card_services = KpiCard("Uslugi z terminem", "#0891b2", "🧩")
        self._card_alarms_critical = KpiCard("Alarmy krytyczne", "#dc2626", "🚨")
        self._card_alarms_warning = KpiCard("Ostrzeżenia", "#d97706", "⚠️")
        for card in (
            self._card_income,
            self._card_pending,
            self._card_costs,
            self._card_real_hour,
            self._card_orders,
            self._card_services,
            self._card_alarms_critical,
            self._card_alarms_warning,
        ):
            kpi_row.addWidget(card, 1)
        root.addLayout(kpi_row)

        # ── Charts row ───────────────────────────────────────────────────────
        charts_row = QHBoxLayout()
        charts_row.setSpacing(12)

        # Bar chart section
        bar_frame, bar_lay = _section("Zlecenia · wpłaty klientów", content)
        bar_frame.setMinimumWidth(340)
        self._bar_chart = HBarChart(bar_frame)
        bar_lay.addWidget(self._bar_chart, 1)
        charts_row.addWidget(bar_frame, 3)

        # Donut + legend section
        donut_frame, donut_lay = _section("Struktura kosztów", content)
        donut_frame.setMinimumWidth(240)
        donut_inner = QHBoxLayout()
        donut_inner.setSpacing(8)
        self._donut = DonutChart(donut_frame)
        self._donut.setMinimumSize(180, 180)
        self._legend = ChartLegend(donut_frame)
        donut_inner.addWidget(self._donut, 1)
        donut_inner.addWidget(self._legend, 1)
        donut_lay.addLayout(donut_inner, 1)
        charts_row.addWidget(donut_frame, 2)

        root.addLayout(charts_row, 1)

        # ── Status breakdown ─────────────────────────────────────────────────
        status_frame, status_lay = _section("Zlecenia wg statusu", content)
        self._status_row = QHBoxLayout()
        self._status_row.setSpacing(10)
        status_lay.addLayout(self._status_row)
        root.addWidget(status_frame)

        # ── Workers row ──────────────────────────────────────────────────────
        workers_frame, workers_lay = _section("Pracownicy · zlecenia", content)
        self._workers_row = QHBoxLayout()
        self._workers_row.setSpacing(10)
        workers_lay.addLayout(self._workers_row)
        root.addWidget(workers_frame)

        root.addStretch()

        self._btn_refresh.clicked.connect(self.refresh_data)
        self.refresh_data()

    # ── Data loading ─────────────────────────────────────────────────────────

    def refresh_data(self) -> None:
        orders = self._order_store.list_orders()
        active = [o for o in orders if str(o.status or "").strip().lower() != "zakonczone"]

        # Payments
        total_paid = 0.0
        total_pending = 0.0
        order_payments: list[tuple[str, float, float]] = []
        for order in orders:
            paid = sum(
                float(p.get("amount", 0) or 0)
                for p in (order.customer_payments or [])
                if p.get("paid")
            )
            pending = sum(
                float(p.get("amount", 0) or 0)
                for p in (order.customer_payments or [])
                if not p.get("paid")
            )
            total_paid += paid
            total_pending += pending
            if paid + pending > 0:
                label = str(order.client_name or order.code or "—")
                order_payments.append((label, paid, pending))

        order_payments.sort(key=lambda x: x[1] + x[2], reverse=True)

        # Monthly costs
        fixed_items = self._expenses_store.list_items("fixed", [])
        variable_items = self._expenses_store.list_items("variable", [])
        fixed_total = sum(float(i.get("amount", 0) or 0) for i in fixed_items)
        variable_total = sum(float(i.get("amount", 0) or 0) for i in variable_items)
        monthly_costs = fixed_total + variable_total
        real_hour = self._expenses_store.real_hour_metrics(
            workers_fallback=max(1, len(self._worker_store.list_workers())),
            hours_fallback=160.0,
        )

        # Services
        services = self._service_store.list_services()
        total_services = len(services)
        with_deadline = 0
        overdue_services = 0
        today = date.today()
        for svc in services:
            deadline = str(getattr(svc, "deadline", "") or "").strip()
            if not deadline:
                continue
            try:
                due = date.fromisoformat(deadline)
            except ValueError:
                continue
            with_deadline += 1
            if due < today:
                overdue_services += 1

        # KPI cards
        self._card_income.set_value(total_paid, sub=f"{len([o for o in orders if any(p.get('paid') for p in o.customer_payments)])} zleceń z wpłatami")
        self._card_pending.set_value(total_pending, sub="do odebrania od klientów")
        self._card_costs.set_value(monthly_costs, sub=f"stałe {_fmt(fixed_total)} + zmienne {_fmt(variable_total)}")
        self._card_real_hour.set_raw_text(
            f"{float(real_hour.get('real_hour_rate', 0.0) or 0.0):.2f} zl/h",
            sub=f"{int(float(real_hour.get('workers_count', 0.0) or 0.0))} prac. x {float(real_hour.get('hours_per_worker', 0.0) or 0.0):.0f} h",
        )
        self._card_orders.set_value_int(len(active), sub=f"wszystkich: {len(orders)}")
        self._card_services.set_value_int(with_deadline, sub=f"po terminie: {overdue_services} / wszystkie: {total_services}")

        # Alarm cards
        try:
            from src.services.alarm_generator import AlarmGenerator
            AlarmGenerator().generate_all()
        except Exception:
            pass
        alarm_store = AlarmStoreJson()
        alarms = alarm_store.list_alarms()
        active_alarms = [a for a in alarms if not a.is_resolved]
        critical_count = len([a for a in active_alarms if a.severity == "krytyczny"])
        warning_count = len([a for a in active_alarms if a.severity == "ostrzezenie"])
        self._card_alarms_critical.set_value_int(critical_count, sub=f"aktywnych: {len(active_alarms)}")
        self._card_alarms_warning.set_value_int(warning_count, sub="wymaga uwagi")

        # Bar chart
        self._bar_chart.set_data(order_payments)

        # Donut — expense breakdown
        donut_data: list[tuple[str, float]] = []
        for item in fixed_items:
            name = str(item.get("name", "") or "")
            val = float(item.get("amount", 0) or 0)
            if val > 0:
                donut_data.append((name, val))
        for item in variable_items:
            name = str(item.get("name", "") or "")
            val = float(item.get("amount", 0) or 0)
            if val > 0:
                donut_data.append((name, val))
        donut_data.sort(key=lambda x: x[1], reverse=True)
        self._donut.set_data(donut_data)
        self._legend.set_data(donut_data)

        # Status breakdown
        self._rebuild_status_row(active)

        # Workers
        self._rebuild_workers_row(active)

    def _rebuild_status_row(self, active_orders: list) -> None:
        while self._status_row.count():
            item = self._status_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        status_counts: dict[str, int] = {}
        for order in active_orders:
            s = str(order.status or "Nowe").strip()
            status_counts[s] = status_counts.get(s, 0) + 1

        STATUS_COLORS = {
            "Nowe": "#64748b", "Wycena": "#0891b2", "Wycena gotowa": "#0891b2",
            "Zaakceptowane": "#7c3aed", "Zakup materialow": "#d97706",
            "Produkcja": "#2563eb", "Lakiernia": "#ea580c",
            "Montaz": "#16a34a", "Poprawki": "#dc2626",
        }

        for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
            color = STATUS_COLORS.get(status, "#475569")
            card = QFrame()
            card.setStyleSheet(
                f"QFrame{{background:{color}18;border:1px solid {color}44;"
                "border-radius:10px;padding:6px;}}"
            )
            lay = QVBoxLayout(card)
            lay.setContentsMargins(10, 6, 10, 6)
            lay.setSpacing(2)
            cnt_lab = QLabel(str(count))
            cnt_lab.setStyleSheet(f"font-size:22px;font-weight:800;color:{color};background:transparent;")
            cnt_lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_lab = QLabel(status)
            name_lab.setStyleSheet("font-size:10px;color:#374151;background:transparent;")
            name_lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_lab.setWordWrap(True)
            lay.addWidget(cnt_lab)
            lay.addWidget(name_lab)
            self._status_row.addWidget(card, 1)

        if not status_counts:
            self._status_row.addWidget(QLabel("Brak aktywnych zleceń"), 1)
        self._status_row.addStretch()

    def _rebuild_workers_row(self, active_orders: list) -> None:
        while self._workers_row.count():
            item = self._workers_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        worker_orders: dict[str, int] = {}
        for order in active_orders:
            name = str(order.worker_name or "— brak —").strip() or "— brak —"
            worker_orders[name] = worker_orders.get(name, 0) + 1

        for worker, count in sorted(worker_orders.items(), key=lambda x: -x[1]):
            card = QFrame()
            card.setStyleSheet(
                "QFrame{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;}"
            )
            lay = QVBoxLayout(card)
            lay.setContentsMargins(12, 8, 12, 8)
            lay.setSpacing(2)
            initials = "".join(w[0].upper() for w in worker.split()[:2]) or "?"
            av = QLabel(initials)
            av.setAlignment(Qt.AlignmentFlag.AlignCenter)
            av.setFixedSize(36, 36)
            av.setStyleSheet(
                "background:#2563eb;color:white;border-radius:18px;"
                "font-weight:800;font-size:13px;"
            )
            cnt = QLabel(f"{count} zleceń")
            cnt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cnt.setStyleSheet("font-size:11px;font-weight:700;color:#0f172a;background:transparent;")
            name_lab = QLabel(worker)
            name_lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_lab.setStyleSheet("font-size:10px;color:#64748b;background:transparent;")
            name_lab.setWordWrap(True)
            lay.addWidget(av, 0, Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(cnt)
            lay.addWidget(name_lab)
            self._workers_row.addWidget(card)

        if not worker_orders:
            self._workers_row.addWidget(QLabel("Brak przypisanych pracowników"))
        self._workers_row.addStretch()
