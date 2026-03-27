from __future__ import annotations

import math
import random
from typing import Optional

from PyQt6.QtCore import QEvent, QPoint, QRect, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.widgets.notification_scanner import Alert, scan_alerts


class _NotificationPanel(QFrame):
    """Panel z listą alertów — pokazuje się obok avatara."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("notificationPanel")
        self.setStyleSheet(
            """
            QFrame#notificationPanel {
                background: rgba(255, 255, 255, 245);
                border: 1px solid #d1d5db;
                border-radius: 16px;
            }
            """
        )
        self.setFixedWidth(280)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Nagłówek
        header = QLabel("Powiadomienia")
        header.setStyleSheet(
            "font-size: 13px; font-weight: 800; color: #1f2937;"
            "padding: 12px 16px 8px 16px;"
        )
        outer.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #e5e7eb;")
        outer.addWidget(sep)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setMaximumHeight(340)
        outer.addWidget(self._scroll)

        self._content = QWidget()
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(12, 8, 12, 12)
        self._layout.setSpacing(8)
        self._scroll.setWidget(self._content)

        self.hide()

    def set_alerts(self, alerts: list[Alert]) -> None:
        # Wyczyść poprzednie
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        if not alerts:
            lbl = QLabel("Wszystko gra! Brak alertów.")
            lbl.setStyleSheet("font-size: 12px; color: #6b7280; padding: 8px 4px;")
            lbl.setWordWrap(True)
            self._layout.addWidget(lbl)
        else:
            for alert in alerts:
                card = self._make_card(alert)
                self._layout.addWidget(card)

        self._layout.addStretch(1)
        self._content.adjustSize()
        self.adjustSize()

    def _make_card(self, alert: Alert) -> QFrame:
        colors = {
            "error": ("#fee2e2", "#dc2626", "#1f2937"),
            "warning": ("#fef3c7", "#d97706", "#1f2937"),
            "info": ("#eff6ff", "#2563eb", "#1f2937"),
        }
        bg, accent, text = colors.get(alert.level, ("#f9fafb", "#6b7280", "#1f2937"))

        card = QFrame()
        card.setStyleSheet(
            f"""
            QFrame {{
                background: {bg};
                border: 1px solid {accent}40;
                border-left: 3px solid {accent};
                border-radius: 10px;
            }}
            """
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(3)

        title_lbl = QLabel(alert.icon + " " + alert.title)
        title_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {text};"
            "background: transparent; border: none;"
        )
        title_lbl.setWordWrap(True)
        lay.addWidget(title_lbl)

        if alert.detail:
            detail_lbl = QLabel(alert.detail)
            detail_lbl.setStyleSheet(
                f"font-size: 11px; color: #6b7280; background: transparent; border: none;"
            )
            detail_lbl.setWordWrap(True)
            lay.addWidget(detail_lbl)

        return card


class FloatingAssistantAvatar(QWidget):
    """
    Mały, przeciągany asystent po ekranie aplikacji.

    Funkcje:
    - siedzi w prawym dolnym rogu,
    - można go przeciągać myszką,
    - delikatnie "oddycha" / unosi się,
    - pokazuje dymek z tekstem,
    - reaguje na kliknięcie — wyświetla panel z alertami,
    - czerwona odznaka z liczbą alertów,
    - dwuklik przypina go z powrotem do rogu,
    - skanuje dane co 5 minut.
    """

    _SCAN_INTERVAL_MS = 5 * 60 * 1_000   # 5 minut
    _GREET_DELAY_MS   = 2_500             # opóźnienie pierwszego komunikatu

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self.setObjectName("floatingAssistantAvatar")
        self.setFixedSize(96, 96)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setMouseTracking(True)

        self._press_pos_local = QPoint()
        self._press_pos_parent = QPoint()
        self._dragging = False
        self._docked = True

        self._phase = 0.0
        self._pulse = 0.0
        self._bob = 0.0

        self._alerts: list[Alert] = []
        self._alert_index = 0           # do cyklowania po alertach

        # Dymek tekstowy
        self._bubble = QLabel(parent)
        self._bubble.setObjectName("floatingAssistantBubble")
        self._bubble.setWordWrap(True)
        self._bubble.setMinimumWidth(140)
        self._bubble.setMaximumWidth(260)
        self._bubble.setStyleSheet(
            """
            QLabel#floatingAssistantBubble {
                background: rgba(255, 255, 255, 235);
                color: #1f2937;
                border: 1px solid rgba(31, 41, 55, 40);
                border-radius: 14px;
                padding: 10px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            """
        )
        self._bubble.hide()

        self._bubble_timer = QTimer(self)
        self._bubble_timer.setSingleShot(True)
        self._bubble_timer.timeout.connect(self._bubble.hide)

        # Panel z alertami
        self._panel = _NotificationPanel(parent)
        self._panel.hide()

        # Animacja
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start(40)

        # Skanowanie powiadomień
        self._scan_timer = QTimer(self)
        self._scan_timer.timeout.connect(self._run_scan)
        self._scan_timer.start(self._SCAN_INTERVAL_MS)

        # Pierwsze powitanie + skan po uruchomieniu
        QTimer.singleShot(self._GREET_DELAY_MS, self._on_startup)

        parent.installEventFilter(self)
        self.move_to_corner()
        self.show()

    # ------------------------------------------------------------------
    # Publiczne API
    # ------------------------------------------------------------------

    def say(self, text: str, timeout_ms: int = 3000) -> None:
        self._panel.hide()
        self._bubble.setText(str(text or "").strip())
        self._bubble.adjustSize()
        self._reposition_bubble()
        self._bubble.show()
        self._bubble.raise_()
        self.raise_()

        self._bubble_timer.stop()
        if timeout_ms > 0:
            self._bubble_timer.start(timeout_ms)

    def move_to_corner(self, margin: int = 18) -> None:
        parent = self.parentWidget()
        if parent is None:
            return

        x = max(margin, parent.width() - self.width() - margin)
        y = max(margin, parent.height() - self.height() - margin)
        self.move(x, y)
        self._reposition_bubble()

    # ------------------------------------------------------------------
    # Skanowanie alertów
    # ------------------------------------------------------------------

    def _on_startup(self) -> None:
        self._run_scan()
        count = len(self._alerts)
        if count == 0:
            self.say("Cześć! Wszystko gra. 👋", 3000)
        elif count == 1:
            self.say(self._alerts[0].short(), 4000)
        else:
            self.say(f"Mam {count} powiadomień — kliknij mnie!", 4000)

    def _run_scan(self) -> None:
        try:
            self._alerts = scan_alerts()
        except Exception:
            self._alerts = []
        self._alert_index = 0
        self.update()   # odśwież odznakę

    # ------------------------------------------------------------------
    # Zdarzenia Qt
    # ------------------------------------------------------------------

    def eventFilter(self, watched: object, event: Optional[QEvent]) -> bool:
        if watched is self.parentWidget() and event is not None:
            if event.type() in (
                QEvent.Type.Resize,
                QEvent.Type.Show,
                QEvent.Type.WindowStateChange,
            ):
                if self._docked:
                    self.move_to_corner()
                else:
                    self._clamp_inside_parent()
                    self._reposition_bubble()
                self._reposition_panel()
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos_local = event.position().toPoint()
            self._press_pos_parent = self.mapToParent(event.position().toPoint())
            self._dragging = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return

        parent = self.parentWidget()
        if parent is None:
            super().mouseMoveEvent(event)
            return

        current_parent_pos = self.mapToParent(event.position().toPoint())
        delta = current_parent_pos - self._press_pos_parent

        if not self._dragging and delta.manhattanLength() >= 6:
            self._dragging = True
            self._docked = False
            self._panel.hide()

        if self._dragging:
            new_pos = current_parent_pos - self._press_pos_local
            self.move(new_pos)
            self._clamp_inside_parent()
            self._reposition_bubble()
            self._reposition_panel()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            was_dragging = self._dragging
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self._reposition_bubble()

            if not was_dragging:
                self._on_click()

            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._docked = True
            self._panel.hide()
            self.move_to_corner()
            self.say("Przypinam się z powrotem do rogu.", 2200)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    # ------------------------------------------------------------------
    # Animacja
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        self._phase += 0.18
        if self._phase > 10_000:
            self._phase = 0.0

        self._pulse = math.sin(self._phase) * 2.5
        self._bob = math.sin(self._phase * 0.75) * 2.0
        self.update()

        if not self._dragging:
            self._reposition_bubble()

    # ------------------------------------------------------------------
    # Kliknięcie — panel alertów lub dymek
    # ------------------------------------------------------------------

    def _on_click(self) -> None:
        if self._panel.isVisible():
            self._panel.hide()
            return

        self._bubble.hide()
        self._bubble_timer.stop()

        if not self._alerts:
            # Brak alertów → odśwież i pokaż komunikat
            self._run_scan()
            if not self._alerts:
                self.say(random.choice([
                    "Wszystko gra! Brak alertów.",
                    "Nic pilnego. Dobra robota!",
                    "Brak problemów. Pracujcie spokojnie.",
                ]), 3000)
                return

        # Pokaż panel
        self._panel.set_alerts(self._alerts)
        self._reposition_panel()
        self._panel.show()
        self._panel.raise_()
        self.raise_()

    # ------------------------------------------------------------------
    # Pozycjonowanie
    # ------------------------------------------------------------------

    def _clamp_inside_parent(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return

        x = min(max(0, self.x()), max(0, parent.width() - self.width()))
        y = min(max(0, self.y()), max(0, parent.height() - self.height()))
        if x != self.x() or y != self.y():
            self.move(x, y)

    def _reposition_bubble(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return

        self._bubble.adjustSize()

        gap = 10
        bubble_x = self.x() - self._bubble.width() - gap
        bubble_y = self.y() - 4

        if bubble_x < 8:
            bubble_x = self.x() + self.width() + gap

        if bubble_x + self._bubble.width() > parent.width() - 8:
            bubble_x = max(8, parent.width() - self._bubble.width() - 8)

        if bubble_y < 8:
            bubble_y = 8

        if bubble_y + self._bubble.height() > parent.height() - 8:
            bubble_y = max(8, parent.height() - self._bubble.height() - 8)

        self._bubble.move(bubble_x, bubble_y)

    def _reposition_panel(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return

        self._panel.adjustSize()
        gap = 10

        # Próbuj po lewej stronie avatara
        panel_x = self.x() - self._panel.width() - gap
        panel_y = self.y() + self.height() - self._panel.height()

        if panel_x < 8:
            panel_x = self.x() + self.width() + gap

        if panel_x + self._panel.width() > parent.width() - 8:
            panel_x = max(8, parent.width() - self._panel.width() - 8)

        if panel_y < 8:
            panel_y = 8

        if panel_y + self._panel.height() > parent.height() - 8:
            panel_y = max(8, parent.height() - self._panel.height() - 8)

        self._panel.move(panel_x, panel_y)

    # ------------------------------------------------------------------
    # Rysowanie
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Cień
        shadow_rect = QRectF(18, 64, 56, 14)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 35))
        painter.drawEllipse(shadow_rect)

        # Ciało
        body_rect = QRectF(14, 10 + self._bob, 68 + self._pulse, 68 + self._pulse)
        body_rect.moveLeft((self.width() - body_rect.width()) / 2)
        body_rect.moveTop(8 + self._bob)

        path = QPainterPath()
        path.addEllipse(body_rect)

        painter.setPen(QPen(QColor("#1f2937"), 2))
        body_color = QColor("#ef4444") if self._alerts else QColor("#60a5fa")
        painter.setBrush(body_color)
        painter.drawPath(path)

        inner_rect = QRectF(
            body_rect.left() + 7,
            body_rect.top() + 7,
            body_rect.width() - 14,
            body_rect.height() - 14,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 28))
        painter.drawEllipse(inner_rect)

        # Oczy
        eye_y = body_rect.top() + body_rect.height() * 0.42
        left_eye_x = body_rect.left() + body_rect.width() * 0.38
        right_eye_x = body_rect.left() + body_rect.width() * 0.62

        painter.setBrush(QColor("#111827"))
        painter.drawEllipse(QRectF(left_eye_x - 3, eye_y - 3, 6, 6))
        painter.drawEllipse(QRectF(right_eye_x - 3, eye_y - 3, 6, 6))

        # Usta
        painter.setPen(QPen(QColor("#111827"), 2))
        mouth_rect = QRectF(
            body_rect.left() + body_rect.width() * 0.34,
            body_rect.top() + body_rect.height() * 0.50,
            body_rect.width() * 0.32,
            body_rect.height() * 0.20,
        )
        # Gdy są alerty — usta w dół (smutna mina), bez alertów — uśmiech
        if self._alerts:
            painter.drawArc(mouth_rect, 30 * 16, 120 * 16)
        else:
            painter.drawArc(mouth_rect, 210 * 16, 120 * 16)

        # Odznaka — liczba alertów lub "AI"
        badge_rect = QRect(56, 6, 32, 20)
        alert_count = len(self._alerts)

        if alert_count > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#dc2626"))
            painter.drawRoundedRect(badge_rect, 10, 10)
            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, str(alert_count))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#2563eb"))
            painter.drawRoundedRect(QRect(8, 8, 26, 18), 8, 8)
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            painter.drawText(QRect(8, 8, 26, 18), Qt.AlignmentFlag.AlignCenter, "AI")
