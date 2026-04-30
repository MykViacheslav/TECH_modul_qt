from __future__ import annotations
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
from src.storage.sqlite_db import get_database
from src.domain.catalog_models import (
    Manufacturer, MaterialCategory, ProducerCollection, 
    CatalogItem, CatalogItemVariant, CatalogItemUsageRule
)

class CatalogStoreSqlite:
    def __init__(self):
        self.db = get_database()
        self._cached_manufacturers = {}
        self._cached_categories = {}

    def get_manufacturer_id_by_name(self, name: str) -> Optional[int]:
        name = name.strip()
        if name in self._cached_manufacturers: return self._cached_manufacturers[name]
        
        row = self.db.query_one("SELECT id FROM manufacturers WHERE name = ?", (name,))
        if row:
            self._cached_manufacturers[name] = row['id']
            return row['id']
        return None

    def get_category_id_by_name(self, name: str) -> Optional[int]:
        name = name.strip()
        if name in self._cached_categories: return self._cached_categories[name]

        row = self.db.query_one("SELECT id FROM material_categories WHERE name_pl = ? OR name_en = ?", (name, name))
        if row:
            self._cached_categories[name] = row['id']
            return row['id']
        return None

    def get_manufacturers(self) -> List[Manufacturer]:
        rows = self.db.execute("SELECT * FROM manufacturers WHERE is_active = 1 ORDER BY name")
        return [Manufacturer(**dict(r)) for r in rows]

    def create_manufacturer(self, m: Manufacturer) -> int:
        now = datetime.now().isoformat()
        query = """
            INSERT INTO manufacturers (name, code, website_url, country, notes, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        return self.db.execute_insert(query, (
            m.name, m.code, m.website_url, m.country, m.notes, 1 if m.is_active else 0, now
        ))

    def get_categories(self) -> List[MaterialCategory]:
        rows = self.db.execute("SELECT * FROM material_categories WHERE is_active = 1 ORDER BY sort_order, name_pl")
        return [MaterialCategory(**dict(r)) for r in rows]

    def get_catalog_items(self, category_id: Optional[int] = None, usage_type: Optional[str] = None, include_deleted: bool = False) -> List[CatalogItem]:
        query = "SELECT * FROM catalog_items WHERE is_active = 1"
        if not include_deleted:
            query += " AND is_deleted = 0"
        params = []

        if category_id:
            query += " AND category_id = ?"
            params.append(category_id)
        
        if usage_type:
            # Join with usage rules
            query = """
                SELECT ci.* FROM catalog_items ci
                JOIN catalog_item_usage_rules cur ON ci.id = cur.catalog_item_id
                WHERE ci.is_active = 1 AND cur.usage_type = ? AND cur.allowed = 1
            """
            params = [usage_type]

        rows = self.db.execute(query, tuple(params))
        return [CatalogItem(**dict(r)) for r in rows]

    def create_catalog_item(self, item: CatalogItem) -> int:
        now = datetime.now().isoformat()
        query = """
            INSERT INTO catalog_items (
                internal_code, producer_code, name, short_name, manufacturer_id, 
                collection_id, category_id, subcategory, item_type, base_unit,
                default_thickness_mm, color_name, decor_name, finish_name, 
                surface_code, grain_direction_mode, thumbnail_path, texture_path,
                preview_color_hex, description, producer_page_url, is_active, 
                is_favorite, is_imported, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            item.internal_code, item.producer_code, item.name, item.short_name,
            item.manufacturer_id, item.collection_id, item.category_id, item.subcategory,
            item.item_type, item.base_unit, item.default_thickness_mm, item.color_name,
            item.decor_name, item.finish_name, item.surface_code, item.grain_direction_mode,
            item.thumbnail_path, item.texture_path, item.preview_color_hex, item.description,
            item.producer_page_url, 1 if item.is_active else 0, 1 if item.is_favorite else 0,
            1 if item.is_imported else 0, now, now
        )
        return self.db.execute_insert(query, params)

    def add_usage_rule(self, rule: CatalogItemUsageRule) -> int:
        query = """
            INSERT INTO catalog_item_usage_rules (catalog_item_id, usage_type, allowed, is_default, priority, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        return self.db.execute_insert(query, (
            rule.catalog_item_id, rule.usage_type, 1 if rule.allowed else 0,
            1 if rule.is_default else 0, rule.priority, rule.notes
        ))

    def import_from_csv(self, csv_rows: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Expects keys: name, producer_code, manufacturer, category, thickness, price (optional)
        """
        stats = {"imported": 0, "skipped": 0, "errors": 0}
        
        for row in csv_rows:
            try:
                name = row.get("name")
                if not name: 
                    stats["skipped"] += 1
                    continue
                
                man_name = row.get("manufacturer")
                man_id = self.get_manufacturer_id_by_name(man_name) if man_name else None
                
                cat_name = row.get("category")
                cat_id = self.get_category_id_by_name(cat_name) if cat_name else None
                
                item = CatalogItem(
                    id=None,
                    name=name,
                    producer_code=row.get("producer_code"),
                    manufacturer_id=man_id,
                    category_id=cat_id,
                    default_thickness_mm=float(row.get("thickness", 0)) or None,
                    is_imported=True
                )
                
                self.create_catalog_item(item)
                stats["imported"] += 1
            except Exception as e:
                print(f"Import error for row {row}: {e}")
                stats["errors"] += 1
                
        return stats

    def soft_delete_catalog_item(self, item_id: int):
        return self.db.execute_update("UPDATE catalog_items SET is_deleted = 1 WHERE id = ?", (item_id,))

    def restore_catalog_item(self, item_id: int):
        return self.db.execute_update("UPDATE catalog_items SET is_deleted = 0 WHERE id = ?", (item_id,))
