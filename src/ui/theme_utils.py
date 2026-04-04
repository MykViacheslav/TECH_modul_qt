"""
Theme helper utilities for consistent styling across tabs.
"""
from src.app.app_settings import load_ui_theme_settings


def get_muted_color() -> str:
    """Returns the muted text color based on current theme."""
    theme = load_ui_theme_settings()
    is_tech = str(theme.motif or "").strip().lower() == "tech" and str(theme.mode or "").strip().lower() == "night"
    return "#9bb0cd" if is_tech else "#555555"


def get_theme_colors() -> dict[str, str]:
    """Returns a dict of theme colors for use in stylesheets."""
    theme = load_ui_theme_settings()
    is_tech = str(theme.motif or "").strip().lower() == "tech" and str(theme.mode or "").strip().lower() == "night"
    is_night = str(theme.mode or "").strip().lower() == "night"
    
    if is_night:
        return {
            "text": "#e8efff" if is_tech else "#1f2937",
            "muted": "#9bb0cd" if is_tech else "#666666",
            "bg": "#10172a" if is_tech else "#fbf9f5",
            "border": "#2a4368" if is_tech else "#e6d9c8",
        }
    else:
        return {
            "text": "#12243e" if is_tech else "#1f2937",
            "muted": "#64748b" if is_tech else "#555555",
            "bg": "#f4f7fd" if is_tech else "#fbf9f5",
            "border": "#d9e0ea" if is_tech else "#e6d9c8",
        }
