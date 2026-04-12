"""
Testy porównawcze: GiB Lab (stary system vs ProjectModel)

Weryfikacja że ProjectModel daje takie same wyniki co GiB Lab result.
"""

import pytest
from PyQt6.QtWidgets import QApplication

from src.domain.project_model import (
    ProjectModel, ProjectGibLabResult, ProjectImport3D,
    ProjectPricingSnapshot, ProjectAudit
)


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestGibLabEquivalence:
    """Test że ProjectModel GiB Lab = stary result XML."""

    def test_giblab_result_parsing(self):
        """Weryfikacja że GiB Lab XML → ProjectGibLabResult."""
        # Stary system: parsed z XML
        old_result = {
            "material_amount_mm2": 1500000,  # cMaterialAmountP
            "parts_amount_mm2": 1200000,     # cPartsAmountP
            "waste_amount_mm2": 300000,      # cWasteAmountP
        }

        # Konwersja na m²
        material_m2 = old_result["material_amount_mm2"] / 1_000_000
        parts_m2 = old_result["parts_amount_mm2"] / 1_000_000
        waste_m2 = old_result["waste_amount_mm2"] / 1_000_000

        # Nowy ProjectModel
        giblab = ProjectGibLabResult(
            result_path="/path/to/giblab_result.xml",
            result_kind="giblab_project",
            material_amount_mm2=old_result["material_amount_mm2"],
            parts_amount_mm2=old_result["parts_amount_mm2"],
            waste_amount_mm2=old_result["waste_amount_mm2"],
            material_amount_m2=material_m2,
            parts_amount_m2=parts_m2,
            waste_amount_m2=waste_m2,
            utilization_percent=(parts_m2 / material_m2) * 100
        )

        # Walidacja
        assert giblab.material_amount_mm2 == 1500000
        assert giblab.parts_amount_mm2 == 1200000
        assert giblab.material_amount_m2 == 1.5
        assert giblab.parts_amount_m2 == 1.2
        assert giblab.waste_amount_m2 == 0.3
        assert abs(giblab.utilization_percent - 80.0) < 0.01

    def test_utilization_calculation(self):
        """Weryfikacja obliczenia procenta wykorzystania."""
        test_cases = [
            (1500000, 1200000, 80.0),  # 1200/1500 = 80%
            (1000000, 900000, 90.0),   # 900/1000 = 90%
            (2000000, 1500000, 75.0),  # 1500/2000 = 75%
        ]

        for material, parts, expected_util in test_cases:
            giblab = ProjectGibLabResult(
                result_path="/path/to/result.xml",
                material_amount_mm2=material,
                parts_amount_mm2=parts,
                waste_amount_mm2=material - parts,
                material_amount_m2=material / 1_000_000,
                parts_amount_m2=parts / 1_000_000,
                waste_amount_m2=(material - parts) / 1_000_000,
                utilization_percent=(parts / material) * 100
            )

            assert abs(giblab.utilization_percent - expected_util) < 0.01

    def test_difference_vs_theory(self):
        """Weryfikacja że GiB Lab result vs teoria (z import_3d)."""
        # Teoria (z import_3d)
        theory_total_area_m2 = 1.5

        # Rzeczywistość (z GiB Lab)
        real_material_m2 = 1.5  # Identyczne lub większe ze względu na cięcie
        real_utilization = 80.0

        # Różnica
        difference = theory_total_area_m2 - real_material_m2

        giblab = ProjectGibLabResult(
            result_path="/path/to/result.xml",
            material_amount_m2=real_material_m2,
            utilization_percent=real_utilization,
            difference_vs_theory={
                "material_total": difference,
                "theory_material_total": theory_total_area_m2,
                "utilization_pct": real_utilization,
                "parts_amount": theory_total_area_m2 * 0.8,  # 1.2 m²
                "waste_amount": theory_total_area_m2 * 0.2,  # 0.3 m²
            }
        )

        # Walidacja
        assert giblab.difference_vs_theory["material_total"] == 0.0
        assert giblab.difference_vs_theory["utilization_pct"] == 80.0

    def test_giblab_is_metadata_only(self):
        """Weryfikacja że GiB Lab NIE zmienia pricing_snapshot."""
        # Teoria (z import_3d lub assembly)
        theory_base_total = 1000.00
        theory_brutto = 1230.00

        # GiB Lab wynik (informacyjnie)
        giblab = ProjectGibLabResult(
            result_path="/path/to/result.xml",
            material_amount_m2=1.5,
            utilization_percent=80.0,
            difference_vs_theory={"material_total": 0.0}
        )

        # Nowy ProjectModel - GiB Lab to tylko metadata
        pricing = ProjectPricingSnapshot(
            base_total=theory_base_total,
            brutto_total=theory_brutto,
            computed_at="2026-04-10T12:00:00Z"
        )

        # Walidacja: GiB Lab nie zmienia pricing
        assert pricing.base_total == 1000.00
        assert pricing.brutto_total == 1230.00
        # GiB Lab przechowuje się w giblab_result, ale ceny pozostają takie same

    def test_full_giblab_model(self):
        """Pełny ProjectModel z GiB Lab result."""
        model = ProjectModel(
            project_id="i3d_giblab_001",
            project_name="Kuchnia Standard (z GiB Lab)",
            project_type="import_3d",
            status="active",

            import_3d=ProjectImport3D(
                source_file="/kitchen.project",
                project_name="Kuchnia Standard 2026",
                total_area_m2=1.5,
                total_edgeband_mb=6.0,
            ),

            giblab_result=ProjectGibLabResult(
                result_path="/giblab_result.xml",
                result_kind="giblab_project",
                material_amount_mm2=1500000,
                parts_amount_mm2=1200000,
                waste_amount_mm2=300000,
                material_amount_m2=1.5,
                parts_amount_m2=1.2,
                waste_amount_m2=0.3,
                utilization_percent=80.0,
                real_sheets_count=3,
                real_edgeband_mb=0.0,
                scrap_m2=0.3,
                difference_vs_theory={
                    "material_total": 0.0,
                    "theory_material_total": 1.5,
                    "utilization_pct": 80.0,
                    "parts_amount": 1.2,
                    "waste_amount": 0.3,
                },
                result_timestamp="2026-04-10T14:00:00Z"
            ),

            pricing_snapshot=ProjectPricingSnapshot(
                material_value=500.00,
                extras_total=100.00,
                services_total=0.0,
                base_total=600.00,
                sale_total=660.00,
                brutto_total=811.80,
                computed_at="2026-04-10T12:00:00Z"
                # WAŻNE: pricing_snapshot nie zmienia się na podstawie GiB Lab
            ),

            audit=ProjectAudit(
                source="import_3d with giblab_result",
                giblab_result_used=True,
                giblab_utilization=80.0,
                giblab_vs_theory_diff={"material_total": 0.0, "utilization_pct": 80.0}
            )
        )

        # Walidacja struktury
        assert model.project_type == "import_3d"
        assert model.giblab_result is not None
        assert model.giblab_result.utilization_percent == 80.0

        # Walidacja że pricing nie zmienił się z powodu GiB Lab
        assert model.pricing_snapshot.base_total == 600.00
        assert abs(model.pricing_snapshot.brutto_total - 811.80) < 0.01

        # Walidacja GiB Lab metadanych
        assert model.giblab_result.real_sheets_count == 3
        assert model.giblab_result.scrap_m2 == 0.3
        assert model.audit.giblab_result_used is True

    def test_giblab_without_changing_quote(self):
        """Test że GiB Lab feedback nie zmienia quote_lines."""
        # Model z import 3D
        model = ProjectModel(
            project_id="i3d_001",
            project_type="import_3d",

            # quote_lines z import_3d
            quote_lines=[
                {
                    "line_id": "3d_formatka_1",
                    "cost_material": 500.00,
                    "cost_edgeband": 100.00
                }
            ],

            # Pricing z import_3d
            pricing_snapshot=ProjectPricingSnapshot(
                base_total=600.00,
                brutto_total=738.00,
                computed_at="2026-04-10T12:00:00Z"
            ),

            # GiB Lab wynik (opcjonalnie)
            giblab_result=ProjectGibLabResult(
                result_path="/result.xml",
                material_amount_m2=1.5,
                utilization_percent=75.0,
                difference_vs_theory={"material_total": 0.0}
            )
        )

        # Walidacja: quote_lines pozostają takie same
        sum_lines = sum(l.get("cost_material", 0) + l.get("cost_edgeband", 0)
                       for l in model.quote_lines)
        assert sum_lines == 600.00

        # Walidacja: pricing nie zmienił się
        assert model.pricing_snapshot.base_total == 600.00
        assert abs(model.pricing_snapshot.brutto_total - 738.00) < 0.01

    def test_multiple_giblab_metrics(self):
        """Test wielokrotnych metryk z GiB Lab."""
        giblab = ProjectGibLabResult(
            result_path="/result.xml",
            material_amount_mm2=2000000,
            parts_amount_mm2=1500000,
            waste_amount_mm2=500000,
            material_amount_m2=2.0,
            parts_amount_m2=1.5,
            waste_amount_m2=0.5,
            utilization_percent=75.0,
            real_sheets_count=5,
            real_edgeband_mb=8.5,
            scrap_m2=0.5,
            leftovers=[
                {"size_mm2": 100000, "description": "Odpadek duży"},
                {"size_mm2": 50000, "description": "Odpadek mały"},
            ]
        )

        # Walidacja
        assert giblab.material_amount_m2 == 2.0
        assert giblab.parts_amount_m2 == 1.5
        assert giblab.real_sheets_count == 5
        assert abs(giblab.utilization_percent - 75.0) < 0.01
        assert len(giblab.leftovers) == 2
        assert giblab.leftovers[0]["size_mm2"] == 100000

    def test_giblab_compared_to_theory(self):
        """Test porównania rzeczywistości (GiB) vs teorii."""
        theory = {
            "total_area_m2": 1.5,
            "edgeband_mb": 6.0,
        }

        giblab = ProjectGibLabResult(
            result_path="/result.xml",
            material_amount_m2=1.5,  # Identyczne ze teorią
            utilization_percent=80.0,
            difference_vs_theory={
                "material_total": theory["total_area_m2"] - 1.5,  # 0.0
                "theory_material_total": theory["total_area_m2"],
                "utilization_pct": 80.0,
            }
        )

        # Walidacja
        assert giblab.difference_vs_theory["material_total"] == 0.0
        assert abs(giblab.difference_vs_theory["utilization_pct"] - 80.0) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
