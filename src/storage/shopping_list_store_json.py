from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from src.domain.shopping_models import ShoppingItemDef, new_shopping_id
from src.storage.data_paths import data_dir
from src.storage.safe_json_io import read_json_file, write_json_atomic


class ShoppingListStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = data_dir() / "shopping_list.json"
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            write_json_atomic(self._path, [], ensure_ascii=False, indent=2)

    def list_items(self) -> List[ShoppingItemDef]:
        data = read_json_file(self._path, default=[], expected_type=list)
        return [ShoppingItemDef.from_dict(item) for item in data if isinstance(item, dict)]

    def get_item(self, item_id: str) -> ShoppingItemDef | None:
        for item in self.list_items():
            if item.item_id == item_id:
                return item
        return None

    def save_item(self, item: ShoppingItemDef) -> None:
        items = self.list_items()
        replaced = False
        old_status = ""
        for i, it in enumerate(items):
            if it.item_id == item.item_id:
                old_status = it.status
                items[i] = item
                replaced = True
                break
        if not replaced:
            items.append(item)
        self._persist(items)
        # If status changed to "zakupiono", update material last price
        if item.status == "zakupiono" and old_status != "zakupiono" and item.material_id:
            from src.storage.material_store_json import MaterialStoreJson
            mat_store = MaterialStoreJson()
            mat_store.update_material_last_price(item.material_id, item.price_actual, item.supplier)

    def delete_item(self, item_id: str) -> None:
        items = [it for it in self.list_items() if it.item_id != item_id]
        self._persist(items)

    def add_shopping_item(
        self,
        material_id: str,
        material_name: str,
        quantity: float,
        unit: str,
        project_name: str = "",
        order_id: str = "",
    ) -> ShoppingItemDef:
        """Helper to add a new shopping item, avoiding duplicates.

        Deduplication: ten sam material_id + project_name (status aktywny)
        -> aktualizacja ilosci. Rozne projekty -> osobne pozycje.
        """
        pname = str(project_name or "").strip()
        oid = str(order_id or "").strip()
        for existing in self.list_items():
            if (
                existing.material_id == material_id
                and existing.status in ("do kupienia", "zamowiono")
                and str(existing.project_name or "").strip() == pname
            ):
                changed = False
                if quantity > existing.quantity_needed:
                    existing.quantity_needed = quantity
                    existing.last_updated = datetime.now().isoformat(timespec="seconds")
                    changed = True
                if self._apply_price_recommendation(existing):
                    existing.last_updated = datetime.now().isoformat(timespec="seconds")
                    changed = True
                if changed:
                    self.save_item(existing)
                return existing
        item = ShoppingItemDef(
            item_id=new_shopping_id(),
            material_id=material_id,
            material_name=material_name,
            quantity_needed=quantity,
            unit=unit,
            added_date=datetime.now().strftime("%Y-%m-%d"),
            status="do kupienia",
            last_updated=datetime.now().isoformat(timespec="seconds"),
            project_name=pname,
            order_id=oid,
        )
        self._apply_price_recommendation(item)
        self.save_item(item)
        return item

    def _apply_price_recommendation(self, item: ShoppingItemDef) -> bool:
        changed = False
        try:
            from src.services.shopping_price_compare_service import ShoppingPriceCompareService

            recommendation = ShoppingPriceCompareService().recommend_for_item(
                material_id=item.material_id,
                material_name=item.material_name,
                quantity=item.quantity_needed,
                unit=item.unit,
                preferred_basis="brutto",
                current_unit_price=item.price_estimate,
            )
        except Exception:
            return False

        if recommendation is None:
            return False

        best = recommendation.best_offer
        supplier = str(best.supplier or "").strip()
        if supplier and supplier != str(item.supplier or "").strip():
            item.supplier = supplier
            changed = True

        if best.unit_price > 0 and (item.price_estimate <= 0 or best.unit_price < item.price_estimate):
            item.price_estimate = float(best.unit_price)
            changed = True

        note_parts: list[str] = []
        if best.source:
            note_parts.append(best.source)
        if best.price_basis:
            note_parts.append(best.price_basis)
        note_hint = " / ".join(note_parts)
        note_line = f"Rekomendacja: {best.unit_price:.2f} zl"
        if note_hint:
            note_line += f" ({note_hint})"
        if note_line and note_line not in str(item.notes or ""):
            item.notes = (f"{item.notes} | {note_line}".strip(" |")) if item.notes else note_line
            changed = True
        return changed

    def _persist(self, items: List[ShoppingItemDef]) -> None:
        data = [it.to_dict() for it in items]
        write_json_atomic(self._path, data, ensure_ascii=False, indent=2)

    # Removed older aggregate_purchase_history implementation to keep only the newer one below

    def monthly_averages(self, months: int = 12) -> list[float]:
        """Return list of monthly average prices for last N months.
        Each entry is average price per item for that month (price_actual * quantity).
        If no data for a month, value is 0.0.
        """
        from datetime import date
        # Build list of (year, month) rounded to first day of month
        today = date.today()
        months_keys: list[tuple[int, int]] = []
        y, m = today.year, today.month
        for _ in range(months):
            months_keys.append((y, m))
            if m == 1:
                m = 12
                y -= 1
            else:
                m -= 1
        # initialize accumulators
        sums: dict[str, float] = {f"{yy}-{mm:02d}": 0.0 for (yy, mm) in months_keys}
        counts: dict[str, int] = {f"{yy}-{mm:02d}": 0 for (yy, mm) in months_keys}
        items = self.list_items()
        for it in items:
            if it.status != "zakupiono":
                continue
            added = getattr(it, 'added_date', '') or ''
            if not added:
                continue
            try:
                yr, mn, _ = added.split('-')
                key = f"{yr}-{int(mn):02d}"
            except Exception:
                continue
            if key in sums:
                val = (it.price_actual or 0.0) * (it.quantity_needed or 0.0)
                sums[key] += val
                counts[key] += int(it.quantity_needed or 0)
        result: list[float] = []
        for (yy, mm) in months_keys:
            key = f"{yy}-{mm:02d}"
            if counts.get(key, 0) > 0:
                result.append(sums.get(key, 0.0) / counts.get(key, 1))
            else:
                result.append(0.0)
        return result

    def aggregate_purchase_history(self, months: int = 3) -> tuple[float, int, float]:
        """Aggregate shopping history over last N months.
        Returns (total_spent, item_count, average_price_per_item).
        """
        from datetime import date, timedelta, datetime
        cutoff = date.today() - timedelta(days=months * 30)
        total = 0.0
        count = 0
        for it in self.list_items():
            if it.status != "zakupiono":
                continue
            if not it.added_date:
                continue
            try:
                added_dt = date.fromisoformat(it.added_date)
            except Exception:
                continue
            if added_dt < cutoff:
                continue
            qty = int(it.quantity_needed or 0)
            if qty <= 0:
                qty = 1
            total += (it.price_actual or 0.0) * qty
            count += qty
        avg = (total / count) if count > 0 else 0.0
        return total, count, avg

    def top_suppliers_by_total_spend(self, months: int = 12, top_n: int = 5) -> list[tuple[str, float, int]]:
        """Return top_n suppliers by total spend over the last `months` months.
        Returns a list of tuples: (supplier, total_spent, item_count).
        """
        from datetime import date, timedelta
        today = date.today()
        cutoff = today - timedelta(days=months * 30)
        supplier_totals: dict[str, tuple[float, int]] = {}
        for it in self.list_items():
            if it.status != "zakupiono":
                continue
            added = getattr(it, 'added_date', '') or ''
            if not added:
                continue
            try:
                year, month, _ = added.split('-')
                added_dt = date(int(year), int(month), 1)
            except Exception:
                continue
            if added_dt < cutoff:
                continue
            sup = it.supplier or "<nieznany>"
            amount = (it.price_actual or 0.0) * max(0.0, float(it.quantity_needed or 0.0))
            total, cnt = supplier_totals.get(sup, (0.0, 0))
            supplier_totals[sup] = (total + amount, cnt + int(max(0.0, float(it.quantity_needed or 0.0))))
        results = [(k, v[0], v[1]) for k, v in supplier_totals.items()]
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_n]

    def monthly_supplier_trends(self, months: int = 12) -> dict[str, list[float]]:
        """Return per-supplier monthly spend series for the last `months` months.
        Each supplier maps to a list of length `months` with spend per month (oldest->newest).
        """
        from datetime import date
        today = date.today()
        # Build keys for months: oldest to newest
        keys: list[tuple[int, int]] = []
        y, m = today.year, today.month
        for _ in range(months):
            keys.insert(0, (y, m))  # oldest first
            if m == 1:
                m = 12
                y -= 1
            else:
                m -= 1
        # initialize series per supplier
        suppliers: dict[str, list[float]] = {}
        for (yy, mm) in keys:
            k = f"{yy}-{mm:02d}"
            # ensure all suppliers have a list; we'll fill dynamically when we see supplier
            pass
        items = self.list_items()
        for it in items:
            if it.status != "zakupiono":
                continue
            added = getattr(it, 'added_date', '') or ''
            if not added:
                continue
            try:
                year, month, _ = added.split('-')
                added_dt = date(int(year), int(month), 1)
            except Exception:
                continue
            # compute index: oldest first
            index = None
            try:
                # find position in keys
                for idx, (yy, mm) in enumerate(keys):
                    if int(year) == yy and int(month) == mm:
                        index = idx
                        break
            except Exception:
                index = None
            if index is None:
                continue
            supplier = it.supplier or "<nieznany>"
            amount = (it.price_actual or 0.0) * max(0.0, float(it.quantity_needed or 0.0))
            lst = suppliers.get(supplier, [0.0] * len(keys))
            lst[index] += amount
            suppliers[supplier] = lst
        return suppliers

    def top_suppliers_by_total_spend(self, months: int = 12, top_n: int = 3) -> list[tuple[str, float, int]]:
        """Return top_n suppliers by total spend over the last `months` months.
        Returns a list of tuples: (supplier, total_spent, item_count).
        """
        from datetime import date, timedelta
        cutoff = date.today() - timedelta(days=months * 30)
        supplier_totals: dict[str, tuple[float, int]] = {}
        items = self.list_items()
        for it in items:
            if it.status != "zakupiono":
                continue
            added = getattr(it, "added_date", "") or ""
            if not added:
                continue
            try:
                added_dt = date.fromisoformat(added)
            except Exception:
                continue
            if added_dt < cutoff:
                continue
            sup = it.supplier or "<nieznany>"
            amount = (it.price_actual or 0.0) * max(0.0, float(it.quantity_needed or 0.0))
            prev = supplier_totals.get(sup, (0.0, 0))
            supplier_totals[sup] = (prev[0] + amount, prev[1] + int(max(0, float(it.quantity_needed or 0.0))))
        # convert to list and sort by total spend desc
        result = [(k, v[0], v[1]) for k, v in supplier_totals.items()]
        result.sort(key=lambda x: x[1], reverse=True)
        return result[:top_n]
