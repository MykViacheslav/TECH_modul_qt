from __future__ import annotations

import html

from src.services.constructor_3dc_quote_import_service import parse_3dc_project_for_quote_import


def test_parse_3dc_quote_import_extracts_cnc_technology_summary(tmp_path):
    program_xml = """
<program dx="1000" dy="500" dz="18">
  <tool name="Bore5" d="5" />
  <tool name="Groove4" d="4" />
  <tool name="Mill6" d="6" />
  <bf name="Bore5" dp="12" />
  <br name="Bore5" dp="10" />
  <gr name="Groove4" x1="0" y1="0" x2="500" y2="0" dp="8" t="4" />
  <ms name="Mill6" x="0" y="0" dp="6" />
  <ml x="100" y="0" />
  <mac x="100" y="100" cx="50" cy="50" />
</program>
""".strip()
    escaped_program = html.escape(program_xml, quote=True)

    project_xml = f"""
<Project3dc name="CNC_TEST" date="2026.04.25" version="3.0">
  <Dictionary>
    <Classes>
      <Item id="18" description="Sheet part" />
    </Classes>
    <Materials>
      <Item id="m1" code="LAM-001" name="Laminat Bialy" thick="18" />
      <Item id="b1" code="ABS-1" name="ABS 1mm" />
    </Materials>
    <Units />
  </Dictionary>
  <ProjectStructure>
    <Obj
      id="p1"
      class="18"
      code="PANEL-1"
      name="Panel testowy"
      quantity="2"
      dl="1000"
      dw="500"
      dtt="18"
      material="m1"
      bandL="b1"
      bandR="b1"
    />
  </ProjectStructure>
  <operations>
    <operation typeId="XNC" program="{escaped_program}">
      <part id="p1" />
    </operation>
  </operations>
</Project3dc>
""".strip()

    project_path = tmp_path / "cnc_test.project"
    project_path.write_text(project_xml, encoding="utf-8")

    parsed = parse_3dc_project_for_quote_import(project_path)
    assert parsed.summary.project_name == "CNC_TEST"
    assert parsed.summary.formatki_count == 1
    assert len(parsed.control_rows) == 1

    row = parsed.control_rows[0]
    assert row.section == "Formatka"
    assert row.cnc_data is not None
    assert "<program" in row.cnc_data

    ts = row.technology_summary
    assert ts is not None

    assert ts["part_name"] == "Panel testowy"
    assert ts["part_type"] == "panel"
    assert ts["material_name"] == "LAM-001 | Laminat Bialy"

    assert ts["drill_count_total"] == 2
    assert ts["drill_count_face"] == 1
    assert ts["drill_count_edge"] == 1
    assert 5 in ts["drill_diameters_mm"]
    assert 10 in ts["drill_depths_mm"]
    assert 12 in ts["drill_depths_mm"]

    assert ts["groove_count"] == 1
    assert ts["groove_total_length_mm"] == 500.0
    assert 8 in ts["groove_depths_mm"]
    assert 4 in ts["groove_tool_widths_mm"]

    assert ts["milling_count"] == 1
    assert ts["milling_line_count"] == 1
    assert ts["milling_arc_count"] == 1
    assert ts["milling_total_path_length_mm"] > 100.0
    assert ts["milling_length_estimated_mm"] == ts["milling_total_path_length_mm"]
    assert 6 in ts["milling_tool_diameters_mm"]
    assert 6 in ts["milling_depths_mm"]

    assert "Bore5" in ts["tool_names"]
    assert "Groove4" in ts["tool_names"]
    assert "Mill6" in ts["tool_names"]
    assert ts["tool_count_unique"] >= 3

    assert ts["has_drilling"] is True
    assert ts["has_grooving"] is True
    assert ts["has_milling"] is True
    assert ts["operation_count_total"] >= 5
    assert ts["operation_type_count"] == 3
    assert ts["cnc_complexity_score"] > 0
