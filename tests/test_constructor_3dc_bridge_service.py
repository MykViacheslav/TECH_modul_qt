from __future__ import annotations

from pathlib import Path

import pytest


def _sample_project_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Project3dc name="ZEUS_TEST" date="2026.04.03" version="3.0">
  <Dictionary>
    <Materials>
      <Item id="202:378" type="sheet" code="01.011_18K2" name="Plyta_biala_18K2" thick="18.2" cost="0" />
      <Item id="203:2" type="band" code="P_1" name="PVC White 1 mm" cost="0.3" thick="1" />
    </Materials>
  </Dictionary>
  <ProjectStructure>
    <Obj id="13" class="18" code="ASS1.02.003" name="polka" quantity="2" l="809.6" w="145" material="202:378"
      bandL="203:2" bandT="203:2" bandR="" bandB="203:2" />
    <Obj id="20" class="6" code="A500" name="Edging" quantity="1" />
  </ProjectStructure>
</Project3dc>
"""


def test_parse_3dc_project_parts_reads_sheet_parts(tmp_path):
    project_path = tmp_path / "test.project"
    project_path.write_text(_sample_project_xml(), encoding="utf-8")

    from src.services.constructor_3dc_bridge_service import parse_3dc_project_parts

    parts = parse_3dc_project_parts(project_path)
    assert len(parts) == 1
    part = parts[0]
    assert part.project_name == "ZEUS_TEST"
    assert part.obj_id == "13"
    assert part.obj_code == "ASS1.02.003"
    assert part.name == "polka"
    assert part.material_id == "202:378"
    assert "01.011_18K2" in part.material_name
    assert part.length_l_mm == pytest.approx(809.6, rel=1e-9)
    assert part.length_b_mm == pytest.approx(145.0, rel=1e-9)
    assert part.qty == pytest.approx(2.0, rel=1e-9)
    assert part.edge_l is True
    assert part.edge_g is True
    assert part.edge_p is False
    assert part.edge_d is True


def test_export_giblab_csv_from_3dc_project_creates_csv(tmp_path):
    project_path = tmp_path / "test.project"
    project_path.write_text(_sample_project_xml(), encoding="utf-8")
    out_path = tmp_path / "out.csv"

    from src.services.constructor_3dc_bridge_service import export_giblab_csv_from_3dc_project

    saved = export_giblab_csv_from_3dc_project(project_path, out_path)
    assert saved == out_path
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8-sig")
    assert "Pozycja;Material;ID;Nazwa;L_mm;B_mm;Sztuki;Okleina_L;Okleina_P;Okleina_G;Okleina_D;Uwagi" in content
    assert "ZEUS_TEST" in content
    assert "ASS1.02.003" in content
    assert "polka" in content
    assert "809.6;145;2;1;0;1;1" in content


def test_export_giblab_csv_from_3dc_project_raises_when_no_sheet_parts(tmp_path):
    project_path = tmp_path / "empty.project"
    project_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<Project3dc name="EMPTY">
  <Dictionary><Materials /></Dictionary>
  <ProjectStructure>
    <Obj id="P1" class="6" code="A500" name="Edging" quantity="1" />
  </ProjectStructure>
</Project3dc>
""",
        encoding="utf-8",
    )
    out_path = tmp_path / "out.csv"

    from src.services.constructor_3dc_bridge_service import Constructor3dcParseError, export_giblab_csv_from_3dc_project

    with pytest.raises(Constructor3dcParseError):
        export_giblab_csv_from_3dc_project(project_path, out_path)


def test_build_formatki_rows_from_3dc_project_maps_dimensions_edges_and_notes(tmp_path):
    project_path = tmp_path / "test.project"
    project_path.write_text(_sample_project_xml(), encoding="utf-8")

    from src.services.constructor_3dc_bridge_service import build_formatki_rows_from_3dc_project

    project_name, rows = build_formatki_rows_from_3dc_project(project_path)
    assert project_name == "ZEUS_TEST"
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "ASS1.02.003"
    assert row["name"] == "polka"
    assert row["length_l"] == "809.6"
    assert row["length_b"] == "145"
    assert row["qty"] == pytest.approx(2.0, rel=1e-9)
    assert row["m2"] == pytest.approx((809.6 * 145.0 * 2.0) / 1_000_000.0, rel=1e-9)
    assert row["okleina_l"] is True
    assert row["okleina_p"] is False
    assert row["okleina_g"] is True
    assert row["okleina_d"] is True
    expected_okleina = 2.0 * ((809.6 / 1000.0) + (145.0 / 1000.0) + (145.0 / 1000.0))
    assert row["okleina_mb"] == pytest.approx(expected_okleina, rel=1e-9)
    assert "3dc:ZEUS_TEST" in row["notes"]
    assert "01.011_18K2" in row["notes"]


def test_build_formatki_rows_from_3dc_project_raises_when_no_sheet_parts(tmp_path):
    project_path = tmp_path / "empty.project"
    project_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<Project3dc name="EMPTY">
  <Dictionary><Materials /></Dictionary>
  <ProjectStructure>
    <Obj id="P1" class="6" code="A500" name="Edging" quantity="1" />
  </ProjectStructure>
</Project3dc>
""",
        encoding="utf-8",
    )

    from src.services.constructor_3dc_bridge_service import Constructor3dcParseError, build_formatki_rows_from_3dc_project

    with pytest.raises(Constructor3dcParseError):
        build_formatki_rows_from_3dc_project(project_path)


def test_build_position_payload_from_3dc_project_returns_project_material_hint_and_rows(tmp_path):
    project_path = tmp_path / "test.project"
    project_path.write_text(_sample_project_xml(), encoding="utf-8")

    from src.services.constructor_3dc_bridge_service import build_position_payload_from_3dc_project

    payload = build_position_payload_from_3dc_project(project_path)
    assert payload["project_name"] == "ZEUS_TEST"
    assert payload["parts_count"] == 1
    assert isinstance(payload["formatki_rows"], list)
    assert len(payload["formatki_rows"]) == 1
    assert payload["material_name_hint"]


def test_build_position_payload_from_3dc_project_raises_when_no_sheet_parts(tmp_path):
    project_path = tmp_path / "empty.project"
    project_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<Project3dc name="EMPTY">
  <Dictionary><Materials /></Dictionary>
  <ProjectStructure>
    <Obj id="P1" class="6" code="A500" name="Edging" quantity="1" />
  </ProjectStructure>
</Project3dc>
""",
        encoding="utf-8",
    )

    from src.services.constructor_3dc_bridge_service import Constructor3dcParseError, build_position_payload_from_3dc_project

    with pytest.raises(Constructor3dcParseError):
        build_position_payload_from_3dc_project(project_path)
