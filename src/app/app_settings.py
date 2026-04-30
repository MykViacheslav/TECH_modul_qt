from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class DrawingSettings:
    rect_line_color: str = "#000000"
    rect_line_width_px: int = 3
    dim_line_color: str = "#0066cc"
    dim_line_width_px: int = 3
    dim_end_style: str = "arrows"
    grid_enabled: bool = True
    grid_step_mm: float = 50.0
    grid_color: str = "#e6e6e6"
    grid_width_px: int = 1
    show_front_part: bool = True
    front_mode: str = "external"
    edgeband_color: str = "#cc0000"
    edgeband_width_px: int = 4
    grain_overlay_enabled: bool = True
    grain_overlay_style: str = "wavy"
    grain_overlay_alpha: int = 80
    grain_line_spacing_mm: float = 15.0
    grain_image_path: str = ""
    hinge_edge_offset_mm: float = 12.0
    auto_double_front_width_mm: float = 600.0


@dataclass(frozen=True)
class UiThemeSettings:
    mode: str = "night"
    motif: str = "tech"


@dataclass(frozen=True)
class GmailOAuthSettings:
    enabled: bool = False
    client_id: str = ""
    client_secret: str = ""
    max_fetch: int = 20


@dataclass(frozen=True)
class WhatsAppSettings:
    enabled: bool = False
    account_sid: str = ""
    auth_token: str = ""
    to_number: str = ""
    max_fetch: int = 20


@dataclass(frozen=True)
class EmailSettings:
    enabled: bool = False
    host: str = "imap.gmail.com"
    port: int = 993
    username: str = ""
    password: str = ""
    folder: str = "INBOX"
    max_fetch: int = 20


@dataclass(frozen=True)
class TelegramSettings:
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""
    bot_username: str = ""


@dataclass(frozen=True)
class DefaultMaterialSettings:
    carcass_material_key: str = ""
    carcass_thickness_mm: float = 18.0
    front_material_key: str = ""
    front_thickness_mm: float = 18.0
    shelf_material_key: str = ""
    shelf_thickness_mm: float = 18.0
    back_material_key: str = ""
    back_thickness_mm: float = 3.0
    carcass_edgeband_key: str = ""
    front_edgeband_key: str = ""
    default_leg_height_mm: float = 100.0
    default_carcass_joint: str = "type1"
    material_profile_key: str = ""


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _data_dir() -> Path:
    env = os.environ.get("TECH_MODUL_DATA_DIR", "").strip()
    if env:
        return Path(env)
    return _project_root() / "data"


def _settings_path() -> Path:
    return _data_dir() / "settings.json"


def _load_settings_data() -> Dict[str, Any]:
    path = _settings_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"drawing": DrawingSettings().__dict__}, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except:
        return {}


def _save_settings_data(data: Dict[str, Any]) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_drawing_settings() -> DrawingSettings:
    data = _load_settings_data().get("drawing", {})
    base = DrawingSettings().__dict__.copy()
    for k, v in data.items():
        if k in base: base[k] = v
    return DrawingSettings(**base)


def save_drawing_settings(s: DrawingSettings) -> None:
    data = _load_settings_data()
    data["drawing"] = s.__dict__
    _save_settings_data(data)


def load_ui_theme_settings() -> UiThemeSettings:
    data = _load_settings_data().get("ui", {})
    return UiThemeSettings(mode=data.get("theme_mode", "night"), motif=data.get("theme_motif", "tech"))


def save_ui_theme_settings(mode: str, motif: str) -> None:
    data = _load_settings_data()
    ui = data.get("ui", {})
    ui["theme_mode"], ui["theme_motif"] = mode, motif
    data["ui"] = ui
    _save_settings_data(data)


def load_ui_font_scale(default: float = 1.0) -> float:
    ui = _load_settings_data().get("ui", {})
    try:
        return float(ui.get("font_scale", default))
    except:
        return default


def save_ui_font_scale(scale: float) -> None:
    data = _load_settings_data()
    ui = data.get("ui", {})
    ui["font_scale"] = float(scale)
    data["ui"] = ui
    _save_settings_data(data)


def load_ui_string_list(key: str, default: list[str] | None = None) -> list[str]:
    ui = _load_settings_data().get("ui", {})
    lists = ui.get("string_lists", {})
    val = lists.get(key)
    if isinstance(val, list):
        return [str(i) for i in val]
    return default or []


def save_ui_string_list(key: str, values: list[str]) -> None:
    data = _load_settings_data()
    ui = data.get("ui", {})
    if "string_lists" not in ui:
        ui["string_lists"] = {}
    ui["string_lists"][key] = list(values)
    data["ui"] = ui
    _save_settings_data(data)


def load_telegram_settings() -> TelegramSettings:
    t = _load_settings_data().get("telegram", {})
    return TelegramSettings(
        enabled=bool(t.get("enabled", False)),
        bot_token=str(t.get("bot_token", "")),
        chat_id=str(t.get("chat_id", "")),
        bot_username=str(t.get("bot_username", ""))
    )


def save_telegram_settings(s: TelegramSettings) -> None:
    data = _load_settings_data()
    data["telegram"] = {
        "enabled": bool(s.enabled),
        "bot_token": str(s.bot_token),
        "chat_id": str(s.chat_id),
        "bot_username": str(s.bot_username),
    }
    _save_settings_data(data)


def load_gmail_oauth_settings() -> GmailOAuthSettings:
    g = _load_settings_data().get("gmail_oauth", {})
    return GmailOAuthSettings(
        enabled=bool(g.get("enabled", False)),
        client_id=str(g.get("client_id", "")),
        client_secret=str(g.get("client_secret", "")),
        max_fetch=int(g.get("max_fetch", 20))
    )


def save_gmail_oauth_settings(s: GmailOAuthSettings) -> None:
    data = _load_settings_data()
    data["gmail_oauth"] = s.__dict__
    _save_settings_data(data)


def load_whatsapp_settings() -> WhatsAppSettings:
    w = _load_settings_data().get("whatsapp", {})
    return WhatsAppSettings(
        enabled=bool(w.get("enabled", False)),
        account_sid=str(w.get("account_sid", "")),
        auth_token=str(w.get("auth_token", "")),
        to_number=str(w.get("to_number", "")),
        max_fetch=int(w.get("max_fetch", 20))
    )


def save_whatsapp_settings(s: WhatsAppSettings) -> None:
    data = _load_settings_data()
    data["whatsapp"] = s.__dict__
    _save_settings_data(data)


def load_email_settings() -> EmailSettings:
    e = _load_settings_data().get("email", {})
    return EmailSettings(
        enabled=bool(e.get("enabled", False)),
        host=str(e.get("host", "imap.gmail.com")),
        port=int(e.get("port", 993)),
        username=str(e.get("username", "")),
        password=str(e.get("password", "")),
        folder=str(e.get("folder", "INBOX")),
        max_fetch=int(e.get("max_fetch", 20))
    )


def save_email_settings(s: EmailSettings) -> None:
    data = _load_settings_data()
    data["email"] = s.__dict__
    _save_settings_data(data)


def load_default_material_settings() -> DefaultMaterialSettings:
    d = _load_settings_data().get("default_materials", {})
    base = DefaultMaterialSettings().__dict__.copy()
    for k, v in d.items():
        if k in base: base[k] = v
    return DefaultMaterialSettings(**base)


def save_default_material_settings(s: DefaultMaterialSettings) -> None:
    data = _load_settings_data()
    data["default_materials"] = s.__dict__
    _save_settings_data(data)


def load_modul_splitter_sizes(default: list[int] | None = None) -> list[int]:
    ui = _load_settings_data().get("ui", {})
    raw = ui.get("modul_splitter_sizes")
    if isinstance(raw, list) and len(raw) == 3: return raw
    return default or [360, 900, 360]


def save_modul_splitter_sizes(sizes: list[int] | tuple[int, int, int]) -> None:
    data = _load_settings_data()
    ui = data.get("ui", {})
    ui["modul_splitter_sizes"] = list(sizes)
    data["ui"] = ui
    _save_settings_data(data)


def load_table_column_widths(key: str, default: list[int] | None = None) -> list[int]:
    ui = _load_settings_data().get("ui", {})
    widths = ui.get("table_column_widths", {})
    return widths.get(key, default or [])


def save_table_column_widths(key: str, widths: list[int] | tuple[int, ...]) -> None:
    data = _load_settings_data()
    ui = data.get("ui", {})
    all_widths = ui.get("table_column_widths", {})
    all_widths[key] = list(widths)
    ui["table_column_widths"] = all_widths
    data["ui"] = ui
    _save_settings_data(data)
