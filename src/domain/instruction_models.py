from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class InstructionCardDef:
    instruction_id: str = ""
    category: str = "ogolne"
    title: str = ""
    when_to_use: str = ""
    impact: str = ""
    steps: str = ""
    visualization_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "instruction_id": self.instruction_id,
            "category": self.category,
            "title": self.title,
            "when_to_use": self.when_to_use,
            "impact": self.impact,
            "steps": self.steps,
            "visualization_path": self.visualization_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InstructionCardDef":
        payload = dict(data or {})
        return cls(
            instruction_id=str(payload.get("instruction_id", "") or ""),
            category=str(payload.get("category", "ogolne") or "ogolne").lower(),
            title=str(payload.get("title", "") or ""),
            when_to_use=str(payload.get("when_to_use", "") or ""),
            impact=str(payload.get("impact", "") or ""),
            steps=str(payload.get("steps", "") or ""),
            visualization_path=str(payload.get("visualization_path", "") or ""),
        )
