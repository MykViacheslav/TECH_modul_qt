from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.app.app_settings import load_ui_theme_settings
from src.app.alarm_tab_mapping import map_alarms_to_tabs
from src.app.main_window_sidebar import build_sidebar
from src.app.main_window_wiring import wire_cross_tab_signals
from src.app.navigation_groups import GROUPS
from src.domain.permissions import can_access_tab, has_permission, ROLE_LABELS, normalize_role
from src.services.alarm_generator import AlarmGenerator
from src.storage.alarm_store_json import AlarmStoreJson
from src.tabs.registry import build_tabs
from src.widgets.assistant_avatar import FloatingAssistantAvatar
from src.widgets.login_dialog import QuickSwitchDialog
from src.widgets.time_clock_kiosk import TimeClockKioskWindow


# ---------------------------------------------------------------------------
# Pomocnicze funkcje kolorów (bez zmian)
# ---------------------------------------------------------------------------

def _clamp_channel(value: float) -> int:
    return max(0, min(255, int(round(value))))


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    raw = str(color or "").strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        return (0, 0, 0)
    try:
        return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))
    except ValueError:
        return (0, 0, 0)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{_clamp_channel(r):02x}{_clamp_channel(g):02x}{_clamp_channel(b):02x}"


def _blend_hex(base: str, overlay: str, alpha: float) -> str:
    a = max(0.0, min(1.0, float(alpha)))
    br, bg, bb = _hex_to_rgb(base)
    or_, og, ob = _hex_to_rgb(overlay)
    out = (
        _clamp_channel(br * (1.0 - a) + or_ * a),
        _clamp_channel(bg * (1.0 - a) + og * a),
        _clamp_channel(bb * (1.0 - a) + ob * a),
    )
    return _rgb_to_hex(out)


def _theme_palette(mode: str, motif: str) -> dict[str, str]:
    mode_norm = str(mode or "day").strip().lower()
    motif_norm = str(motif or "cream").strip().lower()

    day_by_motif = {
        "cream": {
            "window_bg": "#f5f1ea",
            "pane_bg": "#fbf9f5",
            "tab_bg": "#efe8dc",
            "tab_hover": "#f6efe5",
            "text": "#243243",
            "btn_bg": "#fffdfa",
            "input_bg": "#fffdfa",
            "table_bg": "#ffffff",
            "header_bg": "#f1ebdf",
            "scroll_bg": "#f1ede6",
            "scroll_handle": "#cbbca2",
        },
        "blue": {
            "window_bg": "#eef4fb",
            "pane_bg": "#f7fbff",
            "tab_bg": "#e2ecf8",
            "tab_hover": "#d9e7f6",
            "text": "#1f3146",
            "btn_bg": "#fafdff",
            "input_bg": "#fafdff",
            "table_bg": "#ffffff",
            "header_bg": "#e8f0fb",
            "scroll_bg": "#e8eef8",
            "scroll_handle": "#a8bcd8",
        },
        "gray": {
            "window_bg": "#f2f3f5",
            "pane_bg": "#fafbfc",
            "tab_bg": "#e6e8eb",
            "tab_hover": "#dde0e4",
            "text": "#2a3340",
            "btn_bg": "#fdfefe",
            "input_bg": "#fdfefe",
            "table_bg": "#ffffff",
            "header_bg": "#eceef1",
            "scroll_bg": "#eceef1",
            "scroll_handle": "#b7bec8",
        },
        "green": {
            "window_bg": "#edf5ef",
            "pane_bg": "#f7fcf8",
            "tab_bg": "#dcecdf",
            "tab_hover": "#d2e6d6",
            "text": "#23352a",
            "btn_bg": "#fbfffc",
            "input_bg": "#fbfffc",
            "table_bg": "#ffffff",
            "header_bg": "#e5f1e8",
            "scroll_bg": "#e5efe7",
            "scroll_handle": "#a4c5ad",
        },
    }

    night_by_motif = {
        "cream": {
            "window_bg": "#2a2e35",
            "pane_bg": "#eef0f4",
            "tab_bg": "#d0d5de",
            "tab_hover": "#c4ccd8",
            "text": "#1e2b3a",
            "btn_bg": "#f5f7fa",
            "input_bg": "#ffffff",
            "table_bg": "#ffffff",
            "header_bg": "#e4e8ef",
            "scroll_bg": "#dde2ea",
            "scroll_handle": "#98a6bc",
        },
        "blue": {
            "window_bg": "#242c38",
            "pane_bg": "#edf2f9",
            "tab_bg": "#c8d4e6",
            "tab_hover": "#bccce2",
            "text": "#1a2d44",
            "btn_bg": "#f5f8fd",
            "input_bg": "#ffffff",
            "table_bg": "#ffffff",
            "header_bg": "#e1e9f5",
            "scroll_bg": "#dae4f3",
            "scroll_handle": "#8ea5c6",
        },
        "gray": {
            "window_bg": "#2b2f34",
            "pane_bg": "#eef1f5",
            "tab_bg": "#d2d8e0",
            "tab_hover": "#c6ced8",
            "text": "#202a36",
            "btn_bg": "#f6f8fb",
            "input_bg": "#ffffff",
            "table_bg": "#ffffff",
            "header_bg": "#e6ebf1",
            "scroll_bg": "#dee4ec",
            "scroll_handle": "#9aa7b8",
        },
        "green": {
            "window_bg": "#243129",
            "pane_bg": "#edf3ef",
            "tab_bg": "#c9d9ce",
            "tab_hover": "#bdd1c4",
            "text": "#213628",
            "btn_bg": "#f4faf6",
            "input_bg": "#ffffff",
            "table_bg": "#ffffff",
            "header_bg": "#e1ece5",
            "scroll_bg": "#d9e8de",
            "scroll_handle": "#8fb39a",
        },
    }

    palettes = night_by_motif if mode_norm == "night" else day_by_motif
    return palettes.get(motif_norm, palettes["cream"])


def _build_app_stylesheet(mode: str, motif: str) -> str:
    p = _theme_palette(mode, motif)
    is_night = str(mode).strip().lower() == "night"
    text_selected = "#10233f"
    selection_bg = "#c8d8f0" if is_night else "#d7e7ff"
    border_main = "#9aa7b8" if is_night else "#d8d1c4"
    border_soft = "#bcc6d3" if is_night else "#ddd5c8"
    button_border = "#a9b4c2" if is_night else "#d0c5b4"
    disabled_bg = "#e5e9ef" if is_night else "#f5f5f5"
    disabled_text = "#9aa4af"
    tab_selected_bg = _blend_hex(p["pane_bg"], p["scroll_handle"], 0.22 if is_night else 0.16)
    tab_selected_border = _blend_hex(border_soft, p["scroll_handle"], 0.58 if is_night else 0.45)
    tab_selected_bottom = _blend_hex(p["scroll_handle"], p["text"], 0.2 if is_night else 0.1)
    sidebar_bg = _blend_hex(p["window_bg"], p["tab_bg"], 0.85)
    sidebar_text = p["text"]
    sidebar_text_muted = p["text"]
    group_btn_hover_bg = _blend_hex(sidebar_bg, p["scroll_handle"], 0.22)
    group_btn_active_bg = _blend_hex(sidebar_bg, p["scroll_handle"], 0.50)
    group_btn_active_border = _blend_hex(p["scroll_handle"], p["text"], 0.35)
    group_btn_active_text = p["text"]
    return f"""
        QMainWindow {{
            background: {p["window_bg"]};
        }}
        /* ---- Sidebar ---- */
        QWidget#Sidebar {{
            background: {sidebar_bg};
            border-right: 2px solid {border_soft};
        }}
        QLabel#SidebarTitle {{
            color: {sidebar_text};
            font-weight: 800;
            font-size: 15px;
            padding: 4px 0px 8px 0px;
            letter-spacing: 1px;
        }}
        QLabel#SidebarDivider {{
            background: {border_soft};
            max-height: 1px;
            min-height: 1px;
        }}
        QPushButton#GroupBtn {{
            text-align: left;
            padding: 9px 14px;
            border: none;
            border-left: 4px solid transparent;
            border-radius: 0px;
            background: transparent;
            font-weight: 500;
            font-size: 13px;
            min-height: 40px;
            color: {sidebar_text_muted};
        }}
        QPushButton#GroupBtn:hover {{
            background: {group_btn_hover_bg};
            color: {sidebar_text};
        }}
        QPushButton#GroupBtn:checked {{
            background: {group_btn_active_bg};
            font-weight: 700;
            font-size: 13px;
            border-left: 4px solid {group_btn_active_border};
            color: {group_btn_active_text};
        }}
        /* ---- Zakładki w grupach ---- */
        QTabWidget::tab-bar {{
            alignment: left;
            left: 0px;
        }}
        QTabBar {{
            background: {p["pane_bg"]};
        }}
        QTabWidget::pane {{
            border: 1px solid {border_soft};
            background: {p["pane_bg"]};
            top: -1px;
        }}
        QTabBar::tab {{
            min-height: 36px;
            min-width: 70px;
            padding: 4px 12px;
            margin-right: 2px;
            border: 1px solid {border_soft};
            border-bottom: 2px solid transparent;
            border-radius: 7px;
            background: {p["pane_bg"]};
            color: {p["text"]};
            font-weight: 500;
        }}
        QTabBar::tab:selected {{
            background: {tab_selected_bg};
            color: {p["text"]};
            border: 1px solid {tab_selected_border};
            border-bottom: 2px solid {tab_selected_bottom};
            font-weight: 650;
        }}
        QTabBar::tab:hover:!selected {{
            background: {p["tab_hover"]};
            border-color: {border_soft};
        }}
        QTabWidget::right-corner {{
            background: {p["pane_bg"]};
            border: none;
        }}
        QTabBar::scroller {{
            width: 54px;
            background: {p["pane_bg"]};
            border: none;
        }}
        QTabBar QToolButton {{
            min-width: 24px;
            max-width: 24px;
            min-height: 30px;
            max-height: 30px;
            margin: 0 2px;
            padding: 0;
            border: 1px solid {border_soft};
            border-radius: 7px;
            background: {p["btn_bg"]};
            color: {p["text"]};
        }}
        QTabBar QToolButton:hover {{
            background: {p["tab_hover"]};
            border-color: {p["scroll_handle"]};
        }}
        QTabBar QToolButton:disabled {{
            background: {disabled_bg};
            color: {disabled_text};
            border-color: {border_soft};
        }}
        /* ---- Ogólne widgety ---- */
        QWidget {{
            selection-background-color: {selection_bg};
            selection-color: {text_selected};
            color: {p["text"]};
        }}
        QLabel {{
            color: {p["text"]};
        }}
        QPushButton,
        QComboBox,
        QLineEdit,
        QSpinBox,
        QDoubleSpinBox,
        QTextEdit,
        QPlainTextEdit,
        QListWidget,
        QTreeWidget,
        QTableWidget {{
            font-size: 13px;
        }}
        QPushButton,
        QComboBox,
        QLineEdit,
        QSpinBox,
        QDoubleSpinBox {{
            min-height: 34px;
            border-radius: 10px;
        }}
        QPushButton {{
            padding: 4px 12px;
            border: 1px solid {button_border};
            background: {p["btn_bg"]};
            color: {p["text"]};
            font-weight: 600;
        }}
        QPushButton:hover {{
            background: {p["tab_hover"]};
            border-color: {p["scroll_handle"]};
        }}
        QPushButton:disabled {{
            color: {disabled_text};
            background: {disabled_bg};
            border-color: {border_soft};
        }}
        QComboBox,
        QLineEdit,
        QSpinBox,
        QDoubleSpinBox,
        QTextEdit,
        QPlainTextEdit {{
            border: 1px solid {border_soft};
            background: {p["input_bg"]};
            padding: 4px 8px;
            color: {p["text"]};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QAbstractItemView,
        QListWidget,
        QTreeWidget,
        QTableWidget {{
            border: 1px solid {border_soft};
            background: {p["table_bg"]};
            alternate-background-color: {p["input_bg"]};
            gridline-color: {border_soft};
        }}
        QHeaderView::section {{
            min-height: 28px;
            padding: 5px 8px;
            background: {p["header_bg"]};
            color: {p["text"]};
            border: none;
            border-right: 1px solid {border_soft};
            border-bottom: 1px solid {border_soft};
            font-weight: 700;
        }}
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollBar:vertical {{
            width: 12px;
            background: {p["scroll_bg"]};
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {p["scroll_handle"]};
            min-height: 24px;
            border-radius: 6px;
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical,
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical,
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal,
        QScrollBar::add-page:horizontal,
        QScrollBar::sub-page:horizontal {{
            background: transparent;
            border: none;
        }}
    """


def _apply_accessible_ui_scale(mode: str = "day", motif: str = "cream") -> None:
    app = QApplication.instance()
    if app is None:
        return

    if not bool(app.property("_tech_modul_accessible_scale_applied")):
        base_font = QFont(app.font())
        point_size = base_font.pointSizeF()
        if point_size <= 0:
            point_size = 9.0
        base_font.setPointSizeF(max(point_size * 1.18, 11.5))
        app.setFont(base_font)
        app.setProperty("_tech_modul_accessible_scale_applied", True)

    app.setStyleSheet(_build_app_stylesheet(mode, motif))


# ---------------------------------------------------------------------------
# Compat shim — dla testów używających w.tabs.currentWidget() itp.
# ---------------------------------------------------------------------------

class _TabsCompat:
    """Pozwala starym testom używać w.tabs.currentWidget() / setCurrentWidget()."""

    def __init__(self, window: "MainWindow") -> None:
        self._w = window

    def currentWidget(self) -> QWidget | None:
        g = self._w._active_group
        if g < 0 or g >= len(self._w._group_tabwidgets):
            return None
        return self._w._group_tabwidgets[g].currentWidget()

    def setCurrentWidget(self, widget: QWidget) -> None:
        for title, w in self._w._tabs_by_title.items():
            if w is widget:
                self._w._navigate_to_tab(title)
                return


# ---------------------------------------------------------------------------
# Główne okno
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        theme = load_ui_theme_settings()
        _apply_accessible_ui_scale(theme.mode, theme.motif)
        self.setWindowTitle("TECH_modul")
        self.resize(1560, 980)

        # Mapowania: tytuł → widget i tytuł → lokalizacja w grupie
        self._tabs_by_title: dict[str, QWidget] = {}
        self._tab_title_to_group: dict[str, int] = {}
        self._tab_title_to_local_idx: dict[str, int] = {}
        self._group_tabwidgets: list[QTabWidget] = []
        self._active_group: int = 0
        self._sidebar_visible: bool = True
        self._time_kiosk_window: TimeClockKioskWindow | None = None

        # Historia nawigacji (lista tytułów zakładek)
        self._nav_history: list[str] = []
        self._nav_history_pos: int = -1
        self._is_history_navigation: bool = False
        
        # Current user info (set via set_current_user after login)
        self._current_worker: str = ""
        self._current_role: str = "produkcja"

        # Układ: sidebar (lewo) + content stack (prawo)
        self._theme_mode = theme.mode
        self._theme_motif = theme.motif

        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._sidebar = self._build_sidebar()
        main_layout.addWidget(self._sidebar)

        self.btn_sidebar_toggle = QPushButton("◀")
        self.btn_sidebar_toggle.setFixedWidth(22)
        self.btn_sidebar_toggle.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.btn_sidebar_toggle.clicked.connect(self._toggle_sidebar_visibility)
        main_layout.addWidget(self.btn_sidebar_toggle)

        self._content_stack = QStackedWidget(central)
        main_layout.addWidget(self._content_stack, 1)

        # Zbierz wszystkie zakładki (z obsługą błędów)
        try:
            tabs_list = build_tabs()
            for title, widget in tabs_list:
                self._tabs_by_title[title] = widget
        except Exception as e:
            print(f"Warning building tabs: {e}")
            # Fallback - create at least Start tab
            from src.tabs.start.tab_start import TabStart
            self._tabs_by_title["Start"] = TabStart()

        # Utwórz QTabWidget dla każdej grupy
        for g_idx, (group_name, tab_titles) in enumerate(GROUPS):
            gtw = QTabWidget()
            gtw.tabBar().setExpanding(True)
            gtw.tabBar().setMovable(False)
            gtw.tabBar().setUsesScrollButtons(False)
            gtw.tabBar().setCursor(Qt.CursorShape.PointingHandCursor)
            gtw.setIconSize(QSize(14, 14))
            self._group_tabwidgets.append(gtw)
            self._content_stack.addWidget(gtw)
            for tab_title in tab_titles:
                widget = self._tabs_by_title.get(tab_title)
                if widget is not None:
                    local_idx = gtw.addTab(widget, tab_title)
                    self._tab_title_to_group[tab_title] = g_idx
                    self._tab_title_to_local_idx[tab_title] = local_idx
            gtw.currentChanged.connect(
                lambda idx, g=g_idx: self._on_group_tab_changed(g, idx)
            )

        # Awatar asystenta
        self.assistant_avatar = FloatingAssistantAvatar(self)
        self.assistant_avatar.say("Hej! Jestem tutaj.", 2600)

        # Ustaw kolory przycisków sidebaru przez QPalette (obejście Windows platform style)
        self._refresh_sidebar_button_colors()
        self._refresh_sidebar_toggle_button()

        # Aktywuj pierwszą grupę (Sprzedaż → Start)
        self._set_active_group(0)

        first_group_titles = GROUPS[0][1]
        if first_group_titles:
            self._nav_history = [first_group_titles[0]]
            self._nav_history_pos = 0

        self._update_navigation_buttons()
        self._wire_cross_tab_signals()

        # ------ ALARMY I BACKUP (opóźnione) ------
        # Wszystkie cięższe inicjalizacje są opóźnione aby uniknąć crasha
        QTimer.singleShot(2000, self._init_services_delayed)
    
    def _init_services_delayed(self) -> None:
        """Initialize heavy services after window is shown."""
        try:
            # Alarm store
            self._alarm_store = AlarmStoreJson()
            self._alarm_store.alarms_changed.connect(self._refresh_all_tab_badges)
            
            # Alarm refresh timer (every 2 minutes)
            self._alarm_refresh_timer = QTimer(self)
            self._alarm_refresh_timer.setInterval(120000)
            self._alarm_refresh_timer.timeout.connect(self._run_alarm_engine)
            self._alarm_refresh_timer.start()
            
            # Initial alarm check
            self._run_alarm_engine()
            self._refresh_all_tab_badges()
            
            # Backup service
            from src.services.backup_service import BackupService
            self._backup_service = BackupService.instance()
            self._backup_service.backup_created.connect(self._on_backup_created)
            self._backup_service.backup_error.connect(self._on_backup_error)
        except Exception as e:
            print(f"Delayed init warning: {e}")

        # Compat dla testów
        self.tabs = _TabsCompat(self)
    
    def _on_backup_created(self, path: str) -> None:
        """Handle backup created."""
        if hasattr(self, "statusBar") and self.statusBar():
            self.statusBar().showMessage(f"✓ Backup utworzony: {path}", 5000)
    
    def _on_backup_error(self, error: str) -> None:
        """Handle backup error."""
        if hasattr(self, "statusBar") and self.statusBar():
            self.statusBar().showMessage(f"⚠ Błąd backupu: {error}", 10000)
    
    def _on_critical_alarm(self, alarm) -> None:
        """Handle new critical alarm - show notification."""
        if hasattr(self, "statusBar") and self.statusBar():
            self.statusBar().showMessage(f"🚨 ALARM: {alarm.title}", 10000)
        self._refresh_all_tab_badges()
    
    def _on_warning_alarm(self, alarm) -> None:
        """Handle new warning - update badges."""
        if hasattr(self, "statusBar") and self.statusBar():
            self.statusBar().showMessage(f"⚠ Ostrzeżenie: {alarm.title}", 5000)
        self._refresh_all_tab_badges()
    
    # ------------------------------------------------------------------
    # Użytkownik i uprawnienia
    # ------------------------------------------------------------------
    
    def set_current_user(self, worker_name: str, role: str) -> None:
        """
        Set the current logged-in user and their role.
        Called after successful login.
        
        Args:
            worker_name: Name of the logged-in worker
            role: User role
        """
        self._current_worker = str(worker_name or "").strip()
        self._current_role = normalize_role(str(role or "produkcja"))
        
        # Update window title with user info
        role_label = ROLE_LABELS.get(self._current_role, self._current_role)
        self.setWindowTitle(f"TECH_modul - {self._current_worker} ({role_label})")
        
        # Update sidebar user label
        if hasattr(self, "_user_label"):
            self._user_label.setText(f"{self._current_worker}\n({role_label})")
        
        # Apply permission-based tab visibility
        self._apply_role_permissions()
        
        # Show welcome message
        if hasattr(self, "statusBar") and self.statusBar():
            self.statusBar().showMessage(
                f"Witaj, {self._current_worker}! Rola: {role_label}", 5000
            )
    
    def get_current_user(self) -> tuple[str, str]:
        """Get current user info as (worker_name, role)."""
        return (self._current_worker, self._current_role)
    
    def _apply_role_permissions(self) -> None:
        """Hide/disable tabs and buttons based on user role."""
        # Hide tabs that user cannot access
        for tab_title, group_idx in self._tab_title_to_group.items():
            local_idx = self._tab_title_to_local_idx.get(tab_title, -1)
            if local_idx < 0:
                continue
            
            gtw = self._group_tabwidgets[group_idx]
            if local_idx < gtw.count():
                can_access = can_access_tab(self._current_role, tab_title)
                # We can't hide tabs easily in QTabWidget, so we'll disable them
                widget = gtw.widget(local_idx)
                if widget:
                    widget.setEnabled(can_access)
        
        # Update sidebar buttons visibility
        self._refresh_sidebar_permissions()
    
    def _refresh_sidebar_permissions(self) -> None:
        """Update sidebar button states based on current role."""
        if not hasattr(self, "_group_buttons"):
            return
        
        for idx, btn in enumerate(self._group_buttons):
            group_name, tab_titles = GROUPS[idx]
            # Check if user can access any tab in this group
            can_access_group = any(
                can_access_tab(self._current_role, title) for title in tab_titles
            )
            btn.setEnabled(can_access_group)
    
    def _on_switch_user(self) -> None:
        """Show dialog to switch to a different user."""
        dialog = QuickSwitchDialog(self._current_worker, self)
        dialog.worker_selected.connect(self.set_current_user)
        dialog.exec()

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    def _build_sidebar(self) -> QWidget:
        return build_sidebar(self, GROUPS)

    def _refresh_sidebar_toggle_button(self) -> None:
        if not hasattr(self, "btn_sidebar_toggle"):
            return
        if self._sidebar_visible:
            self.btn_sidebar_toggle.setText("◀")
            self.btn_sidebar_toggle.setToolTip("Ukryj lewy pasek aplikacji")
        else:
            self.btn_sidebar_toggle.setText("▶")
            self.btn_sidebar_toggle.setToolTip("Pokaz lewy pasek aplikacji")

    def _toggle_sidebar_visibility(self) -> None:
        self._sidebar_visible = not self._sidebar_visible
        if hasattr(self, "_sidebar"):
            self._sidebar.setVisible(self._sidebar_visible)
        self._refresh_sidebar_toggle_button()

    # ------------------------------------------------------------------
    # Nawigacja grupami
    # ------------------------------------------------------------------

    def _set_active_group(self, g_idx: int) -> None:
        if g_idx < 0 or g_idx >= len(self._group_tabwidgets):
            return
        self._active_group = g_idx
        self._content_stack.setCurrentIndex(g_idx)
        for i, btn in enumerate(self._group_buttons):
            btn.setChecked(i == g_idx)
        self._update_navigation_buttons()

    def _navigate_to_tab(self, title: str) -> None:
        g_idx = self._tab_title_to_group.get(title)
        if g_idx is None:
            return
        local_idx = self._tab_title_to_local_idx.get(title)
        if local_idx is None:
            return
        self._set_active_group(g_idx)
        gtw = self._group_tabwidgets[g_idx]
        if gtw.currentIndex() == local_idx:
            # setCurrentIndex nie emituje currentChanged gdy indeks się nie zmienia
            self._on_group_tab_changed(g_idx, local_idx)
        else:
            gtw.setCurrentIndex(local_idx)

    def _current_tab_title(self) -> str | None:
        if self._active_group < 0 or self._active_group >= len(self._group_tabwidgets):
            return None
        gtw = self._group_tabwidgets[self._active_group]
        local_idx = gtw.currentIndex()
        if local_idx < 0:
            return None
        return gtw.tabText(local_idx)

    def _on_group_tab_changed(self, group_idx: int, local_idx: int) -> None:
        if local_idx < 0:
            return
        # Ignoruj zmiany z grup nieaktywnych (np. przy przełączaniu grupy)
        if group_idx != self._active_group:
            return
        gtw = self._group_tabwidgets[group_idx]
        title = gtw.tabText(local_idx)

        if self._is_history_navigation:
            self._update_navigation_buttons()
            return

        if self._nav_history_pos >= 0 and self._nav_history[self._nav_history_pos] == title:
            self._update_navigation_buttons()
            return

        if self._nav_history_pos < len(self._nav_history) - 1:
            self._nav_history = self._nav_history[: self._nav_history_pos + 1]

        self._nav_history.append(title)
        self._nav_history_pos = len(self._nav_history) - 1
        self._update_navigation_buttons()
        QTimer.singleShot(120, self._run_alarm_engine)

    # ------------------------------------------------------------------
    # Przyciski nawigacji (< > Start)
    # ------------------------------------------------------------------

    def _go_back(self) -> None:
        if self._nav_history_pos <= 0:
            return
        self._nav_history_pos -= 1
        self._is_history_navigation = True
        try:
            self._navigate_to_tab(self._nav_history[self._nav_history_pos])
        finally:
            self._is_history_navigation = False
        self._update_navigation_buttons()

    def _go_forward(self) -> None:
        if self._nav_history_pos >= len(self._nav_history) - 1:
            return
        self._nav_history_pos += 1
        self._is_history_navigation = True
        try:
            self._navigate_to_tab(self._nav_history[self._nav_history_pos])
        finally:
            self._is_history_navigation = False
        self._update_navigation_buttons()

    def _go_home(self) -> None:
        self._navigate_to_tab("Start")

    def _update_navigation_buttons(self) -> None:
        can_go_back = self._nav_history_pos > 0
        can_go_forward = 0 <= self._nav_history_pos < len(self._nav_history) - 1
        is_start = self._current_tab_title() == "Start"
        self.btn_nav_back.setEnabled(can_go_back)
        self.btn_nav_forward.setEnabled(can_go_forward)
        self.btn_nav_home.setEnabled(not is_start)

    # ------------------------------------------------------------------
    # Połączenia sygnałów między zakładkami (bez zmian w logice)
    # ------------------------------------------------------------------

    def _wire_cross_tab_signals(self) -> None:
        wire_cross_tab_signals(self)

    # ------------------------------------------------------------------
    # Metody otwierające konkretne zakładki
    # ------------------------------------------------------------------

    def _open_module_in_modul(self, module_name: str) -> None:
        tab = self._tabs_by_title.get("Modul")
        if tab is None or not hasattr(tab, "load_module_from_store_name"):
            return
        if bool(tab.load_module_from_store_name(str(module_name or ""))):
            self._navigate_to_tab("Modul")

    def _open_wall_in_sciana(self, wall_name: str) -> None:
        tab = self._tabs_by_title.get("Sciana")
        if tab is None or not hasattr(tab, "load_wall_from_store_name"):
            return
        if bool(tab.load_wall_from_store_name(str(wall_name or ""))):
            self._navigate_to_tab("Sciana")

    def _open_assembly_in_komplet(self, assembly_name: str) -> None:
        tab = self._tabs_by_title.get("Komplet")
        if tab is None or not hasattr(tab, "load_assembly_from_store_name"):
            return
        if bool(tab.load_assembly_from_store_name(str(assembly_name or ""))):
            self._navigate_to_tab("Komplet")

    def _open_new_module(self) -> None:
        tab = self._tabs_by_title.get("Modul")
        if tab is None:
            return
        if hasattr(tab, "start_new_module"):
            tab.start_new_module()
        self._navigate_to_tab("Modul")

    def _open_quote(self) -> None:
        self._navigate_to_tab("Wycena")

    def _open_work_time(self) -> None:
        self._navigate_to_tab("Czas pracy")

    def _open_time_kiosk(self) -> None:
        if self._time_kiosk_window is None:
            self._time_kiosk_window = TimeClockKioskWindow()
        self._time_kiosk_window.show()
        self._time_kiosk_window.raise_()
        self._time_kiosk_window.activateWindow()

    def _open_calendar(self, target_date: str | None = None) -> None:
        self._navigate_to_tab("Kalendarz")
        if target_date:
            from datetime import date
            try:
                d = date.fromisoformat(str(target_date).strip())
                tab = self._tabs_by_title.get("Kalendarz")
                if tab is not None and hasattr(tab, "open_with_date"):
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(50, lambda: tab.open_with_date(d))
            except (ValueError, AttributeError):
                pass
        tab = self._tabs_by_title.get("Kalendarz")
        if tab is not None and hasattr(tab, "refresh_data"):
            tab.refresh_data()

    def _open_new_wall(self, context: dict | None = None) -> None:
        tab = self._tabs_by_title.get("Sciana")
        if tab is None:
            return
        if context and hasattr(tab, "start_new_wall_from_order_context"):
            tab.start_new_wall_from_order_context(context)
        elif hasattr(tab, "start_new_wall"):
            tab.start_new_wall()
        self._navigate_to_tab("Sciana")

    def _open_new_assembly(self, context: dict | None = None) -> None:
        tab = self._tabs_by_title.get("Komplet")
        if tab is None:
            return
        if context and hasattr(tab, "start_new_assembly_from_wall_context"):
            tab.start_new_assembly_from_wall_context(context)
        elif hasattr(tab, "start_new_assembly"):
            tab.start_new_assembly()
        self._navigate_to_tab("Komplet")

    def _open_new_order(self, context: dict | None = None) -> None:
        tab = self._tabs_by_title.get("Nowe zamowienie")
        if tab is None:
            return
        if context and hasattr(tab, "start_new_order_from_context"):
            tab.start_new_order_from_context(context)
        elif hasattr(tab, "show_new_order_launcher"):
            tab.show_new_order_launcher()
        self._navigate_to_tab("Nowe zamowienie")

    def _open_clients_in_bazy(self) -> None:
        tab = self._tabs_by_title.get("Bazy")
        if tab is not None and hasattr(tab, "open_clients_tab"):
            tab.open_clients_tab(clear_form=False)
        self._navigate_to_tab("Bazy")

    def _open_orders_in_bazy(self) -> None:
        tab = self._tabs_by_title.get("Bazy")
        if tab is not None and hasattr(tab, "open_orders_tab"):
            tab.open_orders_tab(clear_form=False)
        self._navigate_to_tab("Bazy")

    def _open_workers_in_bazy(self) -> None:
        tab = self._tabs_by_title.get("Bazy")
        if tab is not None and hasattr(tab, "open_workers_tab"):
            tab.open_workers_tab(clear_form=False)
        self._navigate_to_tab("Bazy")

    def _open_bazy(self) -> None:
        self._navigate_to_tab("Bazy")

    def _open_settings(self) -> None:
        self._navigate_to_tab("Ustawienia")

    def _apply_ui_theme(self, mode: str, motif: str) -> None:
        self._theme_mode = str(mode or "day")
        self._theme_motif = str(motif or "cream")
        _apply_accessible_ui_scale(self._theme_mode, self._theme_motif)
        self._refresh_sidebar_button_colors()

    def _refresh_sidebar_button_colors(self) -> None:
        """Ustawia kolor tekstu przycisków sidebar przez QPalette — obejście Windows platform style."""
        if not hasattr(self, "_group_buttons"):
            return
        p = _theme_palette(self._theme_mode, self._theme_motif)
        text_color = QColor(p["text"])
        for btn in self._group_buttons:
            pal = btn.palette()
            pal.setColor(QPalette.ColorGroup.Normal,   QPalette.ColorRole.ButtonText, text_color)
            pal.setColor(QPalette.ColorGroup.Active,   QPalette.ColorRole.ButtonText, text_color)
            pal.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.ButtonText, text_color)
            btn.setPalette(pal)

    # ------------------------------------------------------------------
    # Alarmy na zakładkach
    # ------------------------------------------------------------------

    def _refresh_all_tab_badges(self) -> None:
        """Odświeża wskaźniki alarmów (badge'i) na wszystkich zakładkach."""
        if not hasattr(self, "_alarm_store"):
            return

        # Pobierz wszystkie alarmy i filtruj tylko nierozwiązane
        all_alarms = self._alarm_store.list_alarms()
        active_alarms = [a for a in all_alarms if not a.is_resolved]

        # Zmapuj alarmy na zakładki - otrzymaj {tab_title: count}
        tab_alarm_counts = map_alarms_to_tabs(active_alarms)
        
        # Zlicz alarmy wg严重ności dla każdej zakładki
        from src.domain.alarm_models import ALARM_CATEGORIES
        
        # Pobierz krytyczne i ostrzeżenia
        critical_alarms = [a for a in active_alarms if a.severity == "krytyczny"]
        warning_alarms = [a for a in active_alarms if a.severity == "ostrzezenie"]
        
        critical_tab_counts = map_alarms_to_tabs(critical_alarms)
        warning_tab_counts = map_alarms_to_tabs(warning_alarms)

        # Dla każdej grupy zakładek i każdego taba, ustaw odpowiedni tekst i kolor
        for g_idx, gtw in enumerate(self._group_tabwidgets):
            tabBar = gtw.tabBar()
            for local_idx in range(gtw.count()):
                # Odszukaj tytuł zakładki
                tab_title = None
                for title, group_idx in self._tab_title_to_group.items():
                    if group_idx == g_idx and self._tab_title_to_local_idx.get(title) == local_idx:
                        tab_title = title
                        break

                if tab_title is None:
                    continue

                # Pobierz liczbę alarmów dla tej zakładki
                alarm_count = tab_alarm_counts.get(tab_title, 0)
                critical_count = critical_tab_counts.get(tab_title, 0)
                warning_count = warning_tab_counts.get(tab_title, 0)

                # Ustaw tekst taba z badge'em i kolorem
                if alarm_count > 0:
                    # Badge z ikoną odpowiednią do严重ności
                    if critical_count > 0:
                        badge_text = f"🔴 {tab_title} [{alarm_count}]"
                        # Czerwony kolor dla krytycznych
                        tabBar.setTabTextColor(local_idx, QColor("#ff1744"))
                    elif warning_count > 0:
                        badge_text = f"🟡 {tab_title} [{alarm_count}]"
                        # Żółty kolor dla ostrzeżeń
                        tabBar.setTabTextColor(local_idx, QColor("#ffab00"))
                    else:
                        badge_text = f"🔵 {tab_title} [{alarm_count}]"
                        # Niebieski kolor dla informacji
                        tabBar.setTabTextColor(local_idx, QColor("#2196f3"))
                    
                    tabBar.setTabText(local_idx, badge_text)
                else:
                    # Przywróć normalny kolor
                    tabBar.setTabText(local_idx, tab_title)
                    tabBar.setTabTextColor(local_idx, QColor("#000000"))
        
        # Odśwież też główny sidebar - aktualizuj stan przycisków
        self._refresh_sidebar_permissions()

    def _run_alarm_engine(self) -> None:
        try:
            AlarmGenerator().generate_all()
        except Exception:
            pass
