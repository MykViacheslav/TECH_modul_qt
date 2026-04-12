"""
Smoke test: Walidacja że ProjectModel klasy instancjują się poprawnie
"""

import pytest
from datetime import datetime
from PyQt6.QtWidgets import QApplication

from src.domain.project_model import (
    ProjectModel, ProjectHeader, ProjectQuoteContext, ProjectQuoteLine,
    ProjectAssembly, ProjectServiceLine, ProjectImport3D, ProjectMapping,
    ProjectGibLabResult, ProjectPricingSnapshot, ProjectAudit
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class TestProjectModelStructure:
    """Smoke test - sprawdzenie czy klasy się instancjują i mają poprawne pola."""

    def test_project_header_instantiation(self):
        """Weryfikacja ProjectHeader."""
        header = ProjectHeader(
            project_name="Test",
            client_name="ACME",
            order_code="001",
            source_kind="quick_quote",
            source_path="/path.json"
        )
        assert header.project_name == "Test"
        assert header.client_name == "ACME"
        assert header.order_code == "001"

    def test_quote_context_instantiation(self):
        """Weryfikacja ProjectQuoteContext."""
        ctx = ProjectQuoteContext(
            mode="quick_quote",
            margin_percent=10.0,
            vat_percent=23.0,
            transport_flat=50.0,
            montage_flat=0.0,
            labor_cost=100.0
        )
        assert ctx.margin_percent == 10.0
        assert ctx.vat_percent == 23.0
        assert ctx.transport_flat == 50.0

    def test_quote_line_instantiation(self):
        """Weryfikacja ProjectQuoteLine."""
        line = ProjectQuoteLine(
            line_id="l1",
            source_kind="quick_quote",
            group="Materiał",
            module_name="Szafka",
            qty=1.0,
            unit="szt",
            cost_material=100.0,
            cost_labor=50.0,
            cost_extra=10.0,
            line_total=160.0,
            status="OK",
            accuracy="snapshot"
        )
        assert line.line_total == 160.0
        assert line.accuracy == "snapshot"

    def test_service_line_instantiation(self):
        """Weryfikacja ProjectServiceLine."""
        svc = ProjectServiceLine(
            service_id="svc_1",
            service_name="Lakierowanie",
            source_kind="service",
            qty=2.0,
            unit="szt",
            amount=100.0,
            status="przyjete"
        )
        assert svc.service_name == "Lakierowanie"
        assert svc.amount == 100.0
        assert svc.qty == 2.0

    def test_assembly_instantiation(self):
        """Weryfikacja ProjectAssembly."""
        assy = ProjectAssembly(
            assembly_id="assy_1",
            name="Zabudowa",
            width_mm=2000.0,
            height_mm=850.0,
            depth_mm=600.0,
            gap_mm=20.0,
            material_profile_key="MDF_18",
            transport_cost_pln=100.0,
            montage_cost_pln=200.0,
            margin_percent=20.0
        )
        assert assy.width_mm == 2000.0
        assert assy.material_profile_key == "MDF_18"
        assert assy.transport_cost_pln == 100.0

    def test_import_3d_instantiation(self):
        """Weryfikacja ProjectImport3D."""
        imp3d = ProjectImport3D(
            project_path="/path.project",
            project_name="Kuchnia",
            project_date="2026-03-15",
            project_version="1.0",
            module_name="Main",
            module_length_mm=3000.0,
            module_width_mm=600.0,
            module_height_mm=1000.0,
            total_area_m2=1.5,
            total_edgeband_mb=6.0,
            import_status="OK"
        )
        assert imp3d.project_name == "Kuchnia"
        assert imp3d.total_area_m2 == 1.5
        assert imp3d.total_edgeband_mb == 6.0

    def test_mapping_instantiation(self):
        """Weryfikacja ProjectMapping."""
        mapping = ProjectMapping(
            material_map={"MDF 18": "MDF_18_katalog"},
            edgeband_map={"buk": "buk_1mm"},
            mapping_status="OK"
        )
        assert mapping.material_map["MDF 18"] == "MDF_18_katalog"
        assert mapping.mapping_status == "OK"

    def test_giblab_result_instantiation(self):
        """Weryfikacja ProjectGibLabResult."""
        giblab = ProjectGibLabResult(
            result_path="/result.xml",
            result_kind="giblab_project",
            real_area_m2=1.5,
            real_sheets_count=3,
            scrap_m2=0.3,
            difference_vs_theory={"material_total": 0.0, "utilization_pct": 80.0}
        )
        assert giblab.real_area_m2 == 1.5
        assert giblab.real_sheets_count == 3
        assert giblab.difference_vs_theory["utilization_pct"] == 80.0

    def test_pricing_snapshot_instantiation(self):
        """Weryfikacja ProjectPricingSnapshot."""
        snapshot = ProjectPricingSnapshot(
            material_value=500.0,
            services_total=100.0,
            extras_total=50.0,
            base_total=650.0,
            sale_total=715.0,
            brutto_total=878.45,
            profit_total=65.0,
            computed_at="2026-04-10T12:00:00Z"
        )
        assert snapshot.material_value == 500.0
        assert snapshot.base_total == 650.0
        assert abs(snapshot.brutto_total - 878.45) < 0.01

    def test_audit_instantiation(self):
        """Weryfikacja ProjectAudit."""
        audit = ProjectAudit(
            built_from=["SzybkaWycenaSection"],
            adapter_name="build_quick_quote_project_model()",
            notes="Test audit"
        )
        assert len(audit.built_from) == 1
        assert audit.adapter_name == "build_quick_quote_project_model()"

    def test_full_project_model_instantiation(self):
        """Weryfikacja pełnego ProjectModel."""
        model = ProjectModel(
            project_id="proj_001",
            project_name="Test Project",
            project_type="quick_quote",
            status="active",
            source="test",

            header=ProjectHeader(
                project_name="Test",
                client_name="ACME",
                source_kind="quick_quote"
            ),

            quote_context=ProjectQuoteContext(
                mode="quick_quote",
                margin_percent=10.0,
                vat_percent=23.0
            ),

            quote_lines=[
                ProjectQuoteLine(
                    line_id="l1",
                    cost_material=100.0,
                    line_total=100.0,
                    accuracy="snapshot"
                ),
                ProjectQuoteLine(
                    line_id="l2",
                    cost_material=50.0,
                    line_total=50.0,
                    accuracy="snapshot"
                )
            ],

            pricing_snapshot=ProjectPricingSnapshot(
                material_value=150.0,
                base_total=150.0,
                sale_total=165.0,
                brutto_total=202.95,
                computed_at="2026-04-10T12:00:00Z"
            )
        )

        # Walidacja struktury
        assert model.project_type == "quick_quote"
        assert len(model.quote_lines) == 2
        assert model.pricing_snapshot.material_value == 150.0

    def test_serialization_deserialization(self):
        """Weryfikacja to_dict/from_dict round-trip."""
        original = ProjectModel(
            project_id="proj_001",
            project_name="Test",
            project_type="quick_quote",
            status="active",
            header=ProjectHeader(
                client_name="ACME",
                order_code="001"
            ),
            quote_context=ProjectQuoteContext(
                mode="quick_quote",
                margin_percent=10.0
            ),
            pricing_snapshot=ProjectPricingSnapshot(
                base_total=1000.0,
                brutto_total=1230.0
            )
        )

        # Serializacja
        data = original.to_dict()
        assert data["project_id"] == "proj_001"
        assert data["header"]["client_name"] == "ACME"

        # Deserializacja
        restored = ProjectModel.from_dict(data)
        assert restored.project_id == original.project_id
        assert restored.header.client_name == original.header.client_name
        assert restored.pricing_snapshot.base_total == original.pricing_snapshot.base_total


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
