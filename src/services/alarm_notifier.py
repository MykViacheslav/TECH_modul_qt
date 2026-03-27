"""
Sound notification service for critical alarms.
Plays alert sounds when new critical alarms are detected.
"""

from __future__ import annotations

import os
import platform
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from src.domain.alarm_models import AlarmDef
from src.storage.alarm_store_json import AlarmStoreJson


class AlarmNotifier(QObject):
    """
    Monitors alarm store and plays notifications for new critical alarms.
    
    Signals:
        critical_alarm_detected: Emitted when new critical alarm is found (alarm)
        warning_alarm_detected: Emitted when new warning is found (alarm)
    """
    
    critical_alarm_detected = pyqtSignal(object)  # AlarmDef
    warning_alarm_detected = pyqtSignal(object)  # AlarmDef
    
    _instance: Optional['AlarmNotifier'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'AlarmNotifier':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        # Prevent re-initialization
        if AlarmNotifier._initialized:
            return
        super().__init__()
        AlarmNotifier._initialized = True
        
        self._store = AlarmStoreJson()
        self._known_alarm_ids: set[str] = set()
        self._sound_enabled: bool = True
        
        # Initialize known alarms
        self._refresh_known_alarms()
        
        # Setup periodic check - disabled by default for performance
        # Enable only if sound notifications are needed
        self._check_timer = QTimer(self)
        self._check_timer.setInterval(60000)  # Check every 60 seconds (was 10s)
        self._check_timer.timeout.connect(self._check_new_alarms)
        # Don't start automatically - user must enable explicitly
        # self._check_timer.start()
    
    @classmethod
    def instance(cls) -> 'AlarmNotifier':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def set_sound_enabled(self, enabled: bool) -> None:
        """Enable or disable sound notifications."""
        self._sound_enabled = enabled
    
    def is_sound_enabled(self) -> bool:
        """Check if sound notifications are enabled."""
        return self._sound_enabled
    
    def _refresh_known_alarms(self) -> None:
        """Load all existing alarm IDs into known set."""
        for alarm in self._store.list_alarms():
            self._known_alarm_ids.add(alarm.alarm_id)
    
    def _check_new_alarms(self) -> None:
        """Check for new alarms and notify if needed."""
        try:
            current_alarms = self._store.list_alarms()
            
            for alarm in current_alarms:
                if alarm.alarm_id in self._known_alarm_ids:
                    continue
                if alarm.is_resolved:
                    continue
                
                # New alarm found!
                self._known_alarm_ids.add(alarm.alarm_id)
                
                if alarm.severity == "krytyczny":
                    self._play_critical_sound()
                    self.critical_alarm_detected.emit(alarm)
                elif alarm.severity == "ostrzezenie":
                    self._play_warning_sound()
                    self.warning_alarm_detected.emit(alarm)
        except Exception:
            pass
    
    def _play_critical_sound(self) -> None:
        """Play sound for critical alarm."""
        if not self._sound_enabled:
            return
        self._beep(frequency=800, duration=300, repeats=3)
    
    def _play_warning_sound(self) -> None:
        """Play sound for warning alarm."""
        if not self._sound_enabled:
            return
        self._beep(frequency=500, duration=200, repeats=1)
    
    def _beep(self, frequency: int = 440, duration: int = 200, repeats: int = 1) -> None:
        """
        Play a beep sound using platform-specific methods.
        
        Args:
            frequency: Sound frequency in Hz (not all platforms support this)
            duration: Duration in milliseconds
            repeats: Number of times to repeat
        """
        system = platform.system()
        
        try:
            if system == "Windows":
                self._beep_windows(frequency, duration, repeats)
            elif system == "Linux":
                self._beep_linux(frequency, duration, repeats)
            elif system == "Darwin":  # macOS
                self._beep_macos(frequency, duration, repeats)
        except Exception:
            # Fallback: try using simple print with bell character
            try:
                for _ in range(repeats):
                    print("\a", end="", flush=True)
            except Exception:
                pass
    
    def _beep_windows(self, frequency: int, duration: int, repeats: int) -> None:
        """Play beep on Windows using winsound."""
        import winsound
        for _ in range(repeats):
            winsound.Beep(frequency, duration)
    
    def _beep_linux(self, frequency: int, duration: int, repeats: int) -> None:
        """Play beep on Linux using console codes."""
        import sys
        # Linux console bell
        for _ in range(repeats):
            sys.stdout.write("\a")
            sys.stdout.flush()
            import time
            time.sleep(duration / 1000.0)
    
    def _beep_macos(self, frequency: int, duration: int, repeats: int) -> None:
        """Play beep on macOS using osascript."""
        import subprocess
        # Use system beep on macOS
        for _ in range(repeats):
            subprocess.run(["osascript", "-e", "beep"], capture_output=True)
    
    def force_check(self) -> None:
        """Manually trigger a check for new alarms."""
        self._check_new_alarms()
    
    def reset(self) -> None:
        """Reset the notifier state (for testing)."""
        self._known_alarm_ids.clear()
        self._refresh_known_alarms()


class ToastNotifier:
    """
    Shows toast notifications for alarms in the UI.
    Call show() to display a notification.
    """
    
    @staticmethod
    def show_critical(parent, alarm: AlarmDef) -> None:
        """Show critical alarm notification."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(
            parent,
            "🚨 ALARM KRYTYCZNY",
            f"<b>{alarm.title}</b><br><br>"
            f"{alarm.description}<br><br>"
            f"<small>Kategoria: {alarm.category}</small>"
        )
    
    @staticmethod
    def show_warning(parent, alarm: AlarmDef) -> None:
        """Show warning notification."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            parent,
            "⚠️ Ostrzeżenie",
            f"<b>{alarm.title}</b><br><br>"
            f"{alarm.description}"
        )
