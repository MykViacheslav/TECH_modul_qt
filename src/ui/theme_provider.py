from __future__ import annotations
from PyQt6.QtGui import QColor

class ThemeProvider:
    """
    Centralne źródło prawdy dla designu PREMIUM TECH.
    Definiuje paletę barw, style QSS i parametry wizualne.
    """
    
    # --- Paleta barw (Premium Dark Mode) ---
    COLORS = {
        "bg_main": "#020617",         # Głębia midnight
        "bg_pane": "#0f172a",         # Slate navy
        "bg_card": "rgba(30, 41, 59, 0.7)", # Glassmorphism base
        "border_subtle": "rgba(59, 130, 246, 0.15)",
        "accent_blue": "#3b82f6",     # Electric Blue
        "accent_cyan": "#06b6d4",
        "accent_red": "#ef4444",      # Alerty
        "text_main": "#f8fafc",       # Czysta biel/szary
        "text_muted": "#94a3b8",      # Slate blue
        "shadow": "rgba(0, 0, 0, 0.5)"
    }

    @staticmethod
    def get_global_stylesheet() -> str:
        """Zwraca główny arkusz stylów dla całej aplikacji."""
        c = ThemeProvider.COLORS
        return f"""
            QMainWindow {{ background: {c['bg_main']}; }}
            
            /* --- Styl szklanych kart --- */
            [uiCard="true"], [uiCard="True"], .uiCard {{
                background: {c['bg_card']};
                border: 1px solid {c['border_subtle']};
                border-radius: 16px;
                padding: 10px;
            }}
            
            /* --- Akcenty techniczne --- */
            .uiAccentBorder {{
                border-left: 4px solid {c['accent_blue']};
            }}
            
            /* --- Przyciski Premium --- */
            QPushButton {{
                background: rgba(59, 130, 246, 0.08);
                border: 1px solid {c['border_subtle']};
                color: {c['text_main']};
                border-radius: 10px;
                font-weight: 700;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background: rgba(59, 130, 246, 0.15);
                border-color: {c['accent_blue']};
            }}
            QPushButton:pressed {{
                background: {c['accent_blue']};
            }}
            
            /* --- Tabele i listy --- */
            QHeaderView::section {{
                background: {c['bg_pane']};
                color: {c['text_muted']};
                font-weight: 800;
                padding: 6px;
                border: none;
                border-bottom: 2px solid {c['border_subtle']};
            }}
            
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {c['border_subtle']};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c['accent_blue']};
            }}
        """

    @staticmethod
    def apply_theme(widget):
        """Aplikuje globalny styl do podanego widgetu (zwykle MainWindow)."""
        widget.setStyleSheet(ThemeProvider.get_global_stylesheet())
