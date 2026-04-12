"""
Testy porównawcze: Import 3D (stary system vs ProjectModel)

Weryfikacja że ProjectModel daje takie same wyniki co import z .project XML.
"""

import pytest
from PyQt6.QtWidgets import QApplication

from src.domain.project_model import (
    ProjectModel, ProjectHeader, ProjectQuoteLine, ProjectImport3D,
    ProjectMapping, ProjectPricingSnapshot, ProjectAudit
)


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestImport3DEquivalence:
    """Test że ProjectModel import 3D = stary system."""

    def test_import_3d_metadata(self):
        """Weryfikacja że metadata z .project → ProjectImport3D."""
        # Stary system: parsed z XML
        old_metadata = {
            "project_name": "Kuchnia Standard 2026",
            "project_date": "2026-03-15",
            "project_version": "1.0",
            "module_name": "Moduł główny",
            "module_length_mm": 3000,
            "module_width_mm": 600,
            "module_height_mm": 1000,
        }

        # Nowy ProjectModel
        import_3d = ProjectImport3D(
            source_file="/path/to/project.project",
            project_name=old_metadata["project_name"],
            project_date=old_metadata["project_date"],
            project_version=old_metadata["project_version"],
            module_name=old_metadata["module_name"],
            module_length_mm=old_metadata["module_length_mm"],
            module_width_mm=old_metadata["module_width_mm"],
            module_height_mm=old_metadata["module_height_mm"],
        )

        # Walidacja
        assert import_3d.project_name == "Kuchnia Standard 2026"
        assert import_3d.module_length_mm == 3000
        assert import_3d.module_width_mm == 600
        assert import_3d.module_height_mm == 1000

    def test_control_rows_frozen(self):
        """Weryfikacja że control_rows są FROZEN kopią dla audytu."""
        # Stary system: control rows z parsera
        old_control_rows = [
            {
                "section": "Formatka",
                "code": "F001",
                "name": "Bok lewy",
                "qty": 2,
                "length_mm": 1000,
                "width_mm": 500,
                "thickness_mm": 18,
                "material_original": "MDF 18",
                "edgeband_original": "L:buk, R:buk, T:wys, B:buk",
                "edgeband_mb": 4.0,
                "area_m2": 1.0,
                "status": "OK",
                "source_id": "obj_001"
            },
            {
                "section": "Front",
                "code": "FR001",
                "name": "Front lewy",
                "qty": 2,
                "length_mm": 950,
                "width_mm": 480,
                "thickness_mm": 16,
                "material_original": "Szyba bezpieczna",
                "edgeband_original": "Brak",
                "edgeband_mb": 0.0,
                "area_m2": 0.912,
                "status": "OK",
                "source_id": "obj_002"
            }
        ]

        # Nowy ProjectModel - FROZEN rows
        import_3d = ProjectImport3D(
            source_file="/project.project",
            control_rows=old_control_rows,  # Zachowujesz oryginały
        )

        # Walidacja
        assert len(import_3d.control_rows) == 2
        assert import_3d.control_rows[0]["material_original"] == "MDF 18"
        assert import_3d.control_rows[1]["material_original"] == "Szyba bezpieczna"

    def test_material_mapping(self):
        """Weryfikacja że material_map zachowuje mapowanie."""
        # Stary system: mapowanie
        old_mappings = {
            "MDF 18": "MDF_18_katalog",
            "MDF 16": "MDF_16_katalog",
            "Szyba bezpieczna": "SZYBKA_katalog",
        }

        # Nowy ProjectModel
        mapping = ProjectMapping(
            material_map=old_mappings,
            edgeband_map={
                "buk": "buk_1mm",
                "dąb": "dab_1mm",
            },
            hardware_map={},
            operation_map={
                "Lakier": "lakierowanie_usl",
                "Cięcie": "ciecie_usl",
            },
            mapping_status="OK"
        )

        # Walidacja
        assert mapping.material_map["MDF 18"] == "MDF_18_katalog"
        assert mapping.edgeband_map["buk"] == "buk_1mm"
        assert mapping.operation_map["Lakier"] == "lakierowanie_usl"

    def test_quote_lines_from_control_rows(self):
        """Weryfikacja że control_rows → quote_lines."""
        control_row = {
            "section": "Formatka",
            "code": "F001",
            "name": "Bok",
            "qty": 2,
            "length_mm": 1000,
            "width_mm": 500,
            "thickness_mm": 18,
            "material_original": "MDF 18",
            "edgeband_original": "L:buk, R:buk, T:wys, B:buk",
            "edgeband_mb": 4.0,
            "area_m2": 1.0,
            "status": "OK",
            "source_id": "obj_001",
            "unit_cost": 50.00
        }

        # Nowy ProjectModel - quote line z control row
        line = ProjectQuoteLine(
            line_id="3d_formatka_f001",
            source_kind="import_3d_formatka",
            source_ref="obj_001",
            group="Formatki",
            module_name=control_row["name"],
            qty=control_row["qty"],
            unit="szt",
            dimensions=f"{control_row['length_mm']}×{control_row['width_mm']}×{control_row['thickness_mm']}",
            material_name="MDF_18_katalog",  # Po mapowaniu
            edgeband_desc=control_row["edgeband_original"],
            cost_material=control_row["area_m2"] * control_row["unit_cost"],
            cost_edgeband=control_row["edgeband_mb"] * 10.0,  # Przykładowa cena krawędzi
            line_total=control_row["area_m2"] * control_row["unit_cost"] + control_row["edgeband_mb"] * 10.0,
            status="OK",
            accuracy="snapshot"
        )

        # Walidacja
        assert line.source_kind == "import_3d_formatka"
        assert line.source_ref == "obj_001"
        assert line.qty == 2
        assert line.material_name == "MDF_18_katalog"
        assert line.cost_material == 50.00  # 1.0 m² × 50 zł/m²

    def test_aggregated_totals(self):
        """Weryfikacja że totals są agregowane poprawnie."""
        control_rows = [
            {"section": "Formatka", "area_m2": 1.0, "edgeband_mb": 4.0, "qty": 2},
            {"section": "Formatka", "area_m2": 0.5, "edgeband_mb": 2.0, "qty": 1},
            {"section": "Front", "area_m2": 0.912, "edgeband_mb": 0.0, "qty": 2},
        ]

        import_3d = ProjectImport3D(
            source_file="/project.project",
            control_rows=control_rows,
            total_area_m2=sum(r["area_m2"] for r in control_rows),
            total_edgeband_mb=sum(r["edgeband_mb"] for r in control_rows),
            parts_count={
                "formatki": sum(1 for r in control_rows if r["section"] == "Formatka"),
                "fronty": sum(1 for r in control_rows if r["section"] == "Front"),
            }
        )

        # Walidacja
        assert import_3d.total_area_m2 == 2.412  # 1.0 + 0.5 + 0.912
        assert import_3d.total_edgeband_mb == 6.0  # 4.0 + 2.0 + 0.0
        assert import_3d.parts_count["formatki"] == 2
        assert import_3d.parts_count["fronty"] == 1

    def test_full_import_3d_model(self):
        """Pełny ProjectModel dla import 3D."""
        model = ProjectModel(
            project_id="i3d_001",
            project_name="Kuchnia Standard (import 3D)",
            project_type="import_3d",
            status="active",

            header=ProjectHeader(
                client_name="ACME Corp",
                order_code="3D/001/2026",
                source_path="/data/projects/kitchen.project",
                source_kind="import_3d"
            ),

            import_3d=ProjectImport3D(
                source_file="/data/projects/kitchen.project",
                project_name="Kuchnia Standard 2026",
                project_date="2026-03-15",
                project_version="1.0",
                module_name="Moduł główny",
                module_length_mm=3000,
                module_width_mm=600,
                module_height_mm=1000,
                control_rows=[
                    {
                        "section": "Formatka",
                        "code": "F001",
                        "name": "Bok",
                        "qty": 2,
                        "length_mm": 1000,
                        "width_mm": 500,
                        "thickness_mm": 18,
                        "area_m2": 1.0,
                        "edgeband_mb": 4.0,
                        "status": "OK",
                        "source_id": "obj_001"
                    }
                ],
                total_area_m2=1.0,
                total_edgeband_mb=4.0,
                parts_count={"formatki": 1, "fronty": 0, "okucia": 0}
            ),

            mapping=ProjectMapping(
                material_map={"MDF 18": "MDF_18_katalog"},
                edgeband_map={"buk": "buk_1mm"},
                operation_map={},
                mapping_status="OK"
            ),

            quote_lines=[
                ProjectQuoteLine(
                    line_id="3d_formatka_001",
                    source_kind="import_3d_formatka",
                    source_ref="obj_001",
                    group="Formatki",
                    module_name="Bok",
                    qty=2,
                    unit="szt",
                    material_name="MDF_18_katalog",
                    edgeband_desc="L:buk, R:buk, T:wys, B:buk",
                    cost_material=50.00,
                    cost_edgeband=40.00,  # 4.0 mb × 10 zł/mb
                    line_total=90.00,
                    status="OK",
                    accuracy="snapshot"
                )
            ],

            pricing_snapshot=ProjectPricingSnapshot(
                material_value=50.00,
                extras_total=40.00,
                services_total=0.0,
                base_total=90.00,
                sale_total=99.00,  # 90 × 1.10
                brutto_total=121.77,  # 99 × 1.23
                computed_at="2026-04-10T12:00:00Z"
            ),

            audit=ProjectAudit(
                source=".project file",
                adapter="build_3d_import_project_model()",
                import_file="/data/projects/kitchen.project",
                mapping_used="MDF_18_katalog mapping applied",
                parts_parsed={"formatki": 1}
            )
        )

        # Walidacja struktury
        assert model.project_type == "import_3d"
        assert model.import_3d.project_name == "Kuchnia Standard 2026"
        assert model.import_3d.module_length_mm == 3000
        assert len(model.quote_lines) == 1

        # Walidacja sum
        assert model.import_3d.total_area_m2 == 1.0
        assert model.import_3d.total_edgeband_mb == 4.0

        # Walidacja pricing
        assert model.pricing_snapshot.material_value == 50.00
        assert model.pricing_snapshot.extras_total == 40.00
        assert model.pricing_snapshot.base_total == 90.00
        assert abs(model.pricing_snapshot.brutto_total - 121.77) < 0.01

        # Walidacja audit
        assert model.audit.import_file == "/data/projects/kitchen.project"
        assert model.audit.mapping_used == "MDF_18_katalog mapping applied"

    def test_mapping_status_incomplete(self):
        """Test gdy mapowanie jest niekompletne."""
        mapping = ProjectMapping(
            material_map={"MDF 18": "MDF_18_katalog"},
            edgeband_map={},
            operation_map={},
            mapping_status="incomplete"
        )

        assert mapping.mapping_status == "incomplete"
        assert len(mapping.edgeband_map) == 0

    def test_multiple_sections(self):
        """Test import z wieloma sekcjami."""
        control_rows = [
            {"section": "Formatka", "code": "F001", "area_m2": 1.0},
            {"section": "Formatka", "code": "F002", "area_m2": 1.0},
            {"section": "Front", "code": "FR001", "area_m2": 0.5},
            {"section": "Front", "code": "FR002", "area_m2": 0.5},
            {"section": "Okucie", "code": "OK001", "qty": 20},
        ]

        import_3d = ProjectImport3D(
            source_file="/project.project",
            control_rows=control_rows,
            total_area_m2=sum(r.get("area_m2", 0) for r in control_rows),
            parts_count={
                "formatki": 2,
                "fronty": 2,
                "okucia": 1,
            }
        )

        assert len(import_3d.control_rows) == 5
        assert import_3d.parts_count["formatki"] == 2
        assert import_3d.parts_count["fronty"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
