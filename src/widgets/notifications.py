"""
Desktop notification system for TECH_modul.
Uses native OS notifications via PyQt6.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon
from PyQt6.QtGui import QIcon


class NotificationType(str, Enum):
    """Types of notifications."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ALARM = "alarm"


class NotificationManager(QObject):
    """
    Manages desktop notifications.
    Uses system tray icon for native OS notifications.
    """
    
    sig_notification_shown = pyqtSignal(str, str, str)  # title, message, type
    
    _instance: Optional["NotificationManager"] = None
    
    def __new__(cls) -> "NotificationManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        super().__init__()
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._enabled = True
        self._sound_enabled = False
        
        self._init_tray()
    
    def _init_tray(self) -> None:
        """Initialize system tray icon."""
        app = QApplication.instance()
        if app and QSystemTrayIcon.isSystemTrayAvailable():
            self._tray_icon = QSystemTrayIcon(app)
            # Use app icon or default
            self._tray_icon.show()
    
    @property
    def enabled(self) -> bool:
        """Check if notifications are enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set notifications enabled."""
        self._enabled = value
    
    @property
    def sound_enabled(self) -> bool:
        """Check if sound notifications are enabled."""
        return self._sound_enabled
    
    @sound_enabled.setter
    def sound_enabled(self, value: bool) -> None:
        """Set sound notifications enabled."""
        self._sound_enabled = value
    
    def notify(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        duration: int = 5000,
    ) -> bool:
        """
        Show a desktop notification.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            duration: Display duration in ms
        
        Returns:
            True if notification was shown
        """
        if not self._enabled:
            return False
        
        # Map type to system tray icon message type
        icon_map = {
            NotificationType.INFO: QSystemTrayIcon.MessageIcon.Information,
            NotificationType.SUCCESS: QSystemTrayIcon.MessageIcon.Information,
            NotificationType.WARNING: QSystemTrayIcon.MessageIcon.Warning,
            NotificationType.ERROR: QSystemTrayIcon.MessageIcon.Critical,
            NotificationType.ALARM: QSystemTrayIcon.MessageIcon.Warning,
        }
        
        icon = icon_map.get(notification_type, QSystemTrayIcon.MessageIcon.Information)
        
        if self._tray_icon and self._tray_icon.isSystemTrayAvailable():
            self._tray_icon.showMessage(title, message, icon, duration)
            self.sig_notification_shown.emit(title, message, notification_type.value)
            return True
        
        # Fallback: show message box (non-blocking via timer)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._show_fallback_notification(title, message))
        
        return False
    
    def _show_fallback_notification(self, title: str, message: str) -> None:
        """Show fallback notification using message box."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setModal(False)
        msg.show()
    
    def notify_alarm(self, alarm_title: str, alarm_description: str = "") -> bool:
        """Show alarm notification."""
        message = alarm_description if alarm_description else alarm_title
        return self.notify(
            f"ALARM: {alarm_title}",
            message,
            NotificationType.ALARM,
            duration=10000,
        )
    
    def notify_order_status_change(self, order_code: str, new_status: str) -> bool:
        """Show order status change notification."""
        return self.notify(
            "Zmiana statusu zamowienia",
            f"{order_code} -> {new_status}",
            NotificationType.INFO,
        )
    
    def notify_save_success(self, entity_type: str, entity_id: str) -> bool:
        """Show save success notification."""
        return self.notify(
            "Zapisano",
            f"{entity_type}: {entity_id}",
            NotificationType.SUCCESS,
            duration=3000,
        )
    
    def notify_export_complete(self, filename: str) -> bool:
        """Show export complete notification."""
        return self.notify(
            "Eksport ukończony",
            f"Plik: {filename}",
            NotificationType.SUCCESS,
            duration=3000,
        )


def get_notification_manager() -> NotificationManager:
    """Get global notification manager instance."""
    return NotificationManager()


def notify(title: str, message: str, notification_type: NotificationType = NotificationType.INFO) -> bool:
    """Convenience function to show notification."""
    return get_notification_manager().notify(title, message, notification_type)
