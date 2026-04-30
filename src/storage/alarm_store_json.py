from __future__ import annotations

import json
from pathlib import Path
from typing import List

from PyQt6.QtCore import QObject, pyqtSignal

from src.domain.alarm_models import AlarmDef
from src.storage.data_paths import data_dir


class AlarmStoreJson(QObject):
    # Signal emitowany gdy alarmy się zmieniają
    alarms_changed = pyqtSignal()

    def __init__(self, path: Path | None = None) -> None:
        super().__init__()
        if path is None:
            path = data_dir() / "alarms.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")

    def list_alarms(self) -> List[AlarmDef]:
        try:
            text = self._path.read_text(encoding="utf-8")
            data = json.loads(text) if text.strip() else []
            if not isinstance(data, list):
                return []
            return [AlarmDef.from_dict(item) for item in data if isinstance(item, dict)]
        except Exception:
            return []

    def save_alarm(self, alarm: AlarmDef) -> None:
        alarms = self.list_alarms()
        for i, existing in enumerate(alarms):
            if existing.alarm_id == alarm.alarm_id:
                alarms[i] = alarm
                break
        else:
            alarms.append(alarm)
        self._save_all(alarms)

    def delete_alarm(self, alarm_id: str) -> None:
        alarms = self.list_alarms()
        alarms = [a for a in alarms if a.alarm_id != alarm_id]
        self._save_all(alarms)

    def delete_alarms_by_source(self, source: str) -> None:
        """Deletes all unresolved alarms belonging to a specific source in a single batch."""
        alarms = self.list_alarms()
        new_alarms = [
            a for a in alarms
            if a.is_resolved or str((a.extra or {}).get("source", "") or "") != source
        ]
        if len(new_alarms) != len(alarms):
            self._save_all(new_alarms)

    def resolve_alarm(self, alarm_id: str) -> None:
        from datetime import datetime
        alarms = self.list_alarms()
        for alarm in alarms:
            if alarm.alarm_id == alarm_id:
                alarm.is_resolved = True
                alarm.resolved_at = datetime.now().strftime("%Y-%m-%d %H:%M")
                break
        self._save_all(alarms)

    def clear_resolved(self) -> None:
        alarms = self.list_alarms()
        alarms = [a for a in alarms if not a.is_resolved]
        self._save_all(alarms)

    def save_alarms_batch(self, alarms_to_save: List[AlarmDef]) -> None:
        """Saves multiple alarms in a single operation."""
        if not alarms_to_save:
            return
        
        current_alarms = {a.alarm_id: a for a in self.list_alarms()}
        for alarm in alarms_to_save:
            current_alarms[alarm.alarm_id] = alarm
        
        self._save_all(list(current_alarms.values()))

    def _save_all(self, alarms: List[AlarmDef]) -> None:
        data = [alarm.to_dict() for alarm in alarms]
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        # Emituj signal aby inne komponenty wiedziały że alarmy się zmieniły
        self.alarms_changed.emit()
