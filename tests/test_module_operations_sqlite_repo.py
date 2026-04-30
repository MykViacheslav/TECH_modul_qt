from __future__ import annotations

from pathlib import Path

from src.api.data_manager import TechModulDataManager
from src.domain.operations.adapters.sqlite_project_module_repository import SqliteProjectModuleRepository
from src.domain.operations.module_ops import ModuleOperations


def _seed(db_path: Path) -> TechModulDataManager:
    dm = TechModulDataManager(db_path=str(db_path))
    with __import__("sqlite3").connect(str(db_path)) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM project_modules")
        cur.execute("DELETE FROM projects")
        cur.execute("INSERT INTO projects (id, title, client_name) VALUES (1, 'P1', 'C1')")
        cur.execute(
            "INSERT INTO project_modules (id, project_id, module_name, width, height, depth) VALUES (1, 1, 'M1', 600, 720, 500)"
        )
        conn.commit()
    return dm


def test_sqlite_repository_preview_apply(tmp_path: Path) -> None:
    db_path = tmp_path / "tech_modul_test.db"
    dm = _seed(db_path)
    repo = SqliteProjectModuleRepository(data_manager=dm, project_id=1)
    ops = ModuleOperations(repository=repo)

    preview = ops.set_depth({"id": "1"}, depth_mm=650, mode="preview", source="test").to_dict()
    assert preview["status"] == "ok"
    assert preview["can_apply"] is True

    before = dm.get_project_modules(1)[0]
    assert int(before["depth"]) == 500

    apply = ops.set_depth({"id": "1"}, depth_mm=650, mode="apply", source="test").to_dict()
    assert apply["status"] == "ok"
    assert apply["can_apply"] is False

    after = dm.get_project_modules(1)[0]
    assert int(after["depth"]) == 650

