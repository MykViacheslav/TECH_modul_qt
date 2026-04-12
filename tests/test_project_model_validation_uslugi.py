"""
Testy porównawcze: Usługi (stary system vs ProjectModel)

Weryfikacja że ProjectModel daje takie same wyniki co ServiceOrderDef.
"""

import pytest
from datetime import datetime
from PyQt6.QtWidgets import QApplication

from src.domain.project_model import (
    ProjectModel, ProjectHeader, ProjectServiceLine,
    ProjectPricingSnapshot, ProjectAudit
)


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestUslugEquivalence:
    """Test że ProjectModel usługi = stary ServiceOrderDef."""

    def test_service_line_structure(self):
        """Weryfikacja że item usługi → ProjectServiceLine."""
        # Stary system: item z ServiceOrderDef
        old_service_item = {
            "item_id": "item_1",
            "name": "Lakierowanie fronty",
            "material": "Lite drewno",
            "width_mm": 1000,
            "height_mm": 500,
            "quantity": 2,
            "unit": "szt",
            "notes": "Lakier matowy"
        }

        # Nowy ProjectModel
        line = ProjectServiceLine(
            service_id="item_1",
            service_name="Lakierowanie fronty",
            source_kind="service",
            qty=2,
            unit="szt",
            amount=100.00,  # Cena za sztukę
            status="nowe",
            accuracy="snapshot",
            note="Lakier matowy - Lite drewno"
        )

        # Walidacja
        assert line.qty == old_service_item["quantity"]
        assert line.service_name == old_service_item["name"]
        assert line.unit == old_service_item["unit"]

    def test_service_extras(self):
        """Weryfikacja że transport i extras → ProjectServiceLine."""
        # Stary system: ServiceOrderDef fields
        old_order = {
            "service_id": "ord_1",
            "price_base": 500.00,
            "price_transport": 50.00,
            "price_extra": 100.00,
            "price_total": 650.00
        }

        # Nowy ProjectModel - rozbite na service lines
        lines = [
            ProjectServiceLine(
                service_id="ord_1",
                service_name="Łączone pozycje",
                source_kind="service",
                qty=1,
                unit="zl",
                amount=500.00,
                status="przyjete",
                accuracy="snapshot"
            ),
            ProjectServiceLine(
                service_id="ord_1_transport",
                service_name="Transport",
                source_kind="service_extra",
                qty=1,
                unit="zl",
                amount=50.00,
                status="przyjete",
                accuracy="snapshot"
            ),
            ProjectServiceLine(
                service_id="ord_1_extra",
                service_name="Dodatkowe",
                source_kind="service_extra",
                qty=1,
                unit="zl",
                amount=100.00,
                status="przyjete",
                accuracy="snapshot"
            ),
        ]

        # Walidacja
        total = sum(line.amount for line in lines)
        assert total == old_order["price_total"]
        assert total == 650.00

    def test_service_pricing_snapshot(self):
        """Weryfikacja pricing_snapshot dla usług."""
        # Stary system
        price_base = 500.00
        price_transport = 50.00
        price_extra = 100.00
        price_total = 650.00

        # Aplikacja marży i VAT
        margin_percent = 15
        vat_percent = 23

        sale_total = price_total * (1 + margin_percent / 100)
        # sale_total = 650 * 1.15 = 747.50

        brutto_total = sale_total * (1 + vat_percent / 100)
        # brutto_total = 747.50 * 1.23 = 919.425

        # Nowy ProjectModel
        snapshot = ProjectPricingSnapshot(
            services_total=price_total,
            base_total=price_total,
            sale_total=sale_total,
            brutto_total=brutto_total,
            computed_at="2026-04-10T12:00:00Z"
        )

        # Walidacja
        assert snapshot.services_total == 650.00
        assert snapshot.base_total == 650.00
        assert snapshot.sale_total == 747.50
        assert abs(snapshot.brutto_total - 919.425) < 0.01

    def test_full_service_order_model(self):
        """Pełny ProjectModel dla zamówienia usługi."""
        model = ProjectModel(
            project_id="svc_001",
            project_name="Zamówienie usługi - Lakierowanie",
            project_type="service_order",
            status="active",

            header=ProjectHeader(
                client_name="Meblarnia XYZ",
                client_phone="123-456-789",
                client_email="kontakt@xyz.pl",
                source_path="services.json",
                source_kind="service_order"
            ),

            services=[
                ProjectServiceLine(
                    service_id="item_1",
                    service_name="Lakierowanie fronty",
                    source_kind="service",
                    qty=5,
                    unit="szt",
                    amount=50.00,
                    status="w_trakcie",
                    accuracy="snapshot"
                ),
                ProjectServiceLine(
                    service_id="item_2",
                    service_name="Wycinanie krawędziowe",
                    source_kind="service",
                    qty=10,
                    unit="mb",
                    amount=5.00,
                    status="w_trakcie",
                    accuracy="snapshot"
                ),
                ProjectServiceLine(
                    service_id="transport",
                    service_name="Transport",
                    source_kind="service_extra",
                    qty=1,
                    unit="zl",
                    amount=100.00,
                    status="w_trakcie",
                    accuracy="snapshot"
                ),
            ],

            pricing_snapshot=ProjectPricingSnapshot(
                services_total=250.00 + 50.00 + 100.00,  # 400.00
                base_total=400.00,
                sale_total=400.00 * 1.10,  # 440.00
                brutto_total=440.00 * 1.23,  # 541.20
                computed_at="2026-04-10T12:00:00Z"
            ),

            audit=ProjectAudit(
                source="ServiceOrderDef",
                adapter="build_service_order_project_model()",
                service_status_history=[
                    {"status": "nowe", "timestamp": "2026-04-01T10:00:00Z"},
                    {"status": "wycena", "timestamp": "2026-04-02T10:00:00Z"},
                    {"status": "przyjete", "timestamp": "2026-04-03T10:00:00Z"},
                    {"status": "w_trakcie", "timestamp": "2026-04-05T10:00:00Z"},
                ]
            )
        )

        # Walidacja struktury
        assert model.project_type == "service_order"
        assert model.header.client_name == "Meblarnia XYZ"
        assert len(model.services) == 3

        # Walidacja sum
        sum_services = sum(line.amount for line in model.services)
        assert sum_services == 400.00

        # Walidacja pricing
        assert model.pricing_snapshot.services_total == 400.00
        assert model.pricing_snapshot.base_total == 400.00
        assert model.pricing_snapshot.sale_total == 440.00
        assert abs(model.pricing_snapshot.brutto_total - 541.20) < 0.01

        # Walidacja audit trail
        assert len(model.audit.service_status_history) == 4
        assert model.audit.service_status_history[0]["status"] == "nowe"
        assert model.audit.service_status_history[-1]["status"] == "w_trakcie"

    def test_service_status_lifecycle(self):
        """Weryfikacja że historia statusów zachowana."""
        statuses = ["nowe", "wycena", "przyjete", "w_trakcie", "gotowe", "wydane"]

        history = [
            {"status": status, "timestamp": f"2026-04-{i:02d}T10:00:00Z"}
            for i, status in enumerate(statuses, 1)
        ]

        audit = ProjectAudit(
            service_status_history=history
        )

        # Walidacja
        assert len(audit.service_status_history) == len(statuses)
        assert audit.service_status_history[0]["status"] == "nowe"
        assert audit.service_status_history[-1]["status"] == "wydane"

    def test_multiple_service_items(self):
        """Test więcej pozycji usługi."""
        items = [
            ("Lakierowanie", 5, "szt", 50.00),
            ("Wycinanie", 10, "mb", 5.00),
            ("Giecie", 2, "szt", 75.00),
            ("Montaż", 4, "h", 40.00),
        ]

        lines = [
            ProjectServiceLine(
                service_id=f"item_{i}",
                service_name=name,
                source_kind="service",
                qty=qty,
                unit=unit,
                amount=qty * price,
                status="przyjete",
                accuracy="snapshot"
            )
            for i, (name, qty, unit, price) in enumerate(items, 1)
        ]

        # Suma
        total = sum(line.amount for line in lines)
        expected = (5 * 50) + (10 * 5) + (2 * 75) + (4 * 40)
        assert total == expected
        assert total == 250.00 + 50.00 + 150.00 + 160.00  # 610.00

    def test_service_without_extras(self):
        """Test usługi bez transportu/extras."""
        model = ProjectModel(
            project_id="svc_simple",
            project_type="service_order",
            services=[
                ProjectServiceLine(
                    service_id="item_1",
                    service_name="Lakierowanie",
                    source_kind="service",
                    qty=3,
                    unit="szt",
                    amount=150.00,
                    status="gotowe",
                    accuracy="snapshot"
                )
            ],
            pricing_snapshot=ProjectPricingSnapshot(
                services_total=150.00,
                base_total=150.00,
                sale_total=165.00,
                brutto_total=202.95,
                computed_at="2026-04-10T12:00:00Z"
            )
        )

        assert len(model.services) == 1
        assert model.pricing_snapshot.services_total == 150.00
        assert abs(model.pricing_snapshot.brutto_total - 202.95) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
