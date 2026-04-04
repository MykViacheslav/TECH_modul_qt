from __future__ import annotations

from PyQt6.QtCore import QEvent, QPoint, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.app.app_settings import load_ui_font_scale, load_ui_theme_settings, save_ui_theme_settings
from src.app.alarm_tab_mapping import map_alarms_to_tabs
from src.app.main_window_sidebar import build_sidebar
from src.app.main_window_wiring import wire_cross_tab_signals
from src.app.navigation_groups import GROUPS
from src.domain.permissions import can_access_tab, has_permission, ROLE_LABELS, normalize_role
from src.services.alarm_generator import AlarmGenerator
from src.storage.alarm_store_json import AlarmStoreJson
from src.storage.access_control_store_json import AccessControlStoreJson
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
            "muted": "#5a6b7a",
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
            "muted": "#5a6b7a",
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
            "muted": "#5a6b7a",
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
            "muted": "#4a6354",
            "btn_bg": "#fbfffc",
            "input_bg": "#fbfffc",
            "table_bg": "#ffffff",
            "header_bg": "#e5f1e8",
            "scroll_bg": "#e5efe7",
            "scroll_handle": "#a4c5ad",
        },
        "contrast": {
            "window_bg": "#f7f9fc",
            "pane_bg": "#ffffff",
            "tab_bg": "#e5ecf7",
            "tab_hover": "#d7e3f3",
            "text": "#0f172a",
            "muted": "#475569",
            "btn_bg": "#ffffff",
            "input_bg": "#ffffff",
            "table_bg": "#ffffff",
            "header_bg": "#dce5f3",
            "scroll_bg": "#e2e8f0",
            "scroll_handle": "#1d4ed8",
        },
        "tech": {
            "window_bg": "#e8eef8",
            "pane_bg": "#f4f7fd",
            "tab_bg": "#e1e9f7",
            "tab_hover": "#d7e2f5",
            "text": "#12243e",
            "muted": "#64748b",
            "btn_bg": "#f7faff",
            "input_bg": "#ffffff",
            "table_bg": "#ffffff",
            "header_bg": "#e4ecfa",
            "scroll_bg": "#dfe8f8",
            "scroll_handle": "#2f6feb",
        },
    }

    night_by_motif = {
        "cream": {
            "window_bg": "#2a2e35",
            "pane_bg": "#eef0f4",
            "tab_bg": "#d0d5de",
            "tab_hover": "#c4ccd8",
            "text": "#1e2b3a",
            "muted": "#7a8a9a",
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
            "muted": "#6b7c8f",
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
            "muted": "#6b7785",
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
            "muted": "#5a7a64",
            "btn_bg": "#f4faf6",
            "input_bg": "#ffffff",
            "table_bg": "#ffffff",
            "header_bg": "#e1ece5",
            "scroll_bg": "#d9e8de",
            "scroll_handle": "#8fb39a",
        },
        "contrast": {
            "window_bg": "#0b1220",
            "pane_bg": "#0f172a",
            "tab_bg": "#1e293b",
            "tab_hover": "#334155",
            "text": "#f8fafc",
            "muted": "#94a3b8",
            "btn_bg": "#1f2937",
            "input_bg": "#111827",
            "table_bg": "#0f172a",
            "header_bg": "#1e293b",
            "scroll_bg": "#0b1220",
            "scroll_handle": "#f59e0b",
        },
        "tech": {
            "window_bg": "#0b1120",
            "pane_bg": "#10172a",
            "tab_bg": "#15213a",
            "tab_hover": "#1c2c49",
            "text": "#e8efff",
            "muted": "#94a3b8",
            "btn_bg": "#16223a",
            "input_bg": "#0f1a2f",
            "table_bg": "#0d172a",
            "header_bg": "#1a2843",
            "scroll_bg": "#0a1324",
            "scroll_handle": "#2f6feb",
        },
    }

    palettes = night_by_motif if mode_norm == "night" else day_by_motif
    return palettes.get(motif_norm, palettes.get("tech", palettes["cream"]))


def _build_app_stylesheet(mode: str, motif: str, ui_scale: float = 1.0) -> str:
    p = _theme_palette(mode, motif)
    is_night = str(mode).strip().lower() == "night"
    is_contrast = str(motif).strip().lower() == "contrast"
    is_tech = str(motif).strip().lower() == "tech"
    scale = max(0.68, min(1.0, float(ui_scale or 1.0)))

    def px(value: float, floor: int = 1) -> int:
        return max(int(floor), int(round(float(value) * scale)))

    text_selected = "#0f172a" if is_contrast else ("#e8efff" if is_tech else "#10233f")
    selection_bg = "#f59e0b" if (is_contrast and is_night) else ("#93c5fd" if is_contrast else ("#244f99" if is_tech else ("#c8d8f0" if is_night else "#d7e7ff")))
    border_main = "#64748b" if is_contrast else ("#31527e" if is_tech else ("#9aa7b8" if is_night else "#d8d1c4"))
    border_soft = "#64748b" if is_contrast else ("#2a4368" if is_tech else ("#bcc6d3" if is_night else "#ddd5c8"))
    button_border = "#94a3b8" if is_contrast else ("#355b8f" if is_tech else ("#a9b4c2" if is_night else "#d0c5b4"))
    disabled_bg = "#e5e9ef" if is_night else "#f5f5f5"
    disabled_text = "#9aa4af"
    focus_ring = "#f59e0b" if is_contrast else ("#5fa4ff" if is_tech else ("#f59e0b" if is_night else "#1d4ed8"))
    tab_selected_bg = _blend_hex(p["pane_bg"], p["scroll_handle"], 0.22 if is_night else 0.16)
    tab_selected_border = _blend_hex(border_soft, p["scroll_handle"], 0.58 if is_night else 0.45)
    tab_selected_bottom = _blend_hex(p["scroll_handle"], p["text"], 0.2 if is_night else 0.1)
    sidebar_bg = _blend_hex(p["window_bg"], p["tab_bg"], 0.88 if is_tech else 0.85)
    sidebar_text = p["text"]
    sidebar_text_muted = p["text"]
    group_btn_hover_bg = _blend_hex(sidebar_bg, p["scroll_handle"], 0.28 if is_tech else 0.22)
    group_btn_active_bg = _blend_hex(sidebar_bg, p["scroll_handle"], 0.56 if is_tech else 0.50)
    group_btn_active_border = _blend_hex(p["scroll_handle"], p["text"], 0.35)
    group_btn_active_text = p["text"]
    sidebar_title_font = px(15, 8)
    sidebar_title_pad_top = px(4, 1)
    sidebar_title_pad_bottom = px(8, 2)
    group_btn_pad_v = px(8, 2)
    group_btn_pad_h = px(4, 2)
    group_btn_border_left = px(4, 1)
    group_btn_font = px(10, 6)
    group_btn_min_h = px(64, 36)
    tab_min_h = px(36, 18)
    tab_min_w = px(70, 30)
    tab_pad_v = px(4, 1)
    tab_pad_h = px(12, 3)
    tab_margin_r = px(2, 1)
    tab_radius = px(7, 2)
    tab_bottom_border = px(2, 1)
    scroller_width = px(54, 22)
    tab_tool_w = px(24, 12)
    tab_tool_h = px(30, 16)
    tab_tool_margin = px(2, 1)
    common_font = px(13, 7)
    control_min_h = px(34, 18)
    control_radius = px(10, 4)
    button_pad_v = px(4, 1)
    button_pad_h = px(12, 3)
    input_pad_v = px(4, 1)
    input_pad_h = px(8, 3)
    combo_drop_w = px(24, 12)
    header_min_h = px(28, 16)
    header_pad_v = px(5, 1)
    header_pad_h = px(8, 3)
    scroll_w = px(12, 6)
    scroll_margin = px(2, 1)
    scroll_handle_h = px(24, 10)
    scroll_handle_radius = px(6, 2)
    card_bg = _blend_hex(p["pane_bg"], p["btn_bg"], 0.72 if is_tech else (0.65 if is_night else 0.78))
    card_border = _blend_hex(border_soft, p["scroll_handle"], 0.34 if is_tech else (0.28 if is_night else 0.18))
    primary_bg = _blend_hex(p["scroll_handle"], "#2f6feb", 0.68 if is_tech else 0.58)
    primary_hover = _blend_hex(primary_bg, "#ffffff", 0.14 if is_night else 0.10)
    success_bg = _blend_hex(p["scroll_handle"], "#1f9d66", 0.62)
    success_hover = _blend_hex(success_bg, "#ffffff", 0.10)
    danger_bg = _blend_hex(p["scroll_handle"], "#c2413b", 0.64)
    danger_hover = _blend_hex(danger_bg, "#ffffff", 0.09)
    ghost_bg = _blend_hex(p["btn_bg"], p["scroll_handle"], 0.10)
    ghost_hover = _blend_hex(ghost_bg, p["scroll_handle"], 0.18)
    accent_border = _blend_hex(button_border, p["scroll_handle"], 0.45)
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
            font-size: {sidebar_title_font}px;
            padding: {sidebar_title_pad_top}px 0px {sidebar_title_pad_bottom}px 0px;
            letter-spacing: 1px;
        }}
        QLabel#SidebarDivider {{
            background: {border_soft};
            max-height: 1px;
            min-height: 1px;
        }}
        QToolButton#GroupBtn {{
            text-align: center;
            padding: {group_btn_pad_v}px 2px;
            border: none;
            border-left: {group_btn_border_left}px solid transparent;
            border-radius: 0px;
            background: transparent;
            font-weight: 500;
            font-size: {group_btn_font}px;
            min-height: {group_btn_min_h}px;
            min-width: 72px;
            color: {sidebar_text_muted};
        }}
        QToolButton#GroupBtn:hover {{
            background: {group_btn_hover_bg};
            color: {sidebar_text};
        }}
        QToolButton#GroupBtn:checked {{
            background: {group_btn_active_bg};
            font-weight: 700;
            font-size: {group_btn_font}px;
            border-left: {group_btn_border_left}px solid {group_btn_active_border};
            color: {group_btn_active_text};
        }}
        QToolButton#SidebarSwitchUser,
        QWidget#Sidebar QToolButton {{
            background: transparent;
            border: none;
            border-radius: 4px;
            color: {sidebar_text_muted};
            font-size: {group_btn_font}px;
            padding: 2px 4px;
        }}
        QToolButton#SidebarSwitchUser:hover,
        QWidget#Sidebar QToolButton:hover {{
            background: {group_btn_hover_bg};
            color: {sidebar_text};
        }}
        QToolButton#SidebarSwitchUser:pressed,
        QWidget#Sidebar QToolButton:pressed {{
            background: {group_btn_active_bg};
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
            min-height: {tab_min_h}px;
            min-width: {tab_min_w}px;
            padding: {tab_pad_v}px {tab_pad_h}px;
            margin-right: {tab_margin_r}px;
            border: 1px solid {border_soft};
            border-bottom: {tab_bottom_border}px solid transparent;
            border-radius: {tab_radius}px;
            background: {p["tab_bg"]};
            color: {p["text"]};
            font-weight: 500;
        }}
        QTabBar::tab:selected {{
            background: {tab_selected_bg};
            color: {p["text"]};
            border: 1px solid {tab_selected_border};
            border-bottom: {tab_bottom_border}px solid {tab_selected_bottom};
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
            width: {scroller_width}px;
            background: {p["pane_bg"]};
            border: none;
        }}
        QTabBar QToolButton {{
            min-width: {tab_tool_w}px;
            max-width: {tab_tool_w}px;
            min-height: {tab_tool_h}px;
            max-height: {tab_tool_h}px;
            margin: 0 {tab_tool_margin}px;
            padding: 0;
            border: 1px solid {border_soft};
            border-radius: {tab_radius}px;
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
            font-size: {common_font}px;
        }}
        QPushButton,
        QComboBox,
        QLineEdit,
        QSpinBox,
        QDoubleSpinBox {{
            min-height: {control_min_h}px;
            border-radius: {control_radius}px;
        }}
        QPushButton {{
            padding: {button_pad_v}px {button_pad_h}px;
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
        QWidget[uiCard="true"] {{
            border: 1px solid {card_border};
            border-radius: {control_radius + 4}px;
            background: {card_bg};
        }}
        QLabel[uiMuted="true"] {{
            color: {p["muted"]};
        }}
        QPushButton[uiVariant="primary"],
        QToolButton[uiVariant="primary"] {{
            background: {primary_bg};
            color: #ffffff;
            border: 1px solid {accent_border};
            font-weight: 700;
        }}
        QPushButton[uiVariant="primary"]:hover,
        QToolButton[uiVariant="primary"]:hover {{
            background: {primary_hover};
            border-color: {primary_hover};
        }}
        QPushButton[uiVariant="success"],
        QToolButton[uiVariant="success"] {{
            background: {success_bg};
            color: #ffffff;
            border: 1px solid {accent_border};
            font-weight: 700;
        }}
        QPushButton[uiVariant="success"]:hover,
        QToolButton[uiVariant="success"]:hover {{
            background: {success_hover};
            border-color: {success_hover};
        }}
        QPushButton[uiVariant="danger"],
        QToolButton[uiVariant="danger"] {{
            background: {danger_bg};
            color: #ffffff;
            border: 1px solid {accent_border};
            font-weight: 700;
        }}
        QPushButton[uiVariant="danger"]:hover,
        QToolButton[uiVariant="danger"]:hover {{
            background: {danger_hover};
            border-color: {danger_hover};
        }}
        QPushButton[uiVariant="ghost"],
        QToolButton[uiVariant="ghost"] {{
            background: {ghost_bg};
            color: {p["text"]};
            border: 1px solid {button_border};
            font-weight: 650;
        }}
        QPushButton[uiVariant="ghost"]:hover,
        QToolButton[uiVariant="ghost"]:hover {{
            background: {ghost_hover};
            border-color: {p["scroll_handle"]};
        }}
        QPushButton[uiVariant="ghost"]:checked,
        QToolButton[uiVariant="ghost"]:checked {{
            background: {_blend_hex(ghost_bg, p["scroll_handle"], 0.26)};
            border-color: {p["scroll_handle"]};
            color: {p["text"]};
            font-weight: 700;
        }}
        QPushButton[uiVariant="success"]:checked,
        QToolButton[uiVariant="success"]:checked {{
            background: {_blend_hex(success_bg, "#0b3d2a", 0.18)};
            border-color: {_blend_hex(accent_border, "#0b3d2a", 0.22)};
            color: #ffffff;
            font-weight: 700;
        }}
        QPushButton[uiVariant="primary"]:checked,
        QToolButton[uiVariant="primary"]:checked {{
            background: {_blend_hex(primary_bg, "#12336d", 0.20)};
            border-color: {_blend_hex(accent_border, "#12336d", 0.22)};
            color: #ffffff;
            font-weight: 700;
        }}
        QComboBox,
        QLineEdit,
        QSpinBox,
        QDoubleSpinBox,
        QTextEdit,
        QPlainTextEdit {{
            border: 1px solid {border_soft};
            background: {p["input_bg"]};
            padding: {input_pad_v}px {input_pad_h}px;
            color: {p["text"]};
        }}
        QComboBox::drop-down {{
            border: none;
            width: {combo_drop_w}px;
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
            min-height: {header_min_h}px;
            padding: {header_pad_v}px {header_pad_h}px;
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
            width: {scroll_w}px;
            background: {p["scroll_bg"]};
            margin: {scroll_margin}px;
        }}
        QScrollBar::handle:vertical {{
            background: {p["scroll_handle"]};
            min-height: {scroll_handle_h}px;
            border-radius: {scroll_handle_radius}px;
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
        QPushButton:focus,
        QComboBox:focus,
        QLineEdit:focus,
        QSpinBox:focus,
        QDoubleSpinBox:focus,
        QTextEdit:focus,
        QPlainTextEdit:focus,
        QListWidget:focus,
        QTreeWidget:focus,
        QTableWidget:focus,
        QTabBar::tab:focus {{
            border: 2px solid {focus_ring};
            outline: 0;
        }}
    """


def _apply_accessible_ui_scale(mode: str = "night", motif: str = "tech") -> None:
    app = QApplication.instance()
    if app is None:
        return

    base_size_prop = app.property("_tech_modul_base_font_size")
    if base_size_prop is None:
        current_size = QFont(app.font()).pointSizeF()
        if current_size <= 0:
            current_size = 9.5
        app.setProperty("_tech_modul_base_font_size", float(current_size))
        base_size = float(current_size)
    else:
        try:
            base_size = float(base_size_prop)
        except Exception:
            base_size = 9.5

    screen = app.primaryScreen()
    if screen is not None:
        geo = screen.availableGeometry()
        width = max(800, int(geo.width()))
        height = max(600, int(geo.height()))
        ratio = min(width / 1920.0, height / 1080.0)
    else:
        ratio = 1.0

    # Always keep UI within window bounds on smaller displays.
    # Never upscale above baseline to avoid clipped controls.
    ui_scale = max(0.50, min(1.0, ratio))
    override = app.property("_tech_modul_user_ui_scale_override")
    if override not in (None, "", 0, 0.0):
        try:
            ui_scale = max(0.35, min(1.0, float(override)))
        except Exception:
            pass
    font_scale = load_ui_font_scale(default=1.0)
    target_size = max(6.8, min(13.0, base_size * ui_scale * font_scale))

    base_font = QFont(app.font())
    base_font.setPointSizeF(target_size)
    app.setFont(base_font)
    app.setProperty("_tech_modul_ui_scale", float(ui_scale))
    app.setProperty("_tech_modul_ui_font_scale", float(font_scale))
    app.setProperty("_tech_modul_accessible_scale_applied", True)

    app.setStyleSheet(_build_app_stylesheet(mode, motif, ui_scale=ui_scale))


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
        current = self._w._group_tabwidgets[g].currentWidget()
        return self._w._tab_container_to_widget.get(current, current)

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
        # Okno startuje zmaksymalizowane; resize() jest tylko fallbackiem
        # gdy showMaximized() nie zadziala (np. w testach)
        self.resize(1400, 860)

        # Mapowania: tytuł → widget i tytuł → lokalizacja w grupie
        self._tabs_by_title: dict[str, QWidget] = {}
        self._tab_container_to_widget: dict[QWidget, QWidget] = {}
        self._tab_title_to_group: dict[str, int] = {}
        self._tab_title_to_local_idx: dict[str, int] = {}
        self._group_tabwidgets: list[QTabWidget] = []
        self._active_group: int = 0
        self._sidebar_visible: bool = True
        self._time_kiosk_window: TimeClockKioskWindow | None = None
        self._access_store = AccessControlStoreJson()
        self._return_to_order_available: bool = False

        # Historia nawigacji (lista tytułów zakładek)
        self._nav_history: list[str] = []
        self._nav_history_pos: int = -1
        self._is_history_navigation: bool = False
        self._instruction_mode_enabled: bool = False
        self._instruction_hover_tab_title: str = ""
        self._instruction_bubble_timeout_ms: int = 8000
        self._tab_bar_to_group_idx: dict[int, int] = {}
        self._group_button_to_group_idx: dict[int, int] = {}
        self._tab_instruction_guide: dict[str, dict[str, str]] = self._build_tab_instruction_guide()
        self._tab_walkthrough_guide: dict[str, list[str]] = self._build_tab_walkthrough_guide()
        self._onboarding_active: bool = False
        self._onboarding_steps: list[str] = [
            "Start",
            "Nowe zamowienie",
            "Wycena",
            "Sciana",
            "Komplet",
            "Kalendarz",
            "Czas pracy",
        ]
        self._onboarding_index: int = 0
        
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
            tab_bar = gtw.tabBar()
            tab_bar.setExpanding(False)
            tab_bar.setMovable(False)
            tab_bar.setUsesScrollButtons(True)
            tab_bar.setElideMode(Qt.TextElideMode.ElideNone)
            tab_bar.setCursor(Qt.CursorShape.PointingHandCursor)
            tab_bar.setObjectName(f"MainGroupTabBar_{g_idx}")
            tab_bar.setMouseTracking(True)
            tab_bar.installEventFilter(self)
            self._tab_bar_to_group_idx[id(tab_bar)] = g_idx
            gtw.setIconSize(QSize(14, 14))
            self._group_tabwidgets.append(gtw)
            self._content_stack.addWidget(gtw)
            for tab_title in tab_titles:
                widget = self._tabs_by_title.get(tab_title)
                if widget is not None:
                    tab_container = self._wrap_tab_widget(widget, tab_title)
                    local_idx = gtw.addTab(tab_container, tab_title)
                    gtw.setTabToolTip(local_idx, self._instruction_tooltip_for_tab(tab_title))
                    self._tab_title_to_group[tab_title] = g_idx
                    self._tab_title_to_local_idx[tab_title] = local_idx
            gtw.currentChanged.connect(
                lambda idx, g=g_idx: self._on_group_tab_changed(g, idx)
            )

        # Awatar asystenta
        self.assistant_avatar = FloatingAssistantAvatar(self)

        # Ustaw kolory przycisków sidebaru przez QPalette (obejście Windows platform style)
        self._refresh_sidebar_button_colors()
        self._refresh_sidebar_toggle_button()

        # Connect search button
        if hasattr(self, 'btn_search'):
            self.btn_search.sig_navigate_to.connect(self._navigate_to_tab)
        
        # Aktywuj pierwszą grupę (Sprzedaż → Start)
        self._set_active_group(0)

        first_group_titles = GROUPS[0][1]
        if first_group_titles:
            self._nav_history = [first_group_titles[0]]
            self._nav_history_pos = 0

        self._update_navigation_buttons()
        self._wire_cross_tab_signals()
        # Compat shim must exist immediately (tests and signal handlers use it right away).
        self.tabs = _TabsCompat(self)
        self._install_instruction_hover_sources()
        self._sync_onboarding_status_to_start_tab()

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

        # Per-user UI scale override (different users may have different displays/preferences).
        user_scale = None
        try:
            user_scale = self._access_store.get_ui_scale_override_for_worker(self._current_worker)
        except Exception:
            user_scale = None
        app = QApplication.instance()
        if app is not None:
            app.setProperty(
                "_tech_modul_user_ui_scale_override",
                0.0 if user_scale is None else float(user_scale),
            )
        self._apply_ui_theme(self._theme_mode, self._theme_motif)
        
        # Update window title with user info
        role_label = ROLE_LABELS.get(self._current_role, self._current_role)
        self.setWindowTitle(f"TECH_modul - {self._current_worker} ({role_label})")
        
        # Update sidebar user label
        if hasattr(self, "_user_label"):
            self._user_label.setText(f"{self._current_worker}\n({role_label})")

        # Propagate active user to tabs that support user context
        for _tab_title, tab_widget in self._tabs_by_title.items():
            if hasattr(tab_widget, "set_current_user"):
                try:
                    tab_widget.set_current_user(self._current_worker, self._current_role)
                except Exception:
                    pass
        
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
        """Apply role-based access.
        
        Indywidualne blokowanie zakładek przez setEnabled powoduje na Windows
        ukrywanie kart z paska QTabBar. Zamiast tego uprawnienia sa egzekwowane
        tylko na poziomie grup sidebaru — grupy niedostepne dla roli maja
        wyszarzone przyciski w pasku bocznym.
        """
        # Upewnij sie ze wszystkie karty sa aktywne (widoczne w pasku)
        for group_idx, gtw in enumerate(self._group_tabwidgets):
            for local_idx in range(gtw.count()):
                widget = gtw.widget(local_idx)
                if widget is not None:
                    widget.setEnabled(True)
        
        # Ogranicz dostep tylko na poziomie grup w sidebarze
        self._refresh_sidebar_permissions()
    
    def _refresh_sidebar_permissions(self) -> None:
        """Update sidebar button states based on current role."""
        if not hasattr(self, "_group_buttons"):
            return
        
        for idx, btn in enumerate(self._group_buttons):
            group_name, tab_titles = GROUPS[idx]
            # Check if user can access any tab in this group
            can_access_group = any(
                can_access_tab(self._current_role, title, self._current_worker) for title in tab_titles
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

    def _wrap_tab_widget(self, widget: QWidget, tab_title: str) -> QWidget:
        # Keep real tab widget references in _tabs_by_title, but render each tab inside
        # a scroll container so content is always reachable on smaller displays.
        if isinstance(widget, QScrollArea):
            return widget
        existing_parent = widget.parentWidget()
        if isinstance(existing_parent, QScrollArea):
            self._tab_container_to_widget[existing_parent] = widget
            return existing_parent

        scroll = QScrollArea(self)
        scroll.setObjectName(f"TabScroll::{tab_title}")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(widget)
        self._tab_container_to_widget[scroll] = widget
        return scroll

    def _toggle_sidebar_visibility(self) -> None:
        self._sidebar_visible = not self._sidebar_visible
        if hasattr(self, "_sidebar"):
            self._sidebar.setVisible(self._sidebar_visible)
        self._refresh_sidebar_toggle_button()

    def _install_instruction_hover_sources(self) -> None:
        if hasattr(self, "_group_buttons"):
            for idx, btn in enumerate(self._group_buttons):
                self._group_button_to_group_idx[id(btn)] = idx
                btn.setMouseTracking(True)
                btn.installEventFilter(self)
        for tab_bar in self.findChildren(QTabBar):
            tab_bar.setMouseTracking(True)
            tab_bar.installEventFilter(self)
            g_idx = self._find_group_idx_for_tab_bar(tab_bar)
            if g_idx >= 0:
                self._tab_bar_to_group_idx[id(tab_bar)] = g_idx

    @staticmethod
    def _extract_event_point(event: QEvent) -> QPoint | None:
        point = None
        if hasattr(event, "position"):
            try:
                point = event.position().toPoint()
            except Exception:
                point = None
        if point is None and hasattr(event, "pos"):
            try:
                point = event.pos()
            except Exception:
                point = None
        return point

    def _instruction_show_message(self, key: str, message: str) -> None:
        normalized_key = str(key or "").strip()
        if not normalized_key or normalized_key == self._instruction_hover_tab_title:
            return
        self._instruction_hover_tab_title = normalized_key
        if hasattr(self, "assistant_avatar"):
            self.assistant_avatar.say(message, self._instruction_bubble_timeout_ms)

    def eventFilter(self, watched: object, event: QEvent | None) -> bool:  # type: ignore[override]
        if event is None:
            return super().eventFilter(watched, event)

        event_type = event.type()

        # Sidebar groups (boczne zakladki)
        if isinstance(watched, QPushButton):
            g_idx = self._group_button_to_group_idx.get(id(watched), -1)
            if g_idx >= 0:
                if event_type in (QEvent.Type.Enter, QEvent.Type.HoverEnter):
                    if self._instruction_mode_enabled:
                        group_name, group_tabs = GROUPS[g_idx]
                        self._instruction_show_message(
                            f"group:{group_name}",
                            self._instruction_group_message(group_name, group_tabs),
                        )
                elif event_type in (QEvent.Type.Leave, QEvent.Type.HoverLeave):
                    self._instruction_hover_tab_title = ""

        # Main tabs + inner tabs
        if isinstance(watched, QTabBar):
            group_idx = self._tab_bar_to_group_idx.get(id(watched), -1)
            if group_idx < 0:
                group_idx = self._find_group_idx_for_tab_bar(watched)
            if event_type in (QEvent.Type.MouseMove, QEvent.Type.HoverMove, QEvent.Type.Enter, QEvent.Type.HoverEnter):
                if self._instruction_mode_enabled:
                    point = self._extract_event_point(event)
                    local_idx = -1
                    if point is not None:
                        local_idx = watched.tabAt(point)
                    if local_idx < 0:
                        local_idx = watched.currentIndex()
                    if local_idx >= 0:
                        raw_title = watched.tabText(local_idx)
                        title = self._normalize_instruction_tab_title(raw_title)
                        if title:
                            if group_idx >= 0:
                                self._instruction_show_message(
                                    f"main:{title}",
                                    self._instruction_message_for_tab(title),
                                )
                            else:
                                self._instruction_show_message(
                                    f"inner:{title}",
                                    self._instruction_inner_tab_message(title),
                                )
            elif event_type in (QEvent.Type.Leave, QEvent.Type.HoverLeave):
                self._instruction_hover_tab_title = ""
        return super().eventFilter(watched, event)

    def _find_group_idx_for_tab_bar(self, watched: object) -> int:
        watched_name = ""
        if hasattr(watched, "objectName"):
            try:
                watched_name = str(watched.objectName() or "")
            except Exception:
                watched_name = ""
        if watched_name.startswith("MainGroupTabBar_"):
            tail = watched_name.split("_", 1)[-1]
            try:
                idx = int(tail)
                if 0 <= idx < len(self._group_tabwidgets):
                    return idx
            except Exception:
                pass
        for idx, gtw in enumerate(self._group_tabwidgets):
            tab_bar = gtw.tabBar()
            try:
                if watched is tab_bar or watched == tab_bar:
                    return idx
            except Exception:
                continue
        return -1

    def _set_instruction_mode(self, enabled: bool) -> None:
        self._instruction_mode_enabled = bool(enabled)
        self._instruction_hover_tab_title = ""
        self._install_instruction_hover_sources()
        tab_start = self._tabs_by_title.get("Start")
        if tab_start is not None and hasattr(tab_start, "set_instruction_mode_state"):
            tab_start.set_instruction_mode_state(self._instruction_mode_enabled)
        if not hasattr(self, "assistant_avatar"):
            return
        if self._instruction_mode_enabled:
            self.assistant_avatar.say(
                "Tryb instrukcji wlaczony. Najedz na zakladki, a podpowiem.",
                9000,
            )
        else:
            self.assistant_avatar.say("Tryb instrukcji wylaczony.", 3500)

    def _build_tab_instruction_guide(self) -> dict[str, dict[str, str]]:
        return {
            "Start": {
                "what": "Panel startowy i skroty do najwazniejszych akcji.",
                "when": "Kiedy zaczynasz dzien lub wdrazasz nowa osobe.",
                "impact": "Przyspiesza przejscie przez caly proces bez gubienia krokow.",
            },
            "Nowe zamowienie": {
                "what": "Dane klienta, zamowienia i pozycje do wyceny.",
                "when": "Zawsze na poczatku nowego tematu handlowego.",
                "impact": "To zrodlo danych dla Wyceny, Sciany i Kompletu.",
            },
            "Wycena": {
                "what": "Koszty techniczne, marza i finalna oferta.",
                "when": "Po dodaniu pozycji w zamowieniu.",
                "impact": "Wplywa na rentownosc i decyzje handlowe.",
            },
            "Sciana": {
                "what": "Pomiary i kontekst realizacyjny dla zabudowy.",
                "when": "Po zebraniu danych od klienta i przed budowa kompletu.",
                "impact": "Wymiary przechodza dalej do projektu i ograniczaja bledy na produkcji.",
            },
            "Komplet": {
                "what": "Uklad calosci projektu i powiazania miedzy modulami.",
                "when": "Gdy masz gotowe pomiary i chcesz skladac rozwiazanie.",
                "impact": "Definiuje co trafia na produkcje i montaz.",
            },
            "Modul": {
                "what": "Szczegoly pojedynczego modulu.",
                "when": "Gdy dopracowujesz konkretne elementy projektu.",
                "impact": "Zmienia liste elementow, materialy i koszty.",
            },
            "Kalendarz": {
                "what": "Plan terminow i statusow prac.",
                "when": "Po potwierdzeniu kolejnych etapow.",
                "impact": "Synchronizuje zespol i zmniejsza opoznienia.",
            },
            "Czas pracy": {
                "what": "Ewidencja godzin i kosztu robocizny.",
                "when": "W trakcie realizacji i rozliczen.",
                "impact": "Pokazuje realny koszt pracy i wydajnosc.",
            },
            "Baza materialu": {
                "what": "Biblioteka materialow i parametrow.",
                "when": "Przed finalnym doborem elementow.",
                "impact": "Wplywa na wycene, recepture i raporty zakupowe.",
            },
            "Klienci": {
                "what": "Baza kontaktow klientow.",
                "when": "Przy zakladaniu lub aktualizacji danych zamowienia.",
                "impact": "Porzadkuje historie i dokumenty handlowe.",
            },
            "Pracownicy": {
                "what": "Dane zespolu i role.",
                "when": "Przy przypisywaniu odpowiedzialnosci.",
                "impact": "Wplywa na czas pracy, dostepy i raporty.",
            },
            "QR Telefon": {
                "what": "Szybki dostep telefonem do skanera, kiosku i pomiarow mobilnych.",
                "when": "Gdy pracujesz na hali albo przy pomiarze u klienta.",
                "impact": "Przyspiesza zbieranie danych bez wracania do komputera.",
            },
            "Ustawienia": {
                "what": "Konfiguracja programu i widokow.",
                "when": "Przy pierwszym uruchomieniu lub zmianie standardu pracy.",
                "impact": "Ustala domyslne zachowanie narzedzi.",
            },
            "Dashboard": {
                "what": "Widok KPI i statusu firmy.",
                "when": "Do szybkiej kontroli dnia/tygodnia.",
                "impact": "Pomaga szybciej wylapac ryzyka i priorytety.",
            },
            "Grafika": {
                "what": "Biblioteka wizualna ekranow, instrukcji i stylow.",
                "when": "Gdy chcesz pokazac wyglad programu albo uporzadkowac materialy graficzne.",
                "impact": "Porzadkuje screeny, instrukcje i elementy UI w jednym miejscu.",
            },
        }

    def _build_tab_walkthrough_guide(self) -> dict[str, list[str]]:
        return {
            "Start": [
                "Wlacz Tryb instrukcji, zeby aktywowac podpowiedzi kontekstowe.",
                "Uzyj Start onboarding, jesli wdrazasz nowa osobe.",
                "Przejdz do Nowe zamowienie, aby zainicjowac realny proces.",
            ],
            "Nowe zamowienie": [
                "Uzupelnij klienta i dane kontaktowe.",
                "Dodaj pozycje do wyceny i sprawdz ich typ.",
                "Przejdz do Wyceny lub Sciany, zaleznie od etapu.",
            ],
            "Wycena": [
                "Zweryfikuj koszt techniczny i marze.",
                "Sprawdz, czy pozycje z zamowienia sa kompletne.",
                "Po akceptacji przejdz do Sciany/Kompletu.",
            ],
            "Sciana": [
                "Dodaj lub zweryfikuj pomiary.",
                "Podepnij zdjecia i notatki pomiarowe.",
                "Przekaz kontekst do Kompletu.",
            ],
            "Komplet": [
                "Zbuduj uklad calosci projektu.",
                "Sprawdz powiazania ze Sciana i zamowieniem.",
                "Przejdz do Modul po detale pojedynczych elementow.",
            ],
            "Modul": [
                "Doprecyzuj detale pojedynczego modulu.",
                "Sprawdz materialy i elementy skladowe.",
                "Zweryfikuj wplyw zmian na koszty i produkcje.",
            ],
            "Kalendarz": [
                "Ustal terminy i status realizacji.",
                "Skontroluj zaleznosci miedzy etapami.",
                "Powiaz zadania z odpowiedzialnymi osobami.",
            ],
            "Czas pracy": [
                "Sprawdz odbicia i ewidencje godzin.",
                "Zweryfikuj koszt robocizny dla zlecen.",
                "Zamknij dzien/tydzien raportem czasu.",
            ],
            "Grafika": [
                "Wybierz instrukcje albo szybkie wejscie do ekranu.",
                "Przegladaj materialy wizualne i legendy statusow.",
                "Trzymaj tu wszystko, co ma pomoc w ladniejszym UI i onboardingu.",
            ],
        }

    def _instruction_tab_walkthrough_message(self, title: str) -> str:
        key = self._normalize_instruction_tab_title(title)
        steps = self._tab_walkthrough_guide.get(key, [])
        if not steps:
            return ""
        first = steps[0]
        second = steps[1] if len(steps) > 1 else ""
        if second:
            return f"Prowadzenie: {key}\n1) {first}\n2) {second}"
        return f"Prowadzenie: {key}\n1) {first}"

    def _announce_tab_walkthrough(self, title: str) -> None:
        if not self._instruction_mode_enabled:
            return
        key = self._normalize_instruction_tab_title(title)
        msg = self._instruction_tab_walkthrough_message(key)
        if not msg:
            return
        self._instruction_show_message(f"walk:{key}", msg)

    def _sync_onboarding_status_to_start_tab(self) -> None:
        tab_start = self._tabs_by_title.get("Start")
        if tab_start is None or not hasattr(tab_start, "set_onboarding_status"):
            return
        current_title = ""
        if self._onboarding_active and 0 <= self._onboarding_index < len(self._onboarding_steps):
            current_title = self._onboarding_steps[self._onboarding_index]
        tab_start.set_onboarding_status(
            active=self._onboarding_active,
            current_step=(self._onboarding_index + 1 if self._onboarding_active else 0),
            total_steps=len(self._onboarding_steps),
            current_title=current_title,
        )

    def _global_onboarding_message(self) -> str:
        if not self._onboarding_active or not self._onboarding_steps:
            return "Onboarding globalny nieaktywny."
        idx = max(0, min(self._onboarding_index, len(self._onboarding_steps) - 1))
        title = self._onboarding_steps[idx]
        guide = self._instruction_message_for_tab(title)
        return f"Onboarding {idx + 1}/{len(self._onboarding_steps)}\n{guide}"

    def _start_global_onboarding(self) -> None:
        if not self._onboarding_steps:
            return
        self._onboarding_active = True
        self._onboarding_index = 0
        if not self._instruction_mode_enabled:
            self._set_instruction_mode(True)
        self._sync_onboarding_status_to_start_tab()
        target = self._onboarding_steps[self._onboarding_index]
        self._navigate_to_tab(target)
        self._instruction_show_message(f"onb:{target}", self._global_onboarding_message())

    def _next_global_onboarding_step(self) -> None:
        if not self._onboarding_steps:
            return
        if not self._onboarding_active:
            self._start_global_onboarding()
            return
        if self._onboarding_index >= len(self._onboarding_steps) - 1:
            self._instruction_show_message(
                "onb:done",
                "Onboarding zakonczony. Mozesz kontynuowac prace samodzielnie lub wlaczyc tryb instrukcji na stale.",
            )
            self._stop_global_onboarding()
            return
        self._onboarding_index += 1
        self._sync_onboarding_status_to_start_tab()
        target = self._onboarding_steps[self._onboarding_index]
        self._navigate_to_tab(target)
        self._instruction_show_message(f"onb:{target}", self._global_onboarding_message())

    def _stop_global_onboarding(self) -> None:
        self._onboarding_active = False
        self._onboarding_index = 0
        self._sync_onboarding_status_to_start_tab()

    def _sync_onboarding_with_active_tab(self, title: str) -> None:
        if not self._onboarding_active:
            return
        key = self._normalize_instruction_tab_title(title)
        if key in self._onboarding_steps:
            self._onboarding_index = self._onboarding_steps.index(key)
            self._sync_onboarding_status_to_start_tab()
            self._instruction_show_message(f"onb:{key}", self._global_onboarding_message())

    def _instruction_tooltip_for_tab(self, title: str) -> str:
        key = self._normalize_instruction_tab_title(title)
        entry = self._tab_instruction_guide.get(key)
        if not entry:
            return f"{key}: pomoc kontekstowa w trybie instrukcji."
        return f"{key}: {entry['what']} Wplywa na: {entry['impact']}"

    def _instruction_message_for_tab(self, title: str) -> str:
        key = self._normalize_instruction_tab_title(title)
        entry = self._tab_instruction_guide.get(key)
        related = self._instruction_related_tabs(key)
        if not entry:
            return (
                f"{key}\n"
                "Co to: zakladka funkcjonalna programu.\n"
                "Wplywa na: dane powiazane z Twoim projektem.\n"
                f"Powiazane: {related or 'inne zakladki tej samej grupy.'}"
            )
        return (
            f"{key}\n"
            f"Co to: {entry['what']}\n"
            f"Wplywa na: {entry['impact']}\n"
            f"Powiazane: {related or 'inne zakladki tej samej grupy.'}"
        )

    def _instruction_group_message(self, group_name: str, tab_titles: list[str]) -> str:
        tabs_line = ", ".join(tab_titles[:6])
        if len(tab_titles) > 6:
            tabs_line += ", ..."
        return (
            f"Grupa: {group_name}\n"
            f"Zakladki: {tabs_line}\n"
            "Wplyw: szybkie przejscie miedzy krokami."
        )

    def _instruction_inner_tab_message(self, title: str) -> str:
        key = self._normalize_instruction_tab_title(title)
        entry = self._tab_instruction_guide.get(key)
        if entry:
            return (
                f"Zakladka wewnetrzna: {key}\n"
                f"Co to: {entry['what']}\n"
                f"Wplywa na: {entry['impact']}"
            )
        return (
            f"Zakladka wewnetrzna: {key}\n"
            "Co to: krok pomocniczy w aktualnym ekranie.\n"
            "Wplywa na: podsumowanie, zapisy i kolejne etapy procesu."
        )

    def _instruction_related_tabs(self, title: str) -> str:
        key = self._normalize_instruction_tab_title(title)
        for _group_name, tab_titles in GROUPS:
            if key in tab_titles:
                related = [tab for tab in tab_titles if tab != key]
                if not related:
                    return ""
                line = ", ".join(related[:4])
                if len(related) > 4:
                    line += ", ..."
                return line
        return ""

    def _normalize_instruction_tab_title(self, title: str) -> str:
        out = str(title or "").strip()
        for prefix in ("🔴", "🟡", "🔵", "🟥", "🟧", "🟦"):
            if out.startswith(prefix):
                out = out[len(prefix):].strip()
                break
        if out.endswith("]") and " [" in out:
            out = out.rsplit(" [", 1)[0].strip()
        return out

    # ------------------------------------------------------------------
    # Nawigacja grupami
    # ------------------------------------------------------------------

    def _set_active_group(self, g_idx: int) -> None:
        if g_idx < 0 or g_idx >= len(self._group_tabwidgets):
            return
        group_label = GROUPS[g_idx][0] if g_idx < len(GROUPS) else str(g_idx)
        try:
            self._active_group = g_idx
            self._content_stack.setCurrentIndex(g_idx)
            for i, btn in enumerate(self._group_buttons):
                btn.setChecked(i == g_idx)
            self._update_navigation_buttons()
        except Exception as exc:
            self._show_runtime_error(f"otwarcie grupy '{group_label}'", exc)

    def _show_runtime_error(self, action_label: str, exc: Exception) -> None:
        QMessageBox.critical(
            self,
            "Blad programu",
            f"Nie udalo sie wykonac akcji: {action_label}.\n\nSzczegoly: {exc}",
        )

    def _navigate_to_tab(self, title: str) -> None:
        try:
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
        except Exception as exc:
            self._show_runtime_error(f"otwarcie zakladki '{title}'", exc)

    def _current_tab_title(self) -> str | None:
        if self._active_group < 0 or self._active_group >= len(self._group_tabwidgets):
            return None
        gtw = self._group_tabwidgets[self._active_group]
        local_idx = gtw.currentIndex()
        if local_idx < 0:
            return None
        return gtw.tabText(local_idx)

    def _on_group_tab_changed(self, group_idx: int, local_idx: int) -> None:
        try:
            if local_idx < 0:
                return
            # Ignoruj zmiany z grup nieaktywnych (np. przy przełączaniu grupy)
            if group_idx != self._active_group:
                return
            gtw = self._group_tabwidgets[group_idx]
            title = gtw.tabText(local_idx)
            self._install_instruction_hover_sources()
            self._announce_tab_walkthrough(title)
            self._sync_onboarding_with_active_tab(title)

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
        except Exception as exc:
            group_label = GROUPS[group_idx][0] if 0 <= group_idx < len(GROUPS) else str(group_idx)
            tab_label = ""
            if (
                0 <= group_idx < len(self._group_tabwidgets)
                and local_idx >= 0
                and local_idx < self._group_tabwidgets[group_idx].count()
            ):
                tab_label = self._group_tabwidgets[group_idx].tabText(local_idx)
            action = (
                f"przelaczenie zakladki '{tab_label}' w grupie '{group_label}'"
                if tab_label
                else f"przelaczenie zakladki w grupie '{group_label}'"
            )
            self._show_runtime_error(action, exc)

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
        try:
            if bool(tab.load_module_from_store_name(str(module_name or ""))):
                self._navigate_to_tab("Modul")
        except Exception as exc:
            self._show_runtime_error("otwarcie modulu", exc)

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
        try:
            if hasattr(tab, "start_new_module"):
                tab.start_new_module()
            self._navigate_to_tab("Modul")
        except Exception as exc:
            self._show_runtime_error("uruchomienie zakladki Modul", exc)

    def _open_quote(self) -> None:
        self._navigate_to_tab("Wycena")

    def _open_assembly_in_wycena(self, assembly_name: str) -> None:
        tab = self._tabs_by_title.get("Wycena")
        if tab is not None and hasattr(tab, "open_assembly_for_pricing"):
            tab.open_assembly_for_pricing(str(assembly_name or ""))
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

    def _open_calendar_from_order(self, target_date: str | None = None) -> None:
        self._capture_order_return_state()
        self._open_calendar(target_date)

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
        self._capture_order_return_state()
        tab = self._tabs_by_title.get("Klienci")
        if tab is not None and hasattr(tab, "open_clients_tab"):
            tab.open_clients_tab(clear_form=False)
        self._navigate_to_tab("Klienci")

    def _open_orders_in_bazy(self) -> None:
        self._capture_order_return_state()
        tab = self._tabs_by_title.get("Zamowienia")
        if tab is not None and hasattr(tab, "open_orders_tab"):
            tab.open_orders_tab(clear_form=False)
        self._navigate_to_tab("Zamowienia")

    # Alias used by wiring (tab_baza_szybkich_wycen signal)
    def _open_orders_in_bazy_code(self, *args) -> None:
        self._open_orders_in_bazy()

    def _open_workers_in_bazy(self) -> None:
        self._capture_order_return_state()
        tab = self._tabs_by_title.get("Pracownicy")
        if tab is not None and hasattr(tab, "open_workers_tab"):
            tab.open_workers_tab(clear_form=False)
        self._navigate_to_tab("Pracownicy")

    def _open_bazy(self) -> None:
        self._capture_order_return_state()
        self._navigate_to_tab("Baza materialu")

    def _open_invoice_db(self) -> None:
        self._capture_order_return_state()
        self._navigate_to_tab("Baza faktur")

    def _capture_order_return_state(self) -> None:
        tab_order = self._tabs_by_title.get("Nowe zamowienie")
        has_context = self._current_tab_title() == "Nowe zamowienie"
        if tab_order is not None and hasattr(tab_order, "save_draft_for_navigation"):
            try:
                tab_order.save_draft_for_navigation()
            except Exception:
                pass
        if tab_order is not None and hasattr(tab_order, "has_pending_order_context"):
            try:
                has_context = has_context or bool(tab_order.has_pending_order_context())
            except Exception:
                pass
        self._set_bazy_return_to_order_enabled(has_context)

    def _set_bazy_return_to_order_enabled(self, enabled: bool) -> None:
        self._return_to_order_available = bool(enabled)
        for title in ("Klienci", "Zamowienia", "Pracownicy", "Bazy"):
            tab_bazy = self._tabs_by_title.get(title)
            if tab_bazy is not None and hasattr(tab_bazy, "set_return_to_order_enabled"):
                tab_bazy.set_return_to_order_enabled(self._return_to_order_available)
        tab_kalendarz = self._tabs_by_title.get("Kalendarz")
        if tab_kalendarz is not None and hasattr(tab_kalendarz, "set_return_to_order_enabled"):
            tab_kalendarz.set_return_to_order_enabled(self._return_to_order_available)

    def _return_to_order_from_bazy(self) -> None:
        if not self._return_to_order_available:
            return
        tab_order = self._tabs_by_title.get("Nowe zamowienie")
        if tab_order is not None and hasattr(tab_order, "start_new_order"):
            tab_order.start_new_order(force_blank=False)
        self._navigate_to_tab("Nowe zamowienie")
        self._set_bazy_return_to_order_enabled(False)

    def _return_to_order_from_calendar(self) -> None:
        self._return_to_order_from_bazy()

    def _open_settings(self) -> None:
        self._navigate_to_tab("Ustawienia")

    def _apply_theme_profile(self, profile_key: str) -> None:
        key = str(profile_key or "").strip().lower()
        if key in {"contrast", "kontrast", "kontrastowy", "contrast_desktop", "high_contrast"}:
            mode, motif = ("day", "contrast")
        elif key in {"tech", "tech_dark", "docelowy", "target"}:
            mode, motif = ("night", "tech")
        else:
            mode, motif = ("night", "tech")
        save_ui_theme_settings(mode, motif)
        self._apply_ui_theme(mode, motif)

    def _apply_ui_theme(self, mode: str, motif: str) -> None:
        self._theme_mode = str(mode or "night")
        self._theme_motif = str(motif or "tech")
        _apply_accessible_ui_scale(self._theme_mode, self._theme_motif)
        self._refresh_sidebar_button_colors()
        tab_start = self._tabs_by_title.get("Start")
        if tab_start is not None and hasattr(tab_start, "set_theme_profile"):
            try:
                tab_start.set_theme_profile(self._theme_mode, self._theme_motif)
            except Exception:
                pass

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
                    tabBar.setTabTextColor(local_idx, QColor(_theme_palette(self._theme_mode, self._theme_motif)["text"]))
        
        # Odśwież też główny sidebar - aktualizuj stan przycisków
        self._refresh_sidebar_permissions()

    def _run_alarm_engine(self) -> None:
        try:
            AlarmGenerator().generate_all()
        except Exception:
            pass
