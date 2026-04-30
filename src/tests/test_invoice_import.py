import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

import json
import unittest
from datetime import datetime
from src.storage.invoice_store_json import InvoiceStoreJson
from src.storage.material_store_json import MaterialStoreJson
from src.services.invoice_workflow_service import (
    _build_invoice_payload,
    export_invoice_to_material_store,
)
from src.services.invoice_pdf_import_service import InvoiceParseResult, InvoiceLineItem

class TestInvoiceImport(unittest.TestCase):
    def setUp(self):
        # Use temporary storage for testing
        self.invoice_path = root_dir / "src" / "tests" / "temp_invoices.json"
        self.material_path = root_dir / "src" / "tests" / "temp_baza_materialu.json"
        
        # Cleanup
        if self.invoice_path.exists(): self.invoice_path.unlink()
        if self.material_path.exists(): self.material_path.unlink()
        
        self.invoice_store = InvoiceStoreJson(self.invoice_path)
        self.material_store = MaterialStoreJson(self.material_path)
        
    def tearDown(self):
        # Cleanup
        if self.invoice_path.exists(): self.invoice_path.unlink()
        if self.material_path.exists(): self.material_path.unlink()

    def test_invoice_payload_building_and_vat(self):
        """Verify VAT and payload generation."""
        items = [
            InvoiceLineItem(
                name="Plyta EGGER W1000",
                quantity=2.0,
                unit="szt",
                unit_price=100.0,
                total_price=200.0,
                material_type="plyta",
                thickness_mm="18",
                raw_line="Plyta EGGER W1000 2 szt 100.00 200.00",
                unit_price_net=100.0,
                total_price_net=200.0,
                vat_rate="23",
                total_price_gross=246.0,
            )
        ]
        parsed = InvoiceParseResult(
            source_path=Path("test.pdf"),
            invoice_number="FV/2026/001",
            invoice_date="2026-04-14",
            supplier="Hurtownia Drewna",
            text_length=1000,
            items=tuple(items),
            total_net=200.0,
            total_gross=246.0,
            total_vat=46.0,
            currency="PLN"
        )
        
        payload = _build_invoice_payload(
            parsed=parsed,
            source="test",
            source_path="test.pdf",
            attachment_name="test.pdf",
            attachment_key="test_key",
            payload_hash="hash123"
        )
        
        self.assertEqual(payload["invoice_number"], "FV/2026/001")
        self.assertEqual(payload["total_net"], 200.0)
        self.assertEqual(payload["total_vat"], 46.0)
        self.assertEqual(payload["total_gross"], 246.0)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["name"], "Plyta EGGER W1000")

    def test_duplicate_detection(self):
        """Verify that same invoice is not added twice."""
        invoice_data = {
            "invoice_number": "FV/999",
            "invoice_date": "2026-01-01",
            "supplier": "Test Supplier",
            "total_gross": 1000.0,
            "amount_due": 1000.0,
            "payload_hash": "fixed_hash"
        }
        
        is_new1, rec1 = self.invoice_store.upsert_invoice(invoice_data)
        self.assertTrue(is_new1)
        
        # Try same data again
        is_new2, rec2 = self.invoice_store.upsert_invoice(invoice_data)
        self.assertFalse(is_new2) # Should be false as it is a duplicate
        self.assertEqual(rec1["invoice_id"], rec2["invoice_id"])

    def test_material_export(self):
        """Verify that items from invoice are correctly added to material database."""
        invoice_data = {
            "invoice_number": "FV/MATERIAL/01",
            "supplier": "Stolarz Bis",
            "purchase_channel": "paragon",
            "items": [
                {
                    "name": "Zawias Blum 71B3550",
                    "quantity": 10.0,
                    "unit": "szt",
                    "unit_price_net": 10.0,
                    "unit_price_gross": 12.3,
                    "total_price_gross": 123.0,
                    "material_type": "okucie"
                }
            ]
        }
        
        _, stored = self.invoice_store.upsert_invoice(invoice_data)
        invoice_id = stored["invoice_id"]
        
        summary = export_invoice_to_material_store(
            invoice_id,
            invoice_store=self.invoice_store,
            material_store=self.material_store
        )
        
        self.assertEqual(summary.imported_lines, 1)
        
        # Verify database
        mat_data = self.material_store.load()
        rows = mat_data.get("rows", [])
        self.assertEqual(len(rows), 1)
        item = rows[0]
        self.assertEqual(item["nazwa"], "Zawias Blum 71B3550")
        self.assertEqual(item["producent"], "Stolarz Bis")
        # Check channel label in 'zakup' field
        self.assertIn("Paragon", item["zakup"])
        self.assertEqual(item["numer_faktury"], "FV/MATERIAL/01")
        self.assertEqual(item["magazyn_typ"], "okucia_akcesoria")

if __name__ == "__main__":
    unittest.main()
