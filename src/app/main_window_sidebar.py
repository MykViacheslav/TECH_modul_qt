from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


def build_sidebar(window, groups: list[tuple[str, list[str]]]) -> QWidget:
    sidebar = QWidget()
    sidebar.setObjectName("Sidebar")
    sidebar.setFixedWidth(148)

    layout = QVBoxLayout(sidebar)
    layout.setContentsMargins(0, 12, 0, 10)
    layout.setSpacing(0)

    title_lbl = QLabel("TECH")
    title_lbl.setObjectName("SidebarTitle")
    title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title_lbl)

    divider = QLabel()
    divider.setObjectName("SidebarDivider")
    divider.setFixedHeight(1)
    layout.addWidget(divider)
    layout.addSpacing(6)

    window._group_buttons = []
    for g_idx, (group_name, _titles) in enumerate(groups):
        btn = QPushButton(group_name)
        btn.setObjectName("GroupBtn")
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.clicked.connect(lambda checked, i=g_idx: window._set_active_group(i))
        layout.addWidget(btn)
        window._group_buttons.append(btn)

    layout.addStretch()

    # User info section
    divider_user = QLabel()
    divider_user.setObjectName("SidebarDivider")
    divider_user.setFixedHeight(1)
    layout.addWidget(divider_user)
    layout.addSpacing(4)
    
    # User info label
    window._user_label = QLabel("Brak logowania")
    window._user_label.setObjectName("SidebarUserLabel")
    window._user_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window._user_label.setWordWrap(True)
    window._user_label.setStyleSheet("font-size: 9px; color: #888;")
    layout.addWidget(window._user_label)
    layout.addSpacing(4)
    
    # Switch user button
    window.btn_switch_user = QPushButton("👤 Zmień")
    window.btn_switch_user.setObjectName("SidebarSwitchUser")
    window.btn_switch_user.setToolTip("Zmień użytkownika")
    window.btn_switch_user.setFixedHeight(26)
    window.btn_switch_user.clicked.connect(window._on_switch_user)
    switch_wrapper = QWidget()
    switch_layout = QHBoxLayout(switch_wrapper)
    switch_layout.setContentsMargins(8, 0, 8, 0)
    switch_layout.addWidget(window.btn_switch_user)
    layout.addWidget(switch_wrapper)
    layout.addSpacing(4)

    divider2 = QLabel()
    divider2.setObjectName("SidebarDivider")
    divider2.setFixedHeight(1)
    layout.addWidget(divider2)
    layout.addSpacing(6)

    nav_row = QWidget()
    nav_layout = QHBoxLayout(nav_row)
    nav_layout.setContentsMargins(8, 0, 8, 0)
    nav_layout.setSpacing(4)

    window.btn_nav_back = QPushButton("←")
    window.btn_nav_back.setFixedWidth(38)
    window.btn_nav_back.setToolTip("Wróć do poprzedniego kroku")
    window.btn_nav_back.clicked.connect(window._go_back)

    window.btn_nav_forward = QPushButton("→")
    window.btn_nav_forward.setFixedWidth(38)
    window.btn_nav_forward.setToolTip("Przejdź do następnego kroku")
    window.btn_nav_forward.clicked.connect(window._go_forward)

    nav_layout.addWidget(window.btn_nav_back)
    nav_layout.addWidget(window.btn_nav_forward)
    layout.addWidget(nav_row)

    window.btn_nav_home = QPushButton("⌂ Start")
    window.btn_nav_home.setToolTip("Wróć na ekran startowy")
    window.btn_nav_home.clicked.connect(window._go_home)
    home_wrapper = QWidget()
    home_layout = QHBoxLayout(home_wrapper)
    home_layout.setContentsMargins(8, 2, 8, 0)
    home_layout.addWidget(window.btn_nav_home)
    layout.addWidget(home_wrapper)

    return sidebar
