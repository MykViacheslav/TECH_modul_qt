from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

@dataclass(frozen=True)
class Manufacturer:
    id: Optional[int]
    name: str
    code: Optional[str] = None
    website_url: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "website_url": self.website_url,
            "country": self.country,
            "notes": self.notes,
            "is_active": self.is_active
        }

@dataclass(frozen=True)
class MaterialCategory:
    id: Optional[int]
    code: str
    name_pl: str
    parent_id: Optional[int] = None
    name_en: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True

@dataclass(frozen=True)
class ProducerCollection:
    id: Optional[int]
    manufacturer_id: int
    name: str
    code: Optional[str] = None
    year_label: Optional[str] = None
    source_ref: Optional[str] = None
    is_active: bool = True

@dataclass(frozen=True)
class CatalogItem:
    id: Optional[int]
    name: str
    internal_code: Optional[str] = None
    producer_code: Optional[str] = None
    short_name: Optional[str] = None
    manufacturer_id: Optional[int] = None
    collection_id: Optional[int] = None
    category_id: Optional[int] = None
    subcategory: Optional[str] = None
    item_type: Optional[str] = None # board, hinge, etc.
    base_unit: str = "pcs"
    default_thickness_mm: Optional[float] = None
    color_name: Optional[str] = None
    decor_name: Optional[str] = None
    finish_name: Optional[str] = None
    surface_code: Optional[str] = None
    grain_direction_mode: str = "none" # none, optional, required
    thumbnail_path: Optional[str] = None
    texture_path: Optional[str] = None
    preview_color_hex: Optional[str] = None
    description: Optional[str] = None
    producer_page_url: Optional[str] = None
    is_active: bool = True
    is_favorite: bool = False
    is_imported: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass(frozen=True)
class CatalogItemVariant:
    id: Optional[int]
    catalog_item_id: int
    variant_code: Optional[str] = None
    thickness_mm: Optional[float] = None
    length_mm: Optional[float] = None
    width_mm: Optional[float] = None
    depth_mm: Optional[float] = None
    height_mm: Optional[float] = None
    capacity_kg: Optional[float] = None
    finish_name: Optional[str] = None
    color_name: Optional[str] = None
    unit: Optional[str] = None
    is_default: bool = False
    is_active: bool = True

@dataclass(frozen=True)
class CatalogItemUsageRule:
    id: Optional[int]
    catalog_item_id: int
    usage_type: str # carcass, front, back_panel, etc.
    allowed: bool = True
    is_default: bool = False
    priority: int = 0
    notes: Optional[str] = None
