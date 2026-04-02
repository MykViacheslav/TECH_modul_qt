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
    dim_end_style: str = "arrows"  # "arrows" | "ticks"

    grid_enabled: bool = True
    grid_step_mm: float = 50.0
    grid_color: str = "#e6e6e6"
    grid_width_px: int = 1

    show_front_part: bool = True          # tylko rysunek
    front_mode: str = "external"          # "external" | "internal"

    edgeband_color: str = "#cc0000"
    edgeband_width_px: int = 4

    # NOWE
    hinge_edge_offset_mm: float = 12.0
    auto_double_front_width_mm: float = 600.0


@dataclass(frozen=True)
class UiThemeSettings:
    mode: str = "day"      # "day" | "night"
    motif: str = "cream"   # "cream" | "blue" | "gray" | "green" | "contrast"


@dataclass(frozen=True)
class GmailOAuthSettings:
    """Przechowuje tylko client_id i client_secret — tokeny są w data/gmail_token.json."""
    enabled: bool = False
    client_id: str = ""
    client_secret: str = ""
    max_fetch: int = 20


@dataclass(frozen=True)
class WhatsAppSettings:
    enabled: bool = False
    account_sid: str = ""
    auth_token: str = ""
    # Twój numer WhatsApp w Twilio (format: whatsapp:+48...)
    # Sandbox: whatsapp:+14155238886
    to_number: str = ""
    max_fetch: int = 20  # max wiadomości do pobrania


@dataclass(frozen=True)
class EmailSettings:
    enabled: bool = False
    host: str = "imap.gmail.com"
    port: int = 993
    username: str = ""
    password: str = ""
    folder: str = "INBOX"
    max_fetch: int = 20  # max unprzeczytanych do pobrania


@dataclass(frozen=True)
class TelegramSettings:
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


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
        path.write_text(
            json.dumps({"drawing": DrawingSettings().__dict__}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_settings_data(data: Dict[str, Any]) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def load_drawing_settings() -> DrawingSettings:
    data = _load_settings_data()
    d = (data.get("drawing") or {}) if isinstance(data, dict) else {}

    base: Dict[str, Any] = DrawingSettings().__dict__.copy()
    for k, v in d.items():
        if k in base:
            base[k] = v

    def as_int(x, default: int) -> int:
        try:
            return int(x)
        except Exception:
            return default

    def as_float(x, default: float) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def as_bool(x, default: bool) -> bool:
        try:
            return bool(x)
        except Exception:
            return default

    front_mode = str(base.get("front_mode", "external")).strip().lower()
    if front_mode not in ("external", "internal"):
        front_mode = "external"

    dim_end_style = str(base.get("dim_end_style", "arrows")).strip().lower()
    if dim_end_style not in ("arrows", "ticks"):
        dim_end_style = "arrows"

    return DrawingSettings(
        rect_line_color=str(base["rect_line_color"]),
        rect_line_width_px=max(1, as_int(base["rect_line_width_px"], 3)),

        dim_line_color=str(base["dim_line_color"]),
        dim_line_width_px=max(1, as_int(base["dim_line_width_px"], 3)),
        dim_end_style=dim_end_style,

        grid_enabled=as_bool(base["grid_enabled"], True),
        grid_step_mm=max(5.0, as_float(base["grid_step_mm"], 50.0)),
        grid_color=str(base["grid_color"]),
        grid_width_px=max(1, as_int(base["grid_width_px"], 1)),

        show_front_part=as_bool(base.get("show_front_part", True), True),
        front_mode=front_mode,

        edgeband_color=str(base.get("edgeband_color", "#cc0000")),
        edgeband_width_px=max(1, as_int(base.get("edgeband_width_px", 4), 4)),

        hinge_edge_offset_mm=max(0.0, as_float(base.get("hinge_edge_offset_mm", 12.0), 12.0)),
        auto_double_front_width_mm=max(100.0, as_float(base.get("auto_double_front_width_mm", 600.0), 600.0)),
    )


def save_drawing_settings(s: DrawingSettings) -> None:
    data = _load_settings_data()

    front_mode = (s.front_mode or "external").strip().lower()
    if front_mode not in ("external", "internal"):
        front_mode = "external"

    dim_end_style = (s.dim_end_style or "arrows").strip().lower()
    if dim_end_style not in ("arrows", "ticks"):
        dim_end_style = "arrows"

    data["drawing"] = {
        "rect_line_color": s.rect_line_color,
        "rect_line_width_px": int(s.rect_line_width_px),

        "dim_line_color": s.dim_line_color,
        "dim_line_width_px": int(s.dim_line_width_px),
        "dim_end_style": dim_end_style,

        "grid_enabled": bool(s.grid_enabled),
        "grid_step_mm": float(s.grid_step_mm),
        "grid_color": s.grid_color,
        "grid_width_px": int(s.grid_width_px),

        "show_front_part": bool(s.show_front_part),
        "front_mode": front_mode,

        "edgeband_color": s.edgeband_color,
        "edgeband_width_px": int(s.edgeband_width_px),

        "hinge_edge_offset_mm": float(s.hinge_edge_offset_mm),
        "auto_double_front_width_mm": float(s.auto_double_front_width_mm),
    }

    _save_settings_data(data)


def load_modul_splitter_sizes(default: list[int] | None = None) -> list[int]:
    fallback = list(default or [360, 900, 360])
    if len(fallback) != 3:
        fallback = [360, 900, 360]

    data = _load_settings_data()
    ui = data.get("ui") or {}
    raw = ui.get("modul_splitter_sizes") or []

    if not isinstance(raw, list) or len(raw) != 3:
        return list(fallback)

    out: list[int] = []
    for value in raw:
        try:
            parsed = int(value)
        except Exception:
            return list(fallback)
        if parsed <= 0:
            return list(fallback)
        out.append(parsed)

    return out


def save_modul_splitter_sizes(sizes: list[int] | tuple[int, int, int]) -> None:
    if len(sizes) != 3:
        return

    normalized: list[int] = []
    for value in sizes:
        try:
            parsed = int(value)
        except Exception:
            return
        normalized.append(max(1, parsed))

    data = _load_settings_data()
    ui = dict(data.get("ui") or {})
    ui["modul_splitter_sizes"] = normalized
    data["ui"] = ui
    _save_settings_data(data)


def load_table_column_widths(key: str, default: list[int] | None = None) -> list[int]:
    fallback = list(default or [])
    key_norm = str(key or "").strip()
    if not key_norm:
        return fallback

    data = _load_settings_data()
    ui = data.get("ui") or {}
    all_widths = ui.get("table_column_widths") or {}
    raw = all_widths.get(key_norm) if isinstance(all_widths, dict) else None
    if not isinstance(raw, list):
        return fallback

    out: list[int] = []
    for value in raw:
        try:
            parsed = int(value)
        except Exception:
            return fallback
        if parsed <= 0:
            return fallback
        out.append(parsed)
    return out


def save_table_column_widths(key: str, widths: list[int] | tuple[int, ...]) -> None:
    key_norm = str(key or "").strip()
    if not key_norm:
        return

    normalized: list[int] = []
    for value in widths:
        try:
            parsed = int(value)
        except Exception:
            return
        normalized.append(max(1, parsed))

    data = _load_settings_data()
    ui = dict(data.get("ui") or {})
    all_widths = dict(ui.get("table_column_widths") or {})
    all_widths[key_norm] = normalized
    ui["table_column_widths"] = all_widths
    data["ui"] = ui
    _save_settings_data(data)


def load_ui_string_list(key: str, default: list[str] | None = None) -> list[str]:
    fallback = list(default or [])
    key_norm = str(key or "").strip()
    if not key_norm:
        return fallback

    data = _load_settings_data()
    ui = data.get("ui") or {}
    all_lists = ui.get("string_lists") or {}
    raw = all_lists.get(key_norm) if isinstance(all_lists, dict) else None
    if not isinstance(raw, list):
        return fallback

    out: list[str] = []
    for value in raw:
        text = str(value or "").strip()
        if text:
            out.append(text)
    return out if out else fallback


def save_ui_string_list(key: str, values: list[str] | tuple[str, ...]) -> None:
    key_norm = str(key or "").strip()
    if not key_norm:
        return

    normalized: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text:
            normalized.append(text)

    data = _load_settings_data()
    ui = dict(data.get("ui") or {})
    all_lists = dict(ui.get("string_lists") or {})
    all_lists[key_norm] = normalized
    ui["string_lists"] = all_lists
    data["ui"] = ui
    _save_settings_data(data)


def load_ui_theme_settings() -> UiThemeSettings:
    data = _load_settings_data()
    ui = data.get("ui") or {}

    mode = str(ui.get("theme_mode", "day")).strip().lower()
    if mode not in ("day", "night"):
        mode = "day"

    motif = str(ui.get("theme_motif", "cream")).strip().lower()
    if motif not in ("cream", "blue", "gray", "green", "contrast"):
        motif = "cream"

    return UiThemeSettings(mode=mode, motif=motif)


def load_ui_font_scale(default: float = 1.0) -> float:
    data = _load_settings_data()
    ui = data.get("ui") or {}
    raw = ui.get("font_scale")
    if raw is None:
        return float(default)
    try:
        val = float(raw)
        return max(0.5, min(2.0, val))
    except Exception:
        return float(default)


def save_ui_font_scale(scale: float) -> None:
    data = _load_settings_data()
    ui = dict(data.get("ui") or {})
    ui["font_scale"] = float(max(0.5, min(2.0, scale)))
    data["ui"] = ui
    _save_settings_data(data)


def load_gmail_oauth_settings() -> GmailOAuthSettings:
    data = _load_settings_data()
    g = data.get("gmail_oauth") or {}
    try:
        return GmailOAuthSettings(
            enabled=bool(g.get("enabled", False)),
            client_id=str(g.get("client_id", "")),
            client_secret=str(g.get("client_secret", "")),
            max_fetch=int(g.get("max_fetch", 20)),
        )
    except Exception:
        return GmailOAuthSettings()


def save_gmail_oauth_settings(s: GmailOAuthSettings) -> None:
    data = _load_settings_data()
    data["gmail_oauth"] = {
        "enabled": bool(s.enabled),
        "client_id": str(s.client_id),
        "client_secret": str(s.client_secret),
        "max_fetch": int(s.max_fetch),
    }
    _save_settings_data(data)


def load_whatsapp_settings() -> WhatsAppSettings:
    data = _load_settings_data()
    w = data.get("whatsapp") or {}
    try:
        return WhatsAppSettings(
            enabled=bool(w.get("enabled", False)),
            account_sid=str(w.get("account_sid", "")),
            auth_token=str(w.get("auth_token", "")),
            to_number=str(w.get("to_number", "")),
            max_fetch=int(w.get("max_fetch", 20)),
        )
    except Exception:
        return WhatsAppSettings()


def save_whatsapp_settings(s: WhatsAppSettings) -> None:
    data = _load_settings_data()
    data["whatsapp"] = {
        "enabled": bool(s.enabled),
        "account_sid": str(s.account_sid),
        "auth_token": str(s.auth_token),
        "to_number": str(s.to_number),
        "max_fetch": int(s.max_fetch),
    }
    _save_settings_data(data)


def load_email_settings() -> EmailSettings:
    data = _load_settings_data()
    e = data.get("email") or {}
    try:
        return EmailSettings(
            enabled=bool(e.get("enabled", False)),
            host=str(e.get("host", "imap.gmail.com")),
            port=int(e.get("port", 993)),
            username=str(e.get("username", "")),
            password=str(e.get("password", "")),
            folder=str(e.get("folder", "INBOX")),
            max_fetch=int(e.get("max_fetch", 20)),
        )
    except Exception:
        return EmailSettings()


def save_email_settings(s: EmailSettings) -> None:
    data = _load_settings_data()
    data["email"] = {
        "enabled": bool(s.enabled),
        "host": str(s.host),
        "port": int(s.port),
        "username": str(s.username),
        "password": str(s.password),
        "folder": str(s.folder),
        "max_fetch": int(s.max_fetch),
    }
    _save_settings_data(data)


def load_telegram_settings() -> TelegramSettings:
    data = _load_settings_data()
    t = data.get("telegram") or {}
    try:
        return TelegramSettings(
            enabled=bool(t.get("enabled", False)),
            bot_token=str(t.get("bot_token", "")),
            chat_id=str(t.get("chat_id", "")),
        )
    except Exception:
        return TelegramSettings()


def save_telegram_settings(s: TelegramSettings) -> None:
    data = _load_settings_data()
    data["telegram"] = {
        "enabled": bool(s.enabled),
        "bot_token": str(s.bot_token),
        "chat_id": str(s.chat_id),
    }
    _save_settings_data(data)


@dataclass(frozen=True)
class DefaultMaterialSettings:
    """Domyslne materialy, grubosc i obrzeza dla nowych modulow."""
    # Materialy (klucze z katalogu CatalogStoreJson)
    carcass_material_key: str = ""      # korpus (boki, wiencce)
    carcass_thickness_mm: float = 18.0
    front_material_key: str = ""        # fronty
    front_thickness_mm: float = 18.0
    shelf_material_key: str = ""        # polki (puste = jak korpus)
    shelf_thickness_mm: float = 18.0
    back_material_key: str = ""         # plecy (puste = HDF)
    back_thickness_mm: float = 3.0

    # Obrzeza (klucze z katalogu)
    carcass_edgeband_key: str = ""      # obrzeze korpusu
    front_edgeband_key: str = ""        # obrzeze frontu

    # Nozki / cokol
    default_leg_height_mm: float = 100.0
    default_carcass_joint: str = "type1"  # typ polaczenia korpusu

    # Profil materialowy (klucz presetu)
    material_profile_key: str = ""


def load_default_material_settings() -> DefaultMaterialSettings:
    data = _load_settings_data()
    d = data.get("default_materials") or {}

    def _s(key: str, default: str) -> str:
        return str(d.get(key, default) or default)

    def _f(key: str, default: float) -> float:
        try:
            return float(d.get(key, default))
        except Exception:
            return default

    return DefaultMaterialSettings(
        carcass_material_key=_s("carcass_material_key", ""),
        carcass_thickness_mm=_f("carcass_thickness_mm", 18.0),
        front_material_key=_s("front_material_key", ""),
        front_thickness_mm=_f("front_thickness_mm", 18.0),
        shelf_material_key=_s("shelf_material_key", ""),
        shelf_thickness_mm=_f("shelf_thickness_mm", 18.0),
        back_material_key=_s("back_material_key", ""),
        back_thickness_mm=_f("back_thickness_mm", 3.0),
        carcass_edgeband_key=_s("carcass_edgeband_key", ""),
        front_edgeband_key=_s("front_edgeband_key", ""),
        default_leg_height_mm=_f("default_leg_height_mm", 100.0),
        default_carcass_joint=_s("default_carcass_joint", "type1"),
        material_profile_key=_s("material_profile_key", ""),
    )


def save_default_material_settings(s: DefaultMaterialSettings) -> None:
    data = _load_settings_data()
    data["default_materials"] = {
        "carcass_material_key": str(s.carcass_material_key),
        "carcass_thickness_mm": float(s.carcass_thickness_mm),
        "front_material_key": str(s.front_material_key),
        "front_thickness_mm": float(s.front_thickness_mm),
        "shelf_material_key": str(s.shelf_material_key),
        "shelf_thickness_mm": float(s.shelf_thickness_mm),
        "back_material_key": str(s.back_material_key),
        "back_thickness_mm": float(s.back_thickness_mm),
        "carcass_edgeband_key": str(s.carcass_edgeband_key),
        "front_edgeband_key": str(s.front_edgeband_key),
        "default_leg_height_mm": float(s.default_leg_height_mm),
        "default_carcass_joint": str(s.default_carcass_joint),
        "material_profile_key": str(s.material_profile_key),
    }
    _save_settings_data(data)


def save_ui_theme_settings(mode: str, motif: str) -> None:
    mode_norm = str(mode or "day").strip().lower()
    if mode_norm not in ("day", "night"):
        mode_norm = "day"

    motif_norm = str(motif or "cream").strip().lower()
    if motif_norm not in ("cream", "blue", "gray", "green", "contrast"):
        motif_norm = "cream"

    data = _load_settings_data()
    ui = dict(data.get("ui") or {})
    ui["theme_mode"] = mode_norm
    ui["theme_motif"] = motif_norm
    data["ui"] = ui
    _save_settings_data(data)
