from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QWidget


STEPS_ORDER = [
    "Klient",
    "Sciana",
    "Komplet",
    "Wycena",
]


class StepIndicator(QWidget):
    sig_step_clicked = pyqtSignal(str)

    def __init__(self, current_step: str = "Klient", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._steps = list(STEPS_ORDER)
        self._current = current_step
        self._completed: set[str] = set()

        container = QFrame(self)
        container.setObjectName("WizardStepContainer")
        container.setFrameShape(QFrame.Shape.NoFrame)
        container.setStyleSheet("""
            QFrame#WizardStepContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1e3a5f, stop:0.33 #2563eb, stop:0.66 #3b82f6, stop:1 #1e40af);
                border-radius: 10px;
                padding: 10px 16px;
            }
        """)

        root = QHBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._step_labels: list[QWidget] = []

        for i, step in enumerate(self._steps):
            item = _StepItem(step, i, container)
            item.sig_clicked.connect(self._on_step_click)
            root.addWidget(item, 0)
            self._step_labels.append(item)

            if i < len(self._steps) - 1:
                arrow = QLabel("›", container)
                arrow.setStyleSheet("""
                    color: rgba(255,255,255,0.6);
                    font-size: 22px;
                    font-weight: 700;
                    padding: 0 8px;
                """)
                arrow.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                root.addWidget(arrow, 0)

        root.addStretch(1)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(container, 1)

        self._refresh()

    def _on_step_click(self, step: str) -> None:
        if step in self._completed or step == self._current:
            self.sig_step_clicked.emit(step)

    def set_current(self, step: str) -> None:
        self._current = step
        self._refresh()

    def mark_completed(self, step: str) -> None:
        self._completed.add(step)
        self._refresh()

    def reset_completed(self) -> None:
        self._completed.clear()

    def _refresh(self) -> None:
        for item in self._step_labels:
            if isinstance(item, _StepItem):
                state: str
                if item._label == self._current:
                    state = "active"
                elif item._label in self._completed:
                    state = "done"
                else:
                    state = "pending"
                item._set_state(state)


class _StepItem(QWidget):
    sig_clicked = pyqtSignal(str)

    def __init__(self, label: str, index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = label
        self._index = index
        self._state = "pending"

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 4)
        root.setSpacing(8)

        self.badge = QLabel(str(index + 1), self)
        self.badge.setFixedSize(28, 28)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = self.badge.font()
        f.setPointSize(13)
        f.setWeight(QFont.Weight.Bold)
        self.badge.setFont(f)
        root.addWidget(self.badge, 0)

        self.name = QLabel(label, self)
        f2 = self.name.font()
        f2.setPointSize(14)
        f2.setWeight(QFont.Weight.DemiBold)
        self.name.setFont(f2)
        root.addWidget(self.name, 0)

        self.setStyleSheet("")
        self._apply_style()

    def _set_state(self, state: str) -> None:
        self._state = state
        self._apply_style()

    def _apply_style(self) -> None:
        s = self._state
        if s == "active":
            badge = "background:#ffffff; color:#1e3a5f; border-radius:14px;"
            text = "color:#ffffff; font-weight:800;"
            bg = "background: rgba(255,255,255,0.15); border-radius:6px;"
        elif s == "done":
            badge = "background:#10b981; color:#ffffff; border-radius:14px;"
            text = "color:#6ee7b7; font-weight:600;"
            bg = "background: transparent;"
        else:
            badge = "background:rgba(255,255,255,0.25); color:rgba(255,255,255,0.7); border-radius:14px;"
            text = "color:rgba(255,255,255,0.5); font-weight:500;"
            bg = "background: transparent;"

        self.setStyleSheet(f"QWidget {{ {bg} }}")
        self.badge.setStyleSheet(f"QLabel {{ {badge} }}")
        self.name.setStyleSheet(f"QLabel {{ {text} }}")
        if s == "done" or s == "active":
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if self._state == "done" or self._state == "active":
            self.sig_clicked.emit(self._label)
        super().mousePressEvent(event)
