from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
import re
from typing import Any

from src.storage.data_paths import data_dir
from src.storage.safe_json_io import read_json_file, write_json_atomic


def new_invoice_id() -> str:
    return uuid.uuid4().hex.upper()


class InvoiceStoreJson:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else data_dir() / "invoices.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            write_json_atomic(self._path, {"invoices": []}, ensure_ascii=False, indent=2)

    def list_invoices(self) -> list[dict[str, Any]]:
        payload = self._read_payload()
        rows = payload.get("invoices", [])
        if not isinstance(rows, list):
            return []
        cleaned = [dict(row) for row in rows if isinstance(row, dict)]
        cleaned.sort(
            key=lambda row: str(row.get("received_at", "") or row.get("imported_at", "") or ""),
            reverse=True,
        )
        return cleaned

    def get(self, invoice_id: str) -> dict[str, Any] | None:
        invoice_id_norm = str(invoice_id or "").strip()
        if not invoice_id_norm:
            return None
        for row in self.list_invoices():
            if str(row.get("invoice_id", "") or "").strip() == invoice_id_norm:
                return row
        return None

    def upsert_invoice(self, invoice: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        payload = self._read_payload()
        rows = payload.get("invoices", [])
        if not isinstance(rows, list):
            rows = []

        item = dict(invoice or {})
        if not str(item.get("invoice_id", "") or "").strip():
            item["invoice_id"] = new_invoice_id()
        if not str(item.get("imported_at", "") or "").strip():
            item["imported_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        item.setdefault("exported_to_material", False)
        item.setdefault("exported_at", "")
        item.setdefault("telegram_sent", False)
        item.setdefault("account_type", "bank")
        item.setdefault("purchase_channel", "faktura")


        payload_hash = str(item.get("payload_hash", "") or "").strip().lower()
        attachment_key = str(item.get("attachment_key", "") or "").strip().lower()
        invoice_id = str(item.get("invoice_id", "") or "").strip()
        item_signature = self._invoice_signature(item)

        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            row_invoice_id = str(row.get("invoice_id", "") or "").strip()
            row_payload_hash = str(row.get("payload_hash", "") or "").strip().lower()
            row_attachment_key = str(row.get("attachment_key", "") or "").strip().lower()

            same_id = row_invoice_id and row_invoice_id == invoice_id
            same_hash = payload_hash and row_payload_hash and row_payload_hash == payload_hash
            same_attachment = attachment_key and row_attachment_key and row_attachment_key == attachment_key
            same_signature = self._is_same_invoice_signature(item_signature, self._invoice_signature(row))
            if same_id or same_hash or same_attachment or same_signature:
                if row_invoice_id:
                    item["invoice_id"] = row_invoice_id
                if str(row.get("imported_at", "") or "").strip():
                    item["imported_at"] = str(row.get("imported_at", "") or "").strip()
                # Keep previous export flags if already exported.
                if bool(row.get("exported_to_material", False)):
                    item["exported_to_material"] = True
                    item["exported_at"] = str(row.get("exported_at", "") or "")
                    prev_export_ids = row.get("exported_material_ids", [])
                    if isinstance(prev_export_ids, list):
                        item["exported_material_ids"] = [
                            str(value or "").strip()
                            for value in prev_export_ids
                            if str(value or "").strip()
                        ]
                    item["exported_material_count"] = int(row.get("exported_material_count", 0) or 0)
                    item["last_export_imported_lines"] = int(row.get("last_export_imported_lines", 0) or 0)
                    item["last_export_skipped_lines"] = int(row.get("last_export_skipped_lines", 0) or 0)
                if bool(row.get("telegram_sent", False)):
                    item["telegram_sent"] = True
                if same_signature and not (same_id or same_hash or same_attachment):
                    item["duplicate_reason"] = "invoice_signature"
                    item["duplicate_of_invoice_id"] = row_invoice_id
                else:
                    item["duplicate_reason"] = str(row.get("duplicate_reason", "") or "").strip()
                    item["duplicate_of_invoice_id"] = str(row.get("duplicate_of_invoice_id", "") or "").strip()
                rows[idx] = item
                payload["invoices"] = rows
                self._write_payload(payload)
                return False, item

        rows.append(item)
        payload["invoices"] = rows
        self._write_payload(payload)
        return True, item

    def mark_exported(
        self,
        invoice_id: str,
        *,
        exported_material_ids: list[str] | None = None,
        imported_lines: int | None = None,
        skipped_lines: int | None = None,
    ) -> None:
        payload = self._read_payload()
        rows = payload.get("invoices", [])
        if not isinstance(rows, list):
            return
        invoice_id_norm = str(invoice_id or "").strip()
        if not invoice_id_norm:
            return
        changed = False
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("invoice_id", "") or "").strip() != invoice_id_norm:
                continue
            row["exported_to_material"] = True
            row["exported_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            prev_ids = row.get("exported_material_ids", [])
            existing_ids: list[str] = []
            if isinstance(prev_ids, list):
                existing_ids = [str(value or "").strip() for value in prev_ids if str(value or "").strip()]
            new_ids = [str(value or "").strip() for value in (exported_material_ids or []) if str(value or "").strip()]
            merged_ids: list[str] = []
            seen: set[str] = set()
            for value in existing_ids + new_ids:
                if value in seen:
                    continue
                seen.add(value)
                merged_ids.append(value)
            if merged_ids:
                row["exported_material_ids"] = merged_ids
                row["exported_material_count"] = len(merged_ids)
            else:
                row.setdefault("exported_material_ids", [])
                row["exported_material_count"] = int(row.get("exported_material_count", 0) or 0)
            if imported_lines is not None:
                row["last_export_imported_lines"] = int(imported_lines or 0)
            if skipped_lines is not None:
                row["last_export_skipped_lines"] = int(skipped_lines or 0)
            changed = True
            break
        if changed:
            payload["invoices"] = rows
            self._write_payload(payload)

    def mark_telegram_sent(self, invoice_ids: list[str]) -> None:
        wanted = {str(item or "").strip() for item in invoice_ids if str(item or "").strip()}
        if not wanted:
            return
        payload = self._read_payload()
        rows = payload.get("invoices", [])
        if not isinstance(rows, list):
            return
        changed = False
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_id = str(row.get("invoice_id", "") or "").strip()
            if row_id in wanted and not bool(row.get("telegram_sent", False)):
                row["telegram_sent"] = True
                changed = True
        if changed:
            payload["invoices"] = rows
            self._write_payload(payload)

    def delete_invoice(self, invoice_id: str) -> bool:
        invoice_id_norm = str(invoice_id or "").strip()
        if not invoice_id_norm:
            return False

        payload = self._read_payload()
        rows = payload.get("invoices", [])
        if not isinstance(rows, list):
            return False

        kept_rows: list[dict[str, Any]] = []
        removed = False
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_id = str(row.get("invoice_id", "") or "").strip()
            if row_id == invoice_id_norm:
                removed = True
                continue
            kept_rows.append(row)

        if removed:
            payload["invoices"] = kept_rows
            self._write_payload(payload)
        return removed

    def list_unsent_telegram(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = []
        for row in self.list_invoices():
            if bool(row.get("telegram_sent", False)):
                continue
            rows.append(dict(row))
            if len(rows) >= max(1, int(limit or 10)):
                break
        return rows

    def count_pending_export(self) -> int:
        count = 0
        for row in self.list_invoices():
            if not bool(row.get("exported_to_material", False)):
                count += 1
        return count

    def _read_payload(self) -> dict[str, Any]:
        payload = read_json_file(self._path, default={"invoices": []}, expected_type=dict)
        if not isinstance(payload, dict):
            return {"invoices": []}
        if not isinstance(payload.get("invoices", []), list):
            payload["invoices"] = []
        return payload

    def _write_payload(self, payload: dict[str, Any]) -> None:
        write_json_atomic(self._path, payload, ensure_ascii=False, indent=2)

    @staticmethod
    def _norm_text(value: Any) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def _norm_invoice_number(value: Any) -> str:
        raw = str(value or "").strip().upper()
        if not raw:
            return ""
        return "".join(ch for ch in raw if ch.isalnum())

    @staticmethod
    def _norm_nip(value: Any) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    @staticmethod
    def _norm_date(value: Any) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        match = re.search(r"\d{4}-\d{2}-\d{2}", raw)
        if match:
            return match.group(0)
        return raw[:10]

    @staticmethod
    def _amount(value: Any) -> float:
        try:
            return round(float(value or 0.0), 2)
        except Exception:
            return 0.0

    @classmethod
    def _invoice_signature(cls, invoice: dict[str, Any]) -> dict[str, Any]:
        supplier = cls._norm_text(invoice.get("supplier", "") or invoice.get("sender", ""))
        invoice_no = cls._norm_invoice_number(invoice.get("invoice_number", ""))
        buyer_nip = cls._norm_nip(invoice.get("buyer_nip", ""))
        inv_date = cls._norm_date(invoice.get("invoice_date", ""))
        amount_due = cls._amount(invoice.get("amount_due", 0.0))
        total_gross = cls._amount(invoice.get("total_gross", 0.0))
        total_amount = cls._amount(invoice.get("total_amount", 0.0))
        currency = str(invoice.get("currency", "PLN") or "PLN").strip().upper() or "PLN"
        amount = amount_due if amount_due > 0 else (total_gross if total_gross > 0 else total_amount)
        return {
            "invoice_number": invoice_no,
            "supplier": supplier,
            "buyer_nip": buyer_nip,
            "invoice_date": inv_date,
            "amount": amount,
            "currency": currency,
        }

    @staticmethod
    def _is_same_invoice_signature(current: dict[str, Any], existing: dict[str, Any]) -> bool:
        current_no = str(current.get("invoice_number", "") or "").strip()
        existing_no = str(existing.get("invoice_number", "") or "").strip()
        same_number = bool(current_no and existing_no and current_no == existing_no)

        current_supplier = str(current.get("supplier", "") or "").strip()
        existing_supplier = str(existing.get("supplier", "") or "").strip()
        same_supplier = bool(current_supplier and existing_supplier and current_supplier == existing_supplier)

        current_nip = str(current.get("buyer_nip", "") or "").strip()
        existing_nip = str(existing.get("buyer_nip", "") or "").strip()
        same_nip = bool(current_nip and existing_nip and current_nip == existing_nip)

        current_date = str(current.get("invoice_date", "") or "").strip()
        existing_date = str(existing.get("invoice_date", "") or "").strip()
        same_date = bool(current_date and existing_date and current_date == existing_date)

        try:
            current_amount = float(current.get("amount", 0.0) or 0.0)
            existing_amount = float(existing.get("amount", 0.0) or 0.0)
        except Exception:
            current_amount = 0.0
            existing_amount = 0.0
        same_amount = (
            current_amount > 0
            and existing_amount > 0
            and abs(current_amount - existing_amount) < 0.01
            and str(current.get("currency", "PLN") or "PLN").strip().upper()
            == str(existing.get("currency", "PLN") or "PLN").strip().upper()
        )

        if same_number:
            # Primary dedupe path: same invoice number and at least one corroborating field.
            if same_supplier or same_nip or same_date or same_amount:
                return True

        # Secondary dedupe path for scans with unreadable invoice number.
        # Keep it strict to avoid false positives.
        if not same_number and same_supplier and same_date and same_amount:
            return True

        return False
