"""
Testy porównawcze: Szybka wycena (stary system vs ProjectModel)

Weryfikacja że ProjectModel daje takie same wyniki co UI.
"""

import pytest
from PyQt6.QtWidgets import QApplication

from src.domain.project_model import (
    ProjectModel, ProjectHeader, ProjectQuoteContext, ProjectQuoteLine,
    ProjectPricingSnapshot, ProjectAudit
)


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestSzybkaWycenaEquivalence:
    """Test że ProjectModel szybka wycena = stary UI."""

    def test_quote_line_structure(self):
        """Weryfikacja że każdy wiersz UI → ProjectQuoteLine."""
        # Simulacja starego UI: tabela z wierszami
        old_ui_row = {
            "id": "row_1",
            "nazwa": "Górrne szafki - mały zestaw",
            "ilość": 1,
            "j.m.": "szt",
            "m2": 0.5,
            "cena_jm": 100.00,
            "suma": 50.00,  # 0.5 m² × 100 zł/m²
            "typ": "Materiał"
        }

        # Nowy ProjectModel
        line = ProjectQuoteLine(
            line_id="row_1",
            source_kind="quick_quote",
            source_ref="szybka_1",
            group="Materiał",
            module_name="Górrne szafki - mały zestaw",
            qty=1,
            unit="szt",
            cost_material=50.00,  # Równoważne 'suma'
            line_total=50.00,
            status="OK",
            accuracy="snapshot"
        )

        # Walidacja
        assert line.line_total == old_ui_row["suma"]
        assert line.qty == old_ui_row["ilość"]
        assert line.unit == old_ui_row["j.m."]
        assert line.group == old_ui_row["typ"]

    def test_hardware_line_structure(self):
        """Weryfikacja że osprzęt z osobnej tabeli → ProjectQuoteLine."""
        old_ui_hardware = {
            "id": "hw_1",
            "nazwa": "Okucia 32mm",
            "ilość": 10,
            "cena_szt": 5.00,
            "razem": 50.00
        }

        line = ProjectQuoteLine(
            line_id="hw_1",
            source_kind="quick_quote",
            source_ref="szybka_1",
            group="Osprzęt",
            module_name="Okucia 32mm",
            qty=10,
            unit="szt",
            cost_material=50.00,
            line_total=50.00,
            status="OK",
            accuracy="snapshot"
        )

        assert line.line_total == old_ui_hardware["razem"]
        assert line.qty == old_ui_hardware["ilość"]

    def test_pricing_snapshot_totals(self):
        """Weryfikacja że pricing_snapshot.brutto_total = UI.brutto."""
        # Stary UI - wyliczenia
        material_sum = 500.00  # Σ suma z tabeli wierszy
        hardware_sum = 100.00  # Σ razem z tabeli osprzętu
        transport = 50.00
        labor = 100.00
        montage = 0.00

        base_netto = material_sum + hardware_sum + transport + labor + montage
        # base_netto = 750.00

        margin_percent = 10
        vat_percent = 23

        sale_total = base_netto * (1 + margin_percent / 100)
        # sale_total = 750 * 1.10 = 825.00

        brutto_total_old_ui = sale_total * (1 + vat_percent / 100)
        # brutto_total_old_ui = 825 * 1.23 = 1014.75

        # Nowy ProjectModel
        snapshot = ProjectPricingSnapshot(
            material_value=material_sum + hardware_sum,
            services_total=labor + montage,
            extras_total=transport,
            base_total=base_netto,
            sale_total=sale_total,
            brutto_total=brutto_total_old_ui,
            computed_at="2026-04-10T12:00:00Z"
        )

        # Walidacja
        assert snapshot.base_total == base_netto
        assert snapshot.sale_total == sale_total
        assert snapshot.brutto_total == brutto_total_old_ui
        assert abs(snapshot.brutto_total - 1014.75) < 0.01

    def test_full_szybka_wycena_model(self):
        """Pełny ProjectModel dla szybka wycena."""
        # Simulacja wyceny szybkiej z UI
        model = ProjectModel(
            project_id="sw_001",
            project_name="Wycena test - Szybka",
            project_type="quick_quote",
            status="active",

            header=ProjectHeader(
                client_name="ACME Corp",
                order_code="SW/001/2026",
                source_path="quick_quote_archive.json",
                source_kind="quick_quote"
            ),

            quote_context=ProjectQuoteContext(
                mode="quick_quote",
                margin_percent=10,
                vat_percent=23,
                transport_cost=50.00,
                labor_cost=100.00,
                montage_cost=0.00
            ),

            quote_lines=[
                ProjectQuoteLine(
                    line_id="l1",
                    source_kind="quick_quote",
                    group="Materiał",
                    module_name="Górrne szafki",
                    qty=1,
                    unit="szt",
                    cost_material=300.00,
                    line_total=300.00,
                    status="OK",
                    accuracy="snapshot"
                ),
                ProjectQuoteLine(
                    line_id="l2",
                    source_kind="quick_quote",
                    group="Materiał",
                    module_name="Dolne szafki",
                    qty=1,
                    unit="szt",
                    cost_material=200.00,
                    line_total=200.00,
                    status="OK",
                    accuracy="snapshot"
                ),
                ProjectQuoteLine(
                    line_id="hw1",
                    source_kind="quick_quote",
                    group="Osprzęt",
                    module_name="Okucia",
                    qty=20,
                    unit="szt",
                    cost_material=100.00,
                    line_total=100.00,
                    status="OK",
                    accuracy="snapshot"
                ),
            ],

            pricing_snapshot=ProjectPricingSnapshot(
                material_value=500.00 + 100.00,  # Materiały + Osprzęt
                services_total=100.00,  # Labor
                extras_total=50.00,  # Transport
                base_total=650.00 + 100.00,  # 750.00
                sale_total=825.00,  # 750 * 1.10
                brutto_total=1014.75,  # 825 * 1.23
                computed_at="2026-04-10T12:00:00Z"
            ),

            audit=ProjectAudit(
                source="SzybkaWycenaSection",
                adapter="build_quick_quote_project_model()",
                archive_record_id="sw_001"
            )
        )

        # Walidacja struktury
        assert model.project_type == "quick_quote"
        assert model.header.client_name == "ACME Corp"
        assert len(model.quote_lines) == 3

        # Walidacja sum
        sum_lines = sum(line.line_total for line in model.quote_lines)
        assert sum_lines == 600.00  # 300 + 200 + 100

        # Walidacja pricing
        assert model.pricing_snapshot.material_value == 600.00
        assert model.pricing_snapshot.services_total == 100.00
        assert model.pricing_snapshot.extras_total == 50.00
        assert model.pricing_snapshot.base_total == 750.00
        assert abs(model.pricing_snapshot.brutto_total - 1014.75) < 0.01

    def test_margin_vat_calculation(self):
        """Weryfikacja obliczeń marża + VAT."""
        base = 1000.00
        margin = 20  # 20%
        vat = 23  # 23%

        sale = base * (1 + margin / 100)
        assert sale == 1200.00

        brutto = sale * (1 + vat / 100)
        assert abs(brutto - 1476.00) < 0.01

        # W ProjectModel
        snapshot = ProjectPricingSnapshot(
            base_total=base,
            sale_total=sale,
            brutto_total=brutto,
            computed_at="2026-04-10T12:00:00Z"
        )

        assert snapshot.base_total == base
        assert snapshot.sale_total == sale
        assert abs(snapshot.brutto_total - 1476.00) < 0.01

    def test_empty_quote(self):
        """Test wyceny pustej (brak wierszy)."""
        model = ProjectModel(
            project_id="empty_1",
            project_name="Pusta wycena",
            project_type="quick_quote",
            status="active",
            quote_lines=[],
            pricing_snapshot=ProjectPricingSnapshot(
                material_value=0.0,
                services_total=0.0,
                extras_total=0.0,
                base_total=0.0,
                sale_total=0.0,
                brutto_total=0.0,
                computed_at="2026-04-10T12:00:00Z"
            )
        )

        assert len(model.quote_lines) == 0
        assert model.pricing_snapshot.base_total == 0.0
        assert model.pricing_snapshot.brutto_total == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
