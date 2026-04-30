from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class KnowledgeEntry:
    id: Optional[int]
    title: str
    entry_type: str # article, video, manual, workshop_note
    manufacturer_id: Optional[int] = None
    related_catalog_item_id: Optional[int] = None
    related_category_id: Optional[int] = None
    content_md: Optional[str] = None
    summary: Optional[str] = None
    difficulty_level: str = "beginner" # beginner, advanced, expert
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass(frozen=True)
class KnowledgeAttachment:
    id: Optional[int]
    knowledge_entry_id: int
    attachment_type: str # pdf, image, link
    file_path: Optional[str] = None
    external_url: Optional[str] = None
    title: Optional[str] = None
    sort_order: int = 0
