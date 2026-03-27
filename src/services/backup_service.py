"""
Automatic backup service for TECH_modul data.
Creates compressed backups of all JSON data files.
"""

from __future__ import annotations

import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from src.storage.data_paths import data_dir


class BackupService(QObject):
    """
    Service for automatic backup and restore of application data.
    
    Features:
    - Automatic daily backups
    - Configurable backup retention (number of backups to keep)
    - Zip compression to save space
    - Manual backup and restore
    
    Signals:
        backup_created: Emitted when backup is created (backup_path)
        backup_restored: Emitted when backup is restored
        backup_error: Emitted on error (error_message)
    """
    
    backup_created = pyqtSignal(str)  # backup_path
    backup_restored = pyqtSignal()
    backup_error = pyqtSignal(str)  # error_message
    
    _instance: Optional['BackupService'] = None
    _initialized: bool = False
    
    # Default settings
    DEFAULT_BACKUP_DIR = "backups"
    DEFAULT_MAX_BACKUPS = 30  # Keep 30 days of backups
    DEFAULT_CHECK_INTERVAL = 24 * 60 * 60 * 1000  # 24 hours in ms
    
    def __new__(cls) -> 'BackupService':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        if BackupService._initialized:
            return
        super().__init__()
        BackupService._initialized = True
        
        self._data_dir = data_dir()
        self._backup_dir = self._data_dir.parent / self.DEFAULT_BACKUP_DIR
        self._max_backups = self.DEFAULT_MAX_BACKUPS
        self._auto_backup_enabled = True
        self._last_backup_date: str = ""
        
        # Ensure backup directory exists
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Load last backup date from settings
        self._load_settings()
        
        # Setup auto-backup timer (checks daily)
        self._backup_timer = QTimer(self)
        self._backup_timer.setInterval(self.DEFAULT_CHECK_INTERVAL)
        self._backup_timer.timeout.connect(self._check_auto_backup)
        self._backup_timer.start()
        
        # Check immediately on startup (with delay)
        QTimer.singleShot(30000, self._check_auto_backup)  # 30 seconds delay
    
    @classmethod
    def instance(cls) -> 'BackupService':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _load_settings(self) -> None:
        """Load backup settings from settings file."""
        settings_path = self._data_dir / "backup_settings.json"
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8"))
                self._max_backups = settings.get("max_backups", self.DEFAULT_MAX_BACKUPS)
                self._auto_backup_enabled = settings.get("auto_backup_enabled", True)
                self._last_backup_date = settings.get("last_backup_date", "")
            except Exception:
                pass
    
    def _save_settings(self) -> None:
        """Save backup settings to file."""
        settings_path = self._data_dir / "backup_settings.json"
        settings = {
            "max_backups": self._max_backups,
            "auto_backup_enabled": self._auto_backup_enabled,
            "last_backup_date": self._last_backup_date,
        }
        try:
            settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    
    def _check_auto_backup(self) -> None:
        """Check if automatic backup is needed."""
        if not self._auto_backup_enabled:
            return
        
        today = datetime.now().strftime("%Y-%m-%d")
        if self._last_backup_date == today:
            return  # Already backed up today
        
        # Create backup
        try:
            self.create_backup()
        except Exception as e:
            self.backup_error.emit(str(e))
    
    def create_backup(self, name: Optional[str] = None) -> str:
        """
        Create a new backup of all data files.
        
        Args:
            name: Optional custom name for the backup
            
        Returns:
            Path to the created backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = name or f"backup_{timestamp}"
        backup_path = self._backup_dir / f"{backup_name}.zip"
        
        # Create zip archive
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add all JSON files from data directory
            for json_file in self._data_dir.glob("*.json"):
                zf.write(json_file, json_file.name)
            
            # Add subdirectories (like baza_materialu.json might be in a subfolder)
            for subdir in self._data_dir.iterdir():
                if subdir.is_dir():
                    for file in subdir.rglob("*.json"):
                        zf.write(file, file.relative_to(self._data_dir))
        
        # Update last backup date
        self._last_backup_date = datetime.now().strftime("%Y-%m-%d")
        self._save_settings()
        
        # Clean up old backups
        self._cleanup_old_backups()
        
        self.backup_created.emit(str(backup_path))
        return str(backup_path)
    
    def _cleanup_old_backups(self) -> None:
        """Remove old backups beyond the retention limit."""
        backups = sorted(
            self._backup_dir.glob("backup_*.zip"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # Remove oldest backups if we have too many
        while len(backups) > self._max_backups:
            old_backup = backups.pop()
            try:
                old_backup.unlink()
            except Exception:
                pass
    
    def restore_backup(self, backup_path: str) -> bool:
        """
        Restore data from a backup file.
        
        Args:
            backup_path: Path to the backup zip file
            
        Returns:
            True if successful, False otherwise
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            self.backup_error.emit(f"Backup not found: {backup_path}")
            return False
        
        try:
            # Create a safety backup before restoring
            safety_backup = self.create_backup(f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            # Extract backup to data directory
            with zipfile.ZipFile(backup_file, 'r') as zf:
                zf.extractall(self._data_dir)
            
            self.backup_restored.emit()
            return True
        except Exception as e:
            self.backup_error.emit(f"Restore failed: {e}")
            return False
    
    def list_backups(self) -> list[dict]:
        """
        List all available backups.
        
        Returns:
            List of backup info dicts with path, date, size
        """
        backups = []
        for backup_file in sorted(
            self._backup_dir.glob("backup_*.zip"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        ):
            stat = backup_file.stat()
            backups.append({
                "path": str(backup_file),
                "name": backup_file.stem,
                "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "size_mb": stat.st_size / (1024 * 1024),
            })
        return backups
    
    def delete_backup(self, backup_path: str) -> bool:
        """Delete a specific backup file."""
        try:
            Path(backup_path).unlink()
            return True
        except Exception:
            return False
    
    def get_backup_dir(self) -> str:
        """Get the backup directory path."""
        return str(self._backup_dir)
    
    def set_auto_backup(self, enabled: bool) -> None:
        """Enable or disable automatic backups."""
        self._auto_backup_enabled = enabled
        self._save_settings()
    
    def set_max_backups(self, count: int) -> None:
        """Set the maximum number of backups to keep."""
        self._max_backups = max(1, count)
        self._save_settings()
        self._cleanup_old_backups()
    
    def get_stats(self) -> dict:
        """Get backup statistics."""
        backups = self.list_backups()
        total_size = sum(b["size_mb"] for b in backups)
        return {
            "total_backups": len(backups),
            "total_size_mb": round(total_size, 2),
            "last_backup": self._last_backup_date,
            "auto_backup_enabled": self._auto_backup_enabled,
            "max_backups": self._max_backups,
        }


def create_backup_now() -> str:
    """Convenience function to create a backup immediately."""
    service = BackupService.instance()
    return service.create_backup()


def restore_latest_backup() -> bool:
    """Convenience function to restore the latest backup."""
    service = BackupService.instance()
    backups = service.list_backups()
    if not backups:
        return False
    return service.restore_backup(backups[0]["path"])
