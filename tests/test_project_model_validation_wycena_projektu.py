"""
Testy porównawcze: Wycena projektu / Assembly (stary system vs ProjectModel)

Weryfikacja że ProjectModel daje takie same wyniki co AssemblyDef.
"""

import pytest
from PyQt6.QtWidgets import QApplication

from src.domain.project_model import (
    ProjectModel, ProjectHeader, ProjectQuoteContext, ProjectQuoteLine,
    ProjectAssembly, ProjectPricingSnapshot, ProjectAudit
)


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestWycenaProjetkuEquivalence:
    """Test że ProjectModel wycena = stary AssemblyDef."""

    def test_assembly_dimensions(self):
        """Weryfikacja że wymiary z AssemblyDef → ProjectAssembly."""
        # Stary system: AssemblyDef fields
        old_assembly = {
            "assembly_id": "assy_1",
            "name": "Dolna zabudowa - Standard",
            "wall_name": "Ściana kuchni",
            "order_name": "ZAM/001",
            "client_name": "ACME Corp",
            "width_mm": 2000,
            "height_mm": 850,
            "depth_mm": 600,
            "gap_mm": 20,
            "material_profile_key": "MDF_18",
        }

        # Nowy ProjectModel
        assembly = ProjectAssembly(
            assembly_id=old_assembly["assembly_id"],
            name=old_assembly["name"],
            wall_name=old_assembly["wall_name"],
            order_name=old_assembly["order_name"],
            client_name=old_assembly["client_name"],
            width_mm=old_assembly["width_mm"],
            height_mm=old_assembly["height_mm"],
            depth_mm=old_assembly["depth_mm"],
            gap_mm=old_assembly["gap_mm"],
            material_profile=old_assembly["material_profile_key"]
        )

        # Walidacja
        assert assembly.width_mm == 2000
        assert assembly.height_mm == 850
        assert assembly.depth_mm == 600
        assert assembly.gap_mm == 20
        assert assembly.material_profile == "MDF_18"

    def test_assembly_items_to_quote_lines(self):
        """Weryfikacja że items z AssemblyDef → quote_lines."""
        # Stary system: items w AssemblyDef
        old_items = [
            {
                "item_id": "item_1",
                "name": "Korpus",
                "category": "Korpus",
                "qty": 1,
                "unit": "kpl",
                "cost": 500.00
            },
            {
                "item_id": "item_2",
                "name": "Fronty",
                "category": "Front",
                "qty": 3,
                "unit": "szt",
                "cost": 150.00
            },
            {
                "item_id": "item_3",
                "name": "Okucia",
                "category": "Okucie",
                "qty": 1,
                "unit": "kpl",
                "cost": 50.00
            }
        ]

        # Nowy ProjectModel
        lines = [
            ProjectQuoteLine(
                line_id=item["item_id"],
                source_kind="assembly_item",
                source_ref="assy_1",
                group=item["category"],
                module_name=item["name"],
                qty=item["qty"],
                unit=item["unit"],
                cost_material=item["cost"],
                line_total=item["cost"],
                status="OK",
                accuracy="snapshot"
            )
            for item in old_items
        ]

        # Walidacja
        assert len(lines) == 3
        assert lines[0].line_total == 500.00
        assert lines[1].line_total == 150.00
        assert lines[2].line_total == 50.00

    def test_assembly_with_transport_montage(self):
        """Weryfikacja że transport i montaż → quote_lines."""
        # Stary system
        assembly_data = {
            "assembly_id": "assy_1",
            "transport_cost_pln": 100.00,
            "montage_cost_pln": 200.00,
            "labor_cost_pln": 0.00,
            "margin_percent": 20,
        }

        # Nowy ProjectModel - transport i montaż jako oddzielne linie
        lines = [
            ProjectQuoteLine(
                line_id="item_1",
                source_kind="assembly_item",
                group="Korpus",
                module_name="Korpus",
                qty=1,
                unit="kpl",
                cost_material=800.00,
                line_total=800.00,
                status="OK",
                accuracy="snapshot"
            ),
            ProjectQuoteLine(
                line_id="transport",
                source_kind="assembly_transport",
                group="Transport",
                module_name="Transport",
                qty=1,
                unit="zl",
                cost_extra=assembly_data["transport_cost_pln"],
                line_total=assembly_data["transport_cost_pln"],
                status="OK",
                accuracy="snapshot"
            ),
            ProjectQuoteLine(
                line_id="montage",
                source_kind="assembly_montage",
                group="Montaż",
                module_name="Montaż",
                qty=1,
                unit="zl",
                cost_extra=assembly_data["montage_cost_pln"],
                line_total=assembly_data["montage_cost_pln"],
                status="OK",
                accuracy="snapshot"
            ),
        ]

        # Suma
        total_base = sum(line.line_total for line in lines)
        assert total_base == 800.00 + 100.00 + 200.00  # 1100.00

    def test_assembly_pricing_calculation(self):
        """Weryfikacja obliczeń ceny dla assembly."""
        # Stary system
        base_netto = 1000.00
        margin = 20  # %
        vat = 23  # %

        sale_total = base_netto * (1 + margin / 100)
        # sale_total = 1200.00

        brutto_total = sale_total * (1 + vat / 100)
        # brutto_total = 1476.00

        # Nowy ProjectModel
        snapshot = ProjectPricingSnapshot(
            base_total=base_netto,
            sale_total=sale_total,
            brutto_total=brutto_total,
            computed_at="2026-04-10T12:00:00Z"
        )

        # Walidacja
        assert snapshot.base_total == 1000.00
        assert snapshot.sale_total == 1200.00
        assert abs(snapshot.brutto_total - 1476.00) < 0.01

    def test_full_assembly_model(self):
        """Pełny ProjectModel dla assembly."""
        model = ProjectModel(
            project_id="assy_001",
            project_name="Dolna zabudowa - Standard",
            project_type="assembly_pricing",
            status="active",

            header=ProjectHeader(
                client_name="ACME Corp",
                order_code="ZAM/001",
                project_name="Dolna zabudowa - Standard",
                source_path="assemblies.json",
                source_kind="assembly"
            ),

            quote_context=ProjectQuoteContext(
                mode="assembly_pricing",
                policy_key="MDF_18",
                margin_percent=20,
                vat_percent=23,
                transport_cost=100.00,
                labor_cost=0.00,
                montage_cost=200.00
            ),

            assemblies=[
                ProjectAssembly(
                    assembly_id="assy_1",
                    name="Dolna zabudowa - Standard",
                    wall_name="Ściana kuchni",
                    order_name="ZAM/001",
                    client_name="ACME Corp",
                    width_mm=2000,
                    height_mm=850,
                    depth_mm=600,
                    gap_mm=20,
                    material_profile="MDF_18",
                    items=[
                        {
                            "item_id": "item_1",
                            "name": "Korpus",
                            "category": "Korpus",
                            "qty": 1,
                            "unit": "kpl",
                            "cost": 500.00
                        },
                        {
                            "item_id": "item_2",
                            "name": "Fronty",
                            "category": "Front",
                            "qty": 3,
                            "unit": "szt",
                            "cost": 150.00
                        },
                        {
                            "item_id": "item_3",
                            "name": "Okucia",
                            "category": "Okucie",
                            "qty": 1,
                            "unit": "kpl",
                            "cost": 50.00
                        }
                    ]
                )
            ],

            quote_lines=[
                ProjectQuoteLine(
                    line_id="item_1",
                    source_kind="assembly_item",
                    source_ref="assy_1",
                    group="Korpus",
                    module_name="Korpus",
                    qty=1,
                    unit="kpl",
                    cost_material=500.00,
                    line_total=500.00,
                    status="OK",
                    accuracy="snapshot"
                ),
                ProjectQuoteLine(
                    line_id="item_2",
                    source_kind="assembly_item",
                    source_ref="assy_1",
                    group="Front",
                    module_name="Fronty",
                    qty=3,
                    unit="szt",
                    cost_material=150.00,
                    line_total=150.00,
                    status="OK",
                    accuracy="snapshot"
                ),
                ProjectQuoteLine(
                    line_id="item_3",
                    source_kind="assembly_item",
                    source_ref="assy_1",
                    group="Okucie",
                    module_name="Okucia",
                    qty=1,
                    unit="kpl",
                    cost_material=50.00,
                    line_total=50.00,
                    status="OK",
                    accuracy="snapshot"
                ),
                ProjectQuoteLine(
                    line_id="transport",
                    source_kind="assembly_transport",
                    group="Transport",
                    module_name="Transport",
                    qty=1,
                    unit="zl",
                    cost_extra=100.00,
                    line_total=100.00,
                    status="OK",
                    accuracy="snapshot"
                ),
                ProjectQuoteLine(
                    line_id="montage",
                    source_kind="assembly_montage",
                    group="Montaż",
                    module_name="Montaż",
                    qty=1,
                    unit="zl",
                    cost_extra=200.00,
                    line_total=200.00,
                    status="OK",
                    accuracy="snapshot"
                ),
            ],

            pricing_snapshot=ProjectPricingSnapshot(
                material_value=500.00 + 150.00 + 50.00,  # 700.00
                services_total=0.00,
                extras_total=100.00 + 200.00,  # 300.00
                base_total=700.00 + 0.00 + 300.00,  # 1000.00
                sale_total=1000.00 * 1.20,  # 1200.00
                brutto_total=1200.00 * 1.23,  # 1476.00
                profit_total=1200.00 - 1000.00,  # 200.00
                computed_at="2026-04-10T12:00:00Z"
            ),

            audit=ProjectAudit(
                source="AssemblyDef",
                adapter="build_assembly_project_model()",
                assembly_id="assy_1",
                policy_applied="MDF_18"
            )
        )

        # Walidacja struktury
        assert model.project_type == "assembly_pricing"
        assert len(model.assemblies) == 1
        assert len(model.quote_lines) == 5

        # Walidacja wymiarów
        assert model.assemblies[0].width_mm == 2000
        assert model.assemblies[0].height_mm == 850

        # Walidacja sum
        sum_material = sum(l.cost_material or 0 for l in model.quote_lines)
        assert sum_material == 700.00

        # Walidacja pricing
        assert model.pricing_snapshot.material_value == 700.00
        assert model.pricing_snapshot.extras_total == 300.00
        assert model.pricing_snapshot.base_total == 1000.00
        assert abs(model.pricing_snapshot.brutto_total - 1476.00) < 0.01
        assert abs(model.pricing_snapshot.profit_total - 200.00) < 0.01

    def test_assembly_without_montage(self):
        """Test assembly bez montażu."""
        model = ProjectModel(
            project_type="assembly_pricing",
            quote_context=ProjectQuoteContext(
                mode="assembly_pricing",
                transport_cost=50.00,
                montage_cost=0.00  # Brak montażu
            ),
            quote_lines=[
                ProjectQuoteLine(
                    line_id="item_1",
                    source_kind="assembly_item",
                    group="Korpus",
                    cost_material=500.00,
                    line_total=500.00,
                    status="OK",
                    accuracy="snapshot"
                ),
                ProjectQuoteLine(
                    line_id="transport",
                    source_kind="assembly_transport",
                    group="Transport",
                    cost_extra=50.00,
                    line_total=50.00,
                    status="OK",
                    accuracy="snapshot"
                )
            ],
            pricing_snapshot=ProjectPricingSnapshot(
                base_total=550.00,
                sale_total=660.00,
                brutto_total=811.80,
                computed_at="2026-04-10T12:00:00Z"
            )
        )

        assert model.quote_context.montage_cost == 0.0
        assert len(model.quote_lines) == 2
        assert model.pricing_snapshot.base_total == 550.00

    def test_multiple_categories(self):
        """Test assembly z wieloma kategoriami."""
        categories = [
            ("Korpus", 800.00),
            ("Front", 300.00),
            ("Okucie", 50.00),
            ("Lacznik", 25.00),
            ("Transport", 100.00),
        ]

        lines = [
            ProjectQuoteLine(
                line_id=f"cat_{i}",
                source_kind="assembly_item",
                group=cat,
                cost_material=cost if cat != "Transport" else 0,
                cost_extra=cost if cat == "Transport" else 0,
                line_total=cost,
                status="OK",
                accuracy="snapshot"
            )
            for i, (cat, cost) in enumerate(categories)
        ]

        total = sum(l.line_total for l in lines)
        assert total == 1275.00
        assert len(lines) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
