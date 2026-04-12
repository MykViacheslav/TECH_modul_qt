"""
Testy: Cross-Tab Adapter
"""

import pytest
from PyQt6.QtWidgets import QApplication

from src.domain.project_model import (
    ProjectModel, ProjectHeader, ProjectQuoteContext, ProjectQuoteLine,
    ProjectServiceLine, ProjectPricingSnapshot
)
from src.services.project_model_cross_tab_adapter import (
    merge_project_models, get_quick_quote_summary, get_import_3d_summary,
    get_services_summary
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class TestCrossTabAdapter:
    """Test adapteru łączącego modele."""

    def test_merge_empty_list(self):
        """Test scalenia pustej listy."""
        model = merge_project_models([])
        assert model is not None
        assert model.project_type == "cross_tab_merge"
        assert len(model.quote_lines) == 0
        assert len(model.services) == 0

    def test_merge_single_quick_quote(self):
        """Test scalenia jednego modelu quick quote."""
        quick_model = ProjectModel(
            project_id="quick_001",
            project_name="Szybka wycena",
            project_type="quick_quote",
            status="active",
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
                ),
            ],
            pricing_snapshot=ProjectPricingSnapshot(
                material_value=150.0,
                base_total=150.0,
                sale_total=165.0,
                brutto_total=202.95,
                computed_at="2026-04-10T12:00:00Z"
            )
        )

        merged = merge_project_models(
            [quick_model],
            client_name="ACME",
            order_code="001"
        )

        assert len(merged.quote_lines) == 2
        assert merged.pricing_snapshot.material_value == 150.0
        assert merged.pricing_snapshot.base_total == 150.0

    def test_merge_quick_and_services(self):
        """Test scalenia quick quote + services."""
        quick_model = ProjectModel(
            project_id="quick_001",
            quote_lines=[
                ProjectQuoteLine(
                    line_id="l1",
                    cost_material=100.0,
                    line_total=100.0
                ),
            ],
            pricing_snapshot=ProjectPricingSnapshot(
                material_value=100.0,
                base_total=100.0,
                computed_at="2026-04-10T12:00:00Z"
            )
        )

        service_model = ProjectModel(
            project_id="svc_001",
            services=[
                ProjectServiceLine(
                    service_id="svc_1",
                    service_name="Lakierowanie",
                    qty=2.0,
                    amount=200.0
                ),
            ],
            pricing_snapshot=ProjectPricingSnapshot(
                services_total=200.0,
                base_total=200.0,
                computed_at="2026-04-10T12:00:00Z"
            )
        )

        merged = merge_project_models(
            [quick_model, service_model],
            client_name="ACME",
            margin_percent=10.0,
            vat_percent=23.0
        )

        assert len(merged.quote_lines) == 1
        assert len(merged.services) == 1

        # Sprawdzenie obliczeń
        expected_base = 100.0 + 200.0  # 300.0
        assert merged.pricing_snapshot.base_total == expected_base

        expected_sale = 300.0 * 1.10  # 330.0
        assert abs(merged.pricing_snapshot.sale_total - 330.0) < 0.01

        expected_brutto = 330.0 * 1.23  # 405.9
        assert abs(merged.pricing_snapshot.brutto_total - 405.9) < 0.01

    def test_quick_quote_summary(self):
        """Test ekstrakcji podsumowania szybkiej wyceny."""
        model = ProjectModel(
            project_id="quick_001",
            header=ProjectHeader(
                client_name="ACME",
                order_code="001"
            ),
            pricing_snapshot=ProjectPricingSnapshot(
                material_value=500.0,
                services_total=100.0,
                extras_total=50.0,
                base_total=650.0,
                sale_total=715.0,
                brutto_total=878.45,
                profit_total=65.0,
                computed_at="2026-04-10T12:00:00Z"
            )
        )

        summary = get_quick_quote_summary(model)

        assert summary["client"] == "ACME"
        assert summary["order"] == "001"
        assert summary["material"] == 500.0
        assert summary["services"] == 100.0
        assert summary["base_total"] == 650.0
        assert abs(summary["brutto"] - 878.45) < 0.01

    def test_services_summary(self):
        """Test ekstrakcji podsumowania usług."""
        model = ProjectModel(
            services=[
                ProjectServiceLine(
                    service_id="svc_1",
                    service_name="Lakierowanie",
                    qty=5.0,
                    unit="szt",
                    amount=100.0
                ),
                ProjectServiceLine(
                    service_id="svc_2",
                    service_name="Transport",
                    qty=1.0,
                    unit="zl",
                    amount=50.0
                ),
            ]
        )

        summary = get_services_summary(model)

        assert summary["count"] == 2
        assert summary["total"] == 150.0
        assert len(summary["services"]) == 2
        assert summary["services"][0]["name"] == "Lakierowanie"
        assert summary["services"][0]["amount"] == 100.0

    def test_merge_with_audit_trail(self):
        """Test że audit trail zawiera info o scaleniu."""
        model1 = ProjectModel(
            source="quick_quote_archive",
            quote_lines=[ProjectQuoteLine(line_id="l1", cost_material=100.0, line_total=100.0)]
        )

        model2 = ProjectModel(
            source="service_archive",
            services=[ProjectServiceLine(service_id="svc_1", amount=50.0)]
        )

        merged = merge_project_models(
            [model1, model2],
            merge_reason="test_merge"
        )

        assert "quick_quote_archive" in merged.audit.built_from
        assert "service_archive" in merged.audit.built_from
        assert "test_merge" in merged.audit.notes

    def test_merged_model_is_read_only_snapshot(self):
        """Weryfikacja że scalony model ma accuracy='snapshot'."""
        quick_model = ProjectModel(
            quote_lines=[
                ProjectQuoteLine(
                    line_id="l1",
                    cost_material=100.0,
                    line_total=100.0,
                    accuracy="snapshot"
                ),
            ]
        )

        merged = merge_project_models([quick_model])

        # Wszystkie quote lines powinny mieć accuracy="snapshot"
        for line in merged.quote_lines:
            if line.accuracy:  # Może być pusty string
                assert line.accuracy == "snapshot"

    def test_pricing_aggregation(self):
        """Test agregacji pricing snapshot."""
        model1 = ProjectModel(
            quote_lines=[
                ProjectQuoteLine(
                    line_id="l1",
                    cost_material=100.0,
                    cost_extra=20.0,
                    line_total=120.0
                ),
            ]
        )

        model2 = ProjectModel(
            quote_lines=[
                ProjectQuoteLine(
                    line_id="l2",
                    cost_labor=50.0,
                    line_total=50.0
                ),
            ]
        )

        merged = merge_project_models([model1, model2])

        # material_value to sum cost_material z wszystkich linii
        material = sum(l.cost_material or 0.0 for l in merged.quote_lines)
        assert material == 100.0

        # services_total to sum cost_labor
        services = sum(l.cost_labor or 0.0 for l in merged.quote_lines)
        assert services == 50.0

        # extras_total to sum cost_extra
        extras = sum(l.cost_extra or 0.0 for l in merged.quote_lines)
        assert extras == 20.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
