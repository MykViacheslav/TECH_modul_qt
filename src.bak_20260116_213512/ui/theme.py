from __future__ import annotations

def apply_theme(app) -> None:
    """
    Delikatny jasny theme (soft gray). WAŻNE:
    - NIE wolno robić app.setStyleSheet(...) na poziomie importu modułu.
    - Tylko tutaj, po stworzeniu QApplication.
    """
    qss = """
    * {
        font-family: Segoe UI;
        color: #0f172a;
    }

    QWidget {
        background: #eef1f5;
    }

    QFrame, QGroupBox {
        background: #f7f8fb;
        border: 1px solid #d6dbe3;
        border-radius: 10px;
    }

    QGroupBox {
        margin-top: 10px;
        padding: 10px;
        font-weight: 700;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        top: 2px;
        padding: 0 6px;
        background: transparent;
        color: #0f172a;
    }

    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
        background: #ffffff;
        border: 1px solid #d6dbe3;
        border-radius: 8px;
        padding: 6px 8px;
        selection-background-color: #f59e0b;
    }

    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
        border: 1px solid #f59e0b;
    }

    QPushButton {
        background: #f2f4f8;
        border: 1px solid #d6dbe3;
        border-radius: 10px;
        padding: 8px 10px;
        font-weight: 600;
    }
    QPushButton:hover {
        background: #e6eaf2;
    }
    QPushButton:pressed {
        background: #dde3ee;
    }

    QTabWidget::pane {
        border: 1px solid #d6dbe3;
        border-radius: 12px;
        background: #eef1f5;
        padding: 6px;
    }

    QTabBar::tab {
        background: #f2f4f8;
        border: 1px solid #d6dbe3;
        border-bottom: none;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        padding: 10px 14px;
        margin-right: 6px;
        min-width: 140px;
        font-weight: 700;
    }

    QTabBar::tab:selected {
        background: #ffffff;
        border: 1px solid #d6dbe3;
        border-bottom: 3px solid #f59e0b;
    }

    QCheckBox {
        spacing: 10px;
        font-weight: 800;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
    }

    QScrollArea {
        border: none;
        background: transparent;
    }
    """
    app.setStyleSheet(qss)
