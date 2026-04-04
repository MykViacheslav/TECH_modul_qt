from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget


def refresh_widget_style(widget: QWidget) -> None:
    if widget is None:
        return
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def set_ui_variant(widget: QWidget, variant: str) -> None:
    if widget is None:
        return
    widget.setProperty("uiVariant", str(variant or "").strip().lower())
    refresh_widget_style(widget)


def mark_ui_card(widget: QWidget, elevated: bool = True) -> None:
    if widget is None:
        return
    widget.setProperty("uiCard", True)
    if elevated:
        apply_soft_shadow(widget)
    refresh_widget_style(widget)


def apply_soft_shadow(
    widget: QWidget,
    *,
    blur_radius: float = 18.0,
    y_offset: float = 2.0,
    alpha: int = 36,
) -> None:
    if widget is None:
        return
    effect = QGraphicsDropShadowEffect(widget)
    color = QColor("#111827")
    color.setAlpha(max(0, min(255, int(alpha))))
    effect.setColor(color)
    effect.setBlurRadius(max(0.0, float(blur_radius)))
    effect.setOffset(0.0, float(y_offset))
    widget.setGraphicsEffect(effect)
