from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# Ikonka + krótka etykieta dla każdej grupy nawigacyjnej
# ---------------------------------------------------------------------------
_GROUP_META: dict[str, tuple[str, str]] = {
    "Sprzedaż": ("🛒", "Sprz."),
    "Uslugi":   ("🔧", "Usługi"),
    "Projekt":  ("📐", "Projekt"),
    "Finanse":  ("💼", "Fin."),
    "Operacje": ("🧭", "Oper."),
    "Firma":    ("🏢", "Firma"),
    "Bazy":     ("🗄", "Bazy"),
    "Ustawienia": ("⚙", "Ust."),
    "Inne":     ("⚙", "Inne"),
}

_SIDEBAR_W = 76   # szerokość sidebaru w pikselach
_ICON_SIZE  = 26  # rozmiar emoji-ikony (piksele)
_BTN_MIN_H  = 64  # minimalna wysokość przycisku grupy


def _make_emoji_icon(emoji: str, size: int = _ICON_SIZE) -> QIcon:
    """Renderuje emoji do QIcon gotowego do użycia w QToolButton."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    # Preferuj font z kolorem emoji (Windows: Segoe UI Emoji)
    for family in ("Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", ""):
        font = QFont(family)
        font.setPixelSize(size - 2)
        painter.setFont(font)
        break
    painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
    painter.end()
    return QIcon(pm)


def build_sidebar(window, groups: list[tuple[str, list[str]]]) -> QWidget:
    sidebar = QWidget()
    sidebar.setObjectName("Sidebar")
    sidebar.setFixedWidth(_SIDEBAR_W)

    layout = QVBoxLayout(sidebar)
    layout.setContentsMargins(0, 8, 0, 6)
    layout.setSpacing(0)

    # Logo / tytuł aplikacji
    title_lbl = QLabel("T")
    title_lbl.setObjectName("SidebarTitle")
    title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title_lbl)

    _divider(layout)
    layout.addSpacing(4)

    # ---- Przyciski grup nawigacyjnych ----
    window._group_buttons = []
    for g_idx, (group_name, _titles) in enumerate(groups):
        emoji, short_label = _GROUP_META.get(group_name, ("●", group_name[:6]))

        btn = QToolButton()
        btn.setObjectName("GroupBtn")
        btn.setIcon(_make_emoji_icon(emoji, _ICON_SIZE))
        btn.setIconSize(QSize(_ICON_SIZE, _ICON_SIZE))
        btn.setText(short_label)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn.setToolTip(group_name)
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setMinimumHeight(_BTN_MIN_H)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda checked, i=g_idx: window._set_active_group(i))

        layout.addWidget(btn)
        window._group_buttons.append(btn)

    layout.addStretch(1)

    # ---- Dolna sekcja: użytkownik ----
    _divider(layout)
    layout.addSpacing(4)

    window._user_label = QLabel("–")
    window._user_label.setObjectName("SidebarUserLabel")
    window._user_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window._user_label.setWordWrap(True)
    window._user_label.setStyleSheet("font-size: 9px; color: #888;")
    layout.addWidget(window._user_label)
    layout.addSpacing(2)

    window.btn_switch_user = QToolButton()
    window.btn_switch_user.setObjectName("SidebarSwitchUser")
    window.btn_switch_user.setText("👤")
    window.btn_switch_user.setToolTip("Zmień użytkownika")
    window.btn_switch_user.setMinimumHeight(28)
    window.btn_switch_user.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    window.btn_switch_user.clicked.connect(window._on_switch_user)
    layout.addWidget(window.btn_switch_user)
    layout.addSpacing(4)

    _divider(layout)
    layout.addSpacing(4)

    # ---- Nawigacja ← → ⌂ ----
    nav_row = QWidget()
    nav_layout = QHBoxLayout(nav_row)
    nav_layout.setContentsMargins(4, 0, 4, 0)
    nav_layout.setSpacing(4)

    window.btn_nav_back = QToolButton()
    window.btn_nav_back.setText("←")
    window.btn_nav_back.setToolTip("Wróć do poprzedniego kroku")
    window.btn_nav_back.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    window.btn_nav_back.clicked.connect(window._go_back)

    window.btn_nav_forward = QToolButton()
    window.btn_nav_forward.setText("→")
    window.btn_nav_forward.setToolTip("Przejdź dalej")
    window.btn_nav_forward.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    window.btn_nav_forward.clicked.connect(window._go_forward)

    nav_layout.addWidget(window.btn_nav_back)
    nav_layout.addWidget(window.btn_nav_forward)
    layout.addWidget(nav_row)

    window.btn_nav_home = QToolButton()
    window.btn_nav_home.setText("⌂")
    window.btn_nav_home.setToolTip("Wróć na ekran startowy")
    window.btn_nav_home.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    window.btn_nav_home.clicked.connect(window._go_home)

    home_wrapper = QWidget()
    home_layout = QHBoxLayout(home_wrapper)
    home_layout.setContentsMargins(4, 0, 4, 2)
    home_layout.addWidget(window.btn_nav_home)
    layout.addWidget(home_wrapper)

    return sidebar


def _divider(layout: QVBoxLayout) -> None:
    d = QLabel()
    d.setObjectName("SidebarDivider")
    d.setFixedHeight(1)
    layout.addWidget(d)
