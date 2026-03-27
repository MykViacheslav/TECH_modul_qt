from __future__ import annotations

from typing import List, Callable, Tuple, Any
from src.domain.alarm_models import AlarmDef
from src.storage.alarm_store_json import AlarmStoreJson


class AlarmService:
    """
    Central service for managing application-wide alarms.
    Implements singleton pattern and plug-in check rules.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # Prevent re-initialization
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self._rules: List[Tuple[Callable[[Any], List[AlarmDef]], str]] = []
        self._store = AlarmStoreJson()
        self._initialized = True
    
    @classmethod
    def instance(cls) -> 'AlarmService':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register_rule(self, 
                     check_func: Callable[[Any], List[AlarmDef]], 
                     description: str = "") -> None:
        """
        Register a new alarm check rule.
        
        Args:
            check_func: Function that takes context and returns list of AlarmDef
            description: Human-readable description for logging/debugging
        """
        self._rules.append((check_func, description))
    
    def run_all_checks(self, context: Any = None) -> List[AlarmDef]:
        """
        Execute all registered alarm check rules.
        
        Args:
            context: Optional context data passed to all check functions
            
        Returns:
            List of new alarms generated during this check cycle
        """
        new_alarms: List[AlarmDef] = []
        
        for check_func, description in self._rules:
            try:
                alarms = check_func(context)
                if alarms:
                    for alarm in alarms:
                        # Avoid duplicates: only add if not already present
                        if not self._alarm_exists(alarm):
                            self._store.save_alarm(alarm)
                            new_alarms.append(alarm)
            except Exception as e:
                # In production, you might want to log this properly
                print(f"Alarm check '{description}' failed: {e}")
                
        return new_alarms
    
    def _alarm_exists(self, alarm: AlarmDef) -> bool:
        """Check if an alarm with similar properties already exists."""
        existing_alarms = self._store.list_alarms()
        for existing in existing_alarms:
            # Simple deduplication: same title, category, and related order
            if (existing.title == alarm.title and 
                existing.category == alarm.category and
                existing.related_order == alarm.related_order and
                not existing.is_resolved):
                return True
        return False
    
    def get_active_alarms(self) -> List[AlarmDef]:
        """Get all active (unresolved) alarms."""
        return [a for a in self._store.list_alarms() if not a.is_resolved]
    
    def get_alarms_by_severity(self, severity: str) -> List[AlarmDef]:
        """Get alarms by severity level."""
        return [a for a in self.get_active_alarms() if a.severity == severity]
    
    def resolve_alarm(self, alarm_id: str) -> None:
        """Mark an alarm as resolved."""
        self._store.resolve_alarm(alarm_id)
    
    def clear_resolved_alarms(self) -> None:
        """Remove all resolved alarms from storage."""
        self._store.clear_resolved()