"""
AssistantPanel — Collapsible UI panel with 5 sections for the assistant.

Sections:
1. "Co teraz zrobić" (Next step guidance)
2. "Najważniejsze ostrzeżenia" (Warnings from AlarmService)
3. "Szybkie akcje" (Quick navigation buttons)
4. "Pytaj asystenta" (Text input for queries)
5. "Ostatnie odpowiedzi" (Response history - session only)

Panel is lightweight, dockable, and can be minimized/closed.
"""

from __future__ import annotations

from typing import Optional, List, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QScrollArea,
    QGroupBox, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QColor

from src.core.assistant_context import AssistantContext
from src.core.assistant_query_engine import AssistantQueryEngine, AssistantResponse


class AssistantPanel(QWidget):
    """
    Main assistant panel widget with 5 sections.
    Emits signals for navigation actions (no direct widget manipulation).
    """

    # Signals emitted for actions (MainWindow will handle them)
    sig_navigate_requested = pyqtSignal(str)  # tab_title
    sig_action_requested = pyqtSignal(str)  # action_command
    sig_query_submitted = pyqtSignal(str)  # query_text
    sig_close_requested = pyqtSignal()  # user clicked close/minimize

    def __init__(self, parent=None):
        """Initialize the assistant panel."""
        super().__init__(parent)
        self.context = AssistantContext.instance()
        self.query_engine = AssistantQueryEngine(self.context)

        self._init_ui()
        self._connect_signals()
        self._history: List[str] = []  # Session-only history

    def _init_ui(self):
        """Build the 5-section UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Header: Title + minimize/close buttons
        header = self._build_header()
        main_layout.addWidget(header)

        # Section 1: Next step guidance
        self._section_next_step = self._build_section(
            "📌 Co teraz zrobić",
            "Oczekiwanie na zmianę zakładki..."
        )
        main_layout.addWidget(self._section_next_step)

        # Section 2: Warnings
        self._section_warnings = self._build_section(
            "⚠️  Najważniejsze ostrzeżenia",
            "Brak alarmów."
        )
        main_layout.addWidget(self._section_warnings)

        # Section 3: Quick actions
        self._section_quick_actions = self._build_quick_actions()
        main_layout.addWidget(self._section_quick_actions)

        # Section 4: Query input
        self._section_query = self._build_query_input()
        main_layout.addWidget(self._section_query)

        # Section 5: Response history
        self._section_history = self._build_history_list()
        main_layout.addWidget(self._section_history)

        self.setLayout(main_layout)
        self.setMinimumWidth(280)
        self.setMaximumWidth(400)

    def _build_header(self) -> QWidget:
        """Build the header with title and control buttons."""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Asystent")
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        title.setFont(title_font)

        layout.addWidget(title, 1)

        # Close button — emituje sygnał do MainWindow (który ma toggle)
        btn_close = QPushButton("✕")
        btn_close.setMaximumWidth(30)
        btn_close.setMaximumHeight(24)
        btn_close.setToolTip("Ukryj asystenta (przycisk ▶ po prawej przywraca)")
        btn_close.clicked.connect(self.sig_close_requested.emit)
        layout.addWidget(btn_close)

        return header

    def _build_section(self, title: str, placeholder: str) -> QGroupBox:
        """Build a text-only section (next step or warnings)."""
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        label = QLabel(placeholder)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        label.setStyleSheet("QLabel { color: #333; font-size: 11px; }")

        layout.addWidget(label)
        layout.addStretch()

        group.setLayout(layout)
        return group

    def _build_quick_actions(self) -> QGroupBox:
        """Build section 3: Quick action buttons."""
        group = QGroupBox("⚡ Szybkie akcje")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Quick action buttons (will be populated based on context)
        self._quick_action_buttons: List[QPushButton] = []

        # Default buttons
        btn_show_urgent = QPushButton("Pokaż pilne")
        btn_show_urgent.setMaximumHeight(28)
        btn_show_urgent.clicked.connect(lambda: self._emit_quick_action("what_urgent"))
        self._quick_action_buttons.append(btn_show_urgent)
        layout.addWidget(btn_show_urgent)

        btn_open_finance = QPushButton("Finanse")
        btn_open_finance.setMaximumHeight(28)
        btn_open_finance.clicked.connect(lambda: self._emit_quick_action("navigate:Finanse"))
        self._quick_action_buttons.append(btn_open_finance)
        layout.addWidget(btn_open_finance)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def _build_query_input(self) -> QGroupBox:
        """Build section 4: Text query input."""
        group = QGroupBox("❓ Pytaj asystenta")
        layout = QHBoxLayout(group)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._input_query = QLineEdit()
        self._input_query.setPlaceholderText("Wpisz pytanie...")
        self._input_query.setMaximumHeight(30)
        self._input_query.returnPressed.connect(self._on_query_submit)

        btn_submit = QPushButton("→")
        btn_submit.setMaximumWidth(30)
        btn_submit.setMaximumHeight(30)
        btn_submit.clicked.connect(self._on_query_submit)

        layout.addWidget(self._input_query)
        layout.addWidget(btn_submit)

        group.setLayout(layout)
        return group

    def _build_history_list(self) -> QGroupBox:
        """Build section 5: Response history (session-only)."""
        group = QGroupBox("📋 Ostatnie odpowiedzi")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._history_list = QListWidget()
        self._history_list.setMaximumHeight(120)
        self._history_list.setAlternatingRowColors(True)

        layout.addWidget(self._history_list)
        group.setLayout(layout)
        return group

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def _on_query_submit(self):
        """Handle query submission from input field."""
        query_text = self._input_query.text().strip()
        if not query_text:
            return

        # Clear input
        self._input_query.clear()

        # Process query
        response = self.query_engine.query(query_text)

        # Display response
        self._display_response(response)

        # Handle actions
        if response.actions:
            for action in response.actions:
                self._emit_action(action)

        # Add to history
        self._add_to_history(response.text)

    def _display_response(self, response: AssistantResponse):
        """Display response in the appropriate section based on level."""
        # For now, display in next_step section
        # In future, could display in different sections based on level
        label = self._section_next_step.findChild(QLabel)
        if label:
            label.setText(response.text)

    def _emit_action(self, action: dict):
        """Parse action dict and emit appropriate signal."""
        command = action.get("command", "")
        if command.startswith("navigate:"):
            tab_name = command.replace("navigate:", "")
            self.sig_navigate_requested.emit(tab_name)
        elif command.startswith("open_order:"):
            order_ref = command.replace("open_order:", "")
            self.sig_action_requested.emit(f"open_order:{order_ref}")
        else:
            self.sig_action_requested.emit(command)

    def _emit_quick_action(self, command: str):
        """Emit a quick action command."""
        if command == "what_urgent":
            response = self.query_engine.query("co jest pilne")
            self._display_response(response)
            if response.actions:
                for action in response.actions:
                    self._emit_action(action)
        else:
            self._emit_action({"command": command})

    def _add_to_history(self, response_text: str):
        """Add response to session history list (not persisted)."""
        self._history.append(response_text)
        item = QListWidgetItem(response_text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self._history_list.insertItem(0, item)

        # Limit to 10 most recent
        while self._history_list.count() > 10:
            self._history_list.takeItem(self._history_list.count() - 1)

    def _connect_signals(self):
        """Connect internal signals (none currently; add as needed)."""
        pass

    # =========================================================================
    # PUBLIC METHODS FOR MAINWINDOW
    # =========================================================================

    def on_tab_changed(self, tab_title: str, subtab: Optional[str] = None):
        """Called when active tab changes. Updates guidance section."""
        self.context.set_active_tab(tab_title, subtab)

        # Update next_step guidance
        from src.core.assistant_message_library import get_next_step_message
        msg = get_next_step_message(tab_title, self.context.get_role())
        if msg:
            label = self._section_next_step.findChild(QLabel)
            if label:
                label.setText(msg.text)

    def on_user_changed(self, worker_name: str, role: str):
        """Called when user logs in or changes. Updates context."""
        self.context.set_user(worker_name, role)

        # Refresh all sections (permissions may have changed)
        self.on_tab_changed(self.context.get_active_tab())

    def on_alarms_changed(self, alarm_texts: List[str]):
        """Called when alarms change. Updates warnings section."""
        # This will be called by MainWindow when AlarmService updates
        if alarm_texts:
            warning_text = "\n".join(f"• {text}" for text in alarm_texts)
        else:
            warning_text = "Brak alarmów."

        label = self._section_warnings.findChild(QLabel)
        if label:
            label.setText(warning_text)
