from pathlib import Path

from core.constructor3d_project import import_project_modules


def test_import_project_modules_reads_top_level_assembly(tmp_path: Path):
    project = tmp_path / "one.project"
    project.write_text(
        """<?xml version="1.0" encoding="UTF-8" ?>
<Project3dc name="Demo" date="2026.05.29" version="3.0">
<ProjectStructure>
<Obj id="8" class="1" code="ASS1.01.000" name="Inner" dtl="363.4" dtw="506.7" dtt="743.4" parent="1"></Obj>
<Obj id="1" class="1" code="ASS1.00.000" name="SZ_D_1F_lewa" dtl="400" dtw="525" dtt="780"></Obj>
</ProjectStructure>
</Project3dc>
""",
        encoding="utf-8",
    )

    modules = import_project_modules(project)

    assert len(modules) == 1
    assert modules[0]["code"] == "ASS1.00.000"
    assert modules[0]["name"] == "SZ_D_1F_lewa"
    assert modules[0]["length"] == 400
    assert modules[0]["width"] == 525
    assert modules[0]["height"] == 780
