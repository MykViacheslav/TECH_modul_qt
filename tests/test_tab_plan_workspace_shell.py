from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.domain.assembly_models import AssemblyModuleItemDef, FurnitureAssemblyDef
from src.domain.module_models import ModuleDef
from src.domain.wall_models import WallLayoutDef, WallObstacleDef
from src.storage.assembly_store_json import AssemblyStoreJson
from src.storage.wall_store_json import WallStoreJson
from src.tabs.plan.tab_plan import TabPlan


def test_tab_plan_workspace_shell_selects_real_module(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module = ModuleDef(
        name="M_PHASE1",
        width_mm=800.0,
        height_mm=720.0,
        depth_mm=560.0,
    )
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM1",
        name="Komplet Phase1",
        wall_name="Sciana A",
        width_mm=3000.0,
        height_mm=2500.0,
        depth_mm=600.0,
        items=[
            AssemblyModuleItemDef(
                source_name="M_PHASE1",
                instance_name="M_PHASE1_1",
                offset_ref_mode="wall_left",
                offset_mm=120.0,
                module=module,
            )
        ],
    )
    wall = WallLayoutDef(
        name="Sciana A",
        wall_a_width_mm=3000.0,
        room_height_mm=2500.0,
    )

    wall_store = WallStoreJson()
    assembly_store = AssemblyStoreJson()
    wall_store.overwrite(wall)
    assembly_store.overwrite(assembly)

    tab = TabPlan()

    assert tab.cb_assembly.count() >= 1
    assert len(tab._resolved_items) == 1
    assert tab._selected_item is not None
    assert str(getattr(tab._selected_item.module, "name", "") or "") == "M_PHASE1"
    assert tab.btn_open_modul_tab.isEnabled()
    assert "M_PHASE1" in tab.lbl_module_summary.text()

    tab._on_scene_module_clicked(tab._resolved_items[0])
    assert tab.btn_open_modul_tab.isEnabled()
    assert "M_PHASE1" in tab.lbl_module_summary.text()

    tab._set_mode("komplet")
    assert "Tryb Komplet" in tab.lbl_komplet_summary.text()
    assert "Sciana A" in tab.lbl_komplet_summary.text()
    assert "Liczba modulow: 1" in tab.lbl_komplet_summary.text()
    wall_item = tab.tree_komplet.topLevelItem(0)
    assert wall_item is not None
    komplet_item = wall_item.child(0)
    assert komplet_item is not None
    module_item = komplet_item.child(0)
    assert module_item is not None

    tab._on_komplet_tree_item_clicked(module_item, 0)
    assert tab._selected_item is not None
    assert str(getattr(tab._selected_item.module, "name", "") or "") == "M_PHASE1"


def test_tab_plan_workspace_shell_handles_empty_state(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    tab = TabPlan()

    assert tab.cb_assembly.isEnabled() is False
    assert tab._selected_item is None
    assert "Brak aktywnego kompletu" in tab.lbl_workspace_state.text()
    assert "brak aktywnego kompletu" in tab._scene_hint.text().lower()


def test_tab_plan_workspace_shell_renders_wall_context_without_assembly(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    wall = WallLayoutDef(
        name="Sciana B",
        wall_a_width_mm=4200.0,
        room_height_mm=2700.0,
        obstacles=[
            WallObstacleDef(
                kind="window",
                name="Okno",
                x_mm=1100.0,
                bottom_offset_mm=900.0,
                width_mm=1200.0,
                height_mm=1000.0,
            )
        ],
    )
    wall_store = WallStoreJson()
    wall_store.overwrite(wall)

    tab = TabPlan()
    tab.cb_wall.setCurrentIndex(1)
    tab._set_mode("sciana")

    assert tab.cb_assembly.isEnabled() is False
    assert "Przeszkody: 1" in tab.lbl_wall_summary.text()
    assert "sciana bez kompletu" in tab._scene_hint.text().lower()


def test_tab_plan_workspace_shell_syncs_scene_selection_to_tree(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module1 = ModuleDef(name="M_A", width_mm=600.0, height_mm=720.0, depth_mm=560.0)
    module2 = ModuleDef(name="M_B", width_mm=800.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM2",
        name="Komplet Sync",
        wall_name="Sciana Sync",
        width_mm=3600.0,
        height_mm=2600.0,
        items=[
            AssemblyModuleItemDef(source_name="M_A", instance_name="M_A_1", offset_mm=0.0, module=module1),
            AssemblyModuleItemDef(source_name="M_B", instance_name="M_B_1", offset_ref_mode="previous_module", offset_mm=100.0, module=module2),
        ],
    )
    wall = WallLayoutDef(name="Sciana Sync", wall_a_width_mm=3600.0, room_height_mm=2600.0)
    wall_store = WallStoreJson()
    assembly_store = AssemblyStoreJson()
    wall_store.overwrite(wall)
    assembly_store.overwrite(assembly)

    tab = TabPlan()
    assert len(tab._resolved_items) == 2

    second = tab._resolved_items[1]
    tab._on_scene_module_clicked(second)

    current = tab.tree_komplet.currentItem()
    assert current is not None
    assert int(current.data(0, int(Qt.ItemDataRole.UserRole) + 1)) == 1
    assert tab._selected_item is second
    assert "M_B" in tab.lbl_module_summary.text()
    selected_rows = [row for row in tab._module_scene_payload if bool(row.get("is_selected"))]
    assert len(selected_rows) == 1
    assert str(selected_rows[0].get("display_label", "")) == "M_B"


def test_tab_plan_workspace_shell_handles_missing_wall_for_existing_assembly(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module = ModuleDef(name="M_NOWALL", width_mm=700.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM_NOWALL",
        name="Komplet Bez Sciany",
        wall_name="Sciana Nie Istnieje",
        width_mm=3100.0,
        height_mm=2550.0,
        items=[AssemblyModuleItemDef(source_name="M_NOWALL", instance_name="M_NOWALL_1", module=module)],
    )
    assembly_store = AssemblyStoreJson()
    assembly_store.overwrite(assembly)

    tab = TabPlan()
    assert len(tab._resolved_items) == 1
    assert "Przeszkody na scianie: 0" in tab._scene_hint.text()
    tab._set_mode("sciana")
    assert "Sciana: Sciana Nie Istnieje" in tab.lbl_wall_summary.text()
    assert "Sciana nie istnieje w bazie" in tab.lbl_wall_summary.text()


def test_tab_plan_workspace_shell_phase3_order_actions(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module1 = ModuleDef(name="M_1", width_mm=600.0, height_mm=720.0, depth_mm=560.0)
    module2 = ModuleDef(name="M_2", width_mm=600.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM3",
        name="Komplet Kolejnosc",
        wall_name="Sciana Kolejnosc",
        width_mm=3200.0,
        height_mm=2500.0,
        items=[
            AssemblyModuleItemDef(source_name="M_1", instance_name="M_1_1", offset_mm=0.0, module=module1),
            AssemblyModuleItemDef(source_name="M_2", instance_name="M_2_1", offset_ref_mode="previous_module", offset_mm=40.0, module=module2),
        ],
    )
    wall = WallLayoutDef(name="Sciana Kolejnosc", wall_a_width_mm=3200.0, room_height_mm=2500.0)
    wall_store = WallStoreJson()
    assembly_store = AssemblyStoreJson()
    wall_store.overwrite(wall)
    assembly_store.overwrite(assembly)

    tab = TabPlan()
    tab._on_scene_module_clicked(tab._resolved_items[1])
    tab._move_selected_in_order(-1)

    ordered_labels = [str(row.get("display_label", "")) for row in tab._sorted_payload_rows()]
    assert ordered_labels[0] == "M_2"
    assert ordered_labels[1] == "M_1"

    tab._align_selected_to_start()
    selected_row = tab._selected_payload_row()
    assert selected_row is not None
    assert float(selected_row.get("pos_x", -1.0)) == 0.0

    tab._align_selected_to_end()
    selected_row = tab._selected_payload_row()
    assert selected_row is not None
    assert float(selected_row.get("pos_x", -1.0)) == 2600.0


def test_tab_plan_workspace_shell_phase3_layout_warnings(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module1 = ModuleDef(name="M_WARN_1", width_mm=900.0, height_mm=720.0, depth_mm=560.0)
    module2 = ModuleDef(name="M_WARN_2", width_mm=900.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM4",
        name="Komplet Warning",
        wall_name="Sciana Warning",
        width_mm=2800.0,
        height_mm=2500.0,
        items=[
            AssemblyModuleItemDef(source_name="M_WARN_1", instance_name="M_WARN_1_1", offset_mm=0.0, module=module1),
            AssemblyModuleItemDef(source_name="M_WARN_2", instance_name="M_WARN_2_1", offset_ref_mode="wall_left", offset_mm=400.0, module=module2),
        ],
    )
    wall = WallLayoutDef(
        name="Sciana Warning",
        wall_a_width_mm=2800.0,
        room_height_mm=2500.0,
        obstacles=[
            WallObstacleDef(
                kind="window",
                name="Kolizja",
                x_mm=100.0,
                bottom_offset_mm=100.0,
                width_mm=1000.0,
                height_mm=900.0,
            )
        ],
    )
    wall_store = WallStoreJson()
    assembly_store = AssemblyStoreJson()
    wall_store.overwrite(wall)
    assembly_store.overwrite(assembly)

    tab = TabPlan()
    rows = tab._sorted_payload_rows()
    assert len(rows) == 2
    assert "module_overlap" in list(rows[0].get("warning_flags", []))
    assert "obstacle_intersection_window" in list(rows[0].get("warning_flags", []))

    tab._on_scene_module_clicked(tab._resolved_items[1])
    selected_row = tab._selected_payload_row()
    assert selected_row is not None
    selected_row["pos_x"] = 2500.0
    tab._apply_layout_state_change()
    selected_row = tab._selected_payload_row()
    assert selected_row is not None
    assert "out_of_wall_right" in list(selected_row.get("warning_flags", []))
    assert int(tab._layout_summary.get("warning_count", 0)) >= 1


def test_tab_plan_workspace_shell_phase3_normalize_layout(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module1 = ModuleDef(name="M_N1", width_mm=700.0, height_mm=720.0, depth_mm=560.0)
    module2 = ModuleDef(name="M_N2", width_mm=700.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM5",
        name="Komplet Normalize",
        wall_name="Sciana Normalize",
        width_mm=3200.0,
        height_mm=2500.0,
        items=[
            AssemblyModuleItemDef(source_name="M_N1", instance_name="M_N1_1", offset_mm=0.0, module=module1),
            AssemblyModuleItemDef(source_name="M_N2", instance_name="M_N2_1", offset_ref_mode="previous_module", offset_mm=20.0, module=module2),
        ],
    )
    wall = WallLayoutDef(name="Sciana Normalize", wall_a_width_mm=3200.0, room_height_mm=2500.0)
    wall_store = WallStoreJson()
    assembly_store = AssemblyStoreJson()
    wall_store.overwrite(wall)
    assembly_store.overwrite(assembly)

    tab = TabPlan()
    rows = tab._sorted_payload_rows()
    rows[0]["sequence_index"] = 10
    rows[1]["sequence_index"] = 0
    tab._apply_layout_state_change()
    rows_after_break = tab._sorted_payload_rows()
    assert "invalid_layout_order" in list(rows_after_break[0].get("warning_flags", []))

    tab._normalize_layout_positions()
    rows_after_norm = tab._sorted_payload_rows()
    assert int(rows_after_norm[0].get("sequence_index", -1)) == 0
    assert int(rows_after_norm[1].get("sequence_index", -1)) == 1
    assert float(rows_after_norm[0].get("pos_x", -1.0)) == 0.0
    assert float(rows_after_norm[1].get("pos_x", -1.0)) == 700.0
    assert "invalid_layout_order" not in list(rows_after_norm[0].get("warning_flags", []))


def test_tab_plan_workspace_shell_phase3_manual_position_and_spacing(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module = ModuleDef(name="M_MANUAL", width_mm=650.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM6",
        name="Komplet Manual",
        wall_name="Sciana Manual",
        width_mm=3200.0,
        height_mm=2500.0,
        items=[AssemblyModuleItemDef(source_name="M_MANUAL", instance_name="M_MANUAL_1", offset_mm=0.0, module=module)],
    )
    wall = WallLayoutDef(name="Sciana Manual", wall_a_width_mm=3200.0, room_height_mm=2500.0)
    wall_store = WallStoreJson()
    assembly_store = AssemblyStoreJson()
    wall_store.overwrite(wall)
    assembly_store.overwrite(assembly)

    tab = TabPlan()
    assert tab._selected_item is not None
    tab.sp_pos_x.setValue(123.0)
    tab.sp_spacing_after.setValue(45.0)
    tab._apply_selected_manual_position_and_spacing()

    row = tab._selected_payload_row()
    assert row is not None
    assert float(row.get("pos_x", -1.0)) == 123.0
    assert float(row.get("spacing_after_mm", -1.0)) == 45.0


def test_tab_plan_workspace_shell_phase4_select_obstacle_updates_sciana_context(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    wall = WallLayoutDef(
        name="Sciana O1",
        wall_a_width_mm=3000.0,
        room_height_mm=2500.0,
        obstacles=[WallObstacleDef(kind="door", name="Drzwi A", x_mm=400.0, bottom_offset_mm=0.0, width_mm=900.0, height_mm=2100.0)],
    )
    WallStoreJson().overwrite(wall)

    tab = TabPlan()
    tab.cb_wall.setCurrentIndex(1)
    tab._reload_context()
    assert len(tab._obstacle_scene_payload) == 1
    obstacle_id = str(tab._obstacle_scene_payload[0].get("obstacle_id", ""))
    tab._on_scene_obstacle_clicked(obstacle_id)
    assert tab._selected_obstacle_id == obstacle_id
    assert "Typ: door" in tab.lbl_obstacle_context.text()
    assert "Drzwi A" in tab.lbl_obstacle_context.text()
    assert "Severity: none" in tab.lbl_obstacle_context.text()
    assert "Moduly w kolizji" in tab.lbl_obstacle_context.text()


def test_tab_plan_workspace_shell_phase4_add_edit_delete_obstacle(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    wall = WallLayoutDef(name="Sciana O2", wall_a_width_mm=3200.0, room_height_mm=2600.0)
    WallStoreJson().overwrite(wall)

    tab = TabPlan()
    tab.cb_wall.setCurrentIndex(1)
    tab._reload_context()

    tab.cb_obstacle_type.setCurrentText("window")
    tab.ed_obstacle_label.setText("Okno 1")
    tab.sp_obstacle_x.setValue(300.0)
    tab.sp_obstacle_y.setValue(600.0)
    tab.sp_obstacle_w.setValue(1200.0)
    tab.sp_obstacle_h.setValue(1000.0)
    tab._on_obstacle_add()
    assert len(tab._obstacle_scene_payload) == 1

    tab._selected_obstacle_id = str(tab._obstacle_scene_payload[0].get("obstacle_id", ""))
    tab._sync_obstacle_payload_selection()
    tab._refresh_obstacle_context_ui()
    tab.ed_obstacle_label.setText("Okno 1B")
    tab.sp_obstacle_w.setValue(1100.0)
    tab._on_obstacle_update()
    assert len(tab._obstacle_scene_payload) == 1
    assert "Okno 1B" in str(tab._obstacle_scene_payload[0].get("label", ""))

    tab._selected_obstacle_id = str(tab._obstacle_scene_payload[0].get("obstacle_id", ""))
    tab._sync_obstacle_payload_selection()
    tab._refresh_obstacle_context_ui()
    tab._on_obstacle_delete()
    assert len(tab._obstacle_scene_payload) == 0


def test_tab_plan_workspace_shell_phase4_obstacle_specific_and_out_of_wall_warnings(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module = ModuleDef(name="M_O_WARN", width_mm=1000.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM7",
        name="Komplet OWarn",
        wall_name="Sciana OWarn",
        width_mm=2600.0,
        height_mm=2400.0,
        items=[AssemblyModuleItemDef(source_name="M_O_WARN", instance_name="M_O_WARN_1", offset_mm=100.0, module=module)],
    )
    wall = WallLayoutDef(
        name="Sciana OWarn",
        wall_a_width_mm=2600.0,
        room_height_mm=2400.0,
        obstacles=[
            WallObstacleDef(kind="door", name="Drzwi", x_mm=0.0, bottom_offset_mm=0.0, width_mm=1000.0, height_mm=2100.0),
            WallObstacleDef(kind="column", name="Slup", x_mm=2550.0, bottom_offset_mm=0.0, width_mm=200.0, height_mm=2400.0),
        ],
    )
    WallStoreJson().overwrite(wall)
    AssemblyStoreJson().overwrite(assembly)

    tab = TabPlan()
    rows = tab._sorted_payload_rows()
    assert len(rows) == 1
    assert "obstacle_intersection_door" in list(rows[0].get("warning_flags", []))
    obstacle_warnings = list(rows[0].get("obstacle_warnings", []))
    assert len(obstacle_warnings) >= 1
    assert str(obstacle_warnings[0].get("warning_type", "")) == "obstacle_intersection_door"
    assert str(obstacle_warnings[0].get("obstacle_type", "")) == "door"
    assert str(obstacle_warnings[0].get("obstacle_id", "")).startswith("Sciana OWarn:")
    assert tab._module_warning_severity(rows[0]) == "high"
    obstacle_rows = tab._obstacle_scene_payload
    assert any("obstacle_out_of_wall" in list(row.get("warning_flags", [])) for row in obstacle_rows)
    assert any(tab._obstacle_warning_severity(row) == "high" for row in obstacle_rows)
    door_rows = [row for row in obstacle_rows if str(row.get("obstacle_type", "")) == "door"]
    assert len(door_rows) == 1
    assert tab._obstacle_warning_severity(door_rows[0]) == "medium"
    assert int(door_rows[0].get("intersecting_module_count", 0)) >= 1
    assert len(list(door_rows[0].get("intersecting_module_ids", []))) >= 1
    assert int(tab._layout_summary.get("module_high_warning_count", 0)) >= 1
    assert int(tab._layout_summary.get("obstacle_high_warning_count", 0)) >= 1
    assert int(tab._layout_summary.get("obstacle_medium_warning_count", 0)) >= 1
    assert int(tab._layout_summary.get("obstacle_conflict_pairs_count", 0)) >= 1
    assert int(dict(tab._layout_summary.get("obstacle_conflicts_by_type", {}) or {}).get("door", 0)) >= 1


def test_tab_plan_workspace_shell_phase4_overlapping_obstacles_warning(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    wall = WallLayoutDef(
        name="Sciana OOverlap",
        wall_a_width_mm=3000.0,
        room_height_mm=2500.0,
        obstacles=[
            WallObstacleDef(kind="column", name="Slup 1", x_mm=300.0, bottom_offset_mm=0.0, width_mm=500.0, height_mm=2400.0),
            WallObstacleDef(kind="column", name="Slup 2", x_mm=600.0, bottom_offset_mm=0.0, width_mm=500.0, height_mm=2400.0),
        ],
    )
    WallStoreJson().overwrite(wall)

    tab = TabPlan()
    tab.cb_wall.setCurrentIndex(1)
    tab._reload_context()
    assert len(tab._obstacle_scene_payload) == 2
    assert all("overlapping_obstacles" in list(row.get("warning_flags", [])) for row in tab._obstacle_scene_payload)
    assert int(tab._layout_summary.get("overlapping_obstacle_count", 0)) == 2


def test_tab_plan_workspace_shell_phase4_obstacle_filter_conflict_only(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module = ModuleDef(name="M_FILTER", width_mm=1000.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM15",
        name="Komplet Filter",
        wall_name="Sciana Filter",
        width_mm=3200.0,
        height_mm=2500.0,
        items=[AssemblyModuleItemDef(source_name="M_FILTER", instance_name="M_FILTER_1", offset_mm=200.0, module=module)],
    )
    wall = WallLayoutDef(
        name="Sciana Filter",
        wall_a_width_mm=3200.0,
        room_height_mm=2500.0,
        obstacles=[
            WallObstacleDef(kind="window", name="Okno Bez Kolizji", x_mm=2600.0, bottom_offset_mm=0.0, width_mm=400.0, height_mm=800.0),
            WallObstacleDef(kind="door", name="Drzwi Kolizja", x_mm=200.0, bottom_offset_mm=0.0, width_mm=900.0, height_mm=2100.0),
        ],
    )
    WallStoreJson().overwrite(wall)
    AssemblyStoreJson().overwrite(assembly)

    tab = TabPlan()
    assert len(tab._obstacle_scene_payload) == 2
    assert tab.lst_obstacles.count() == 2

    idx = tab.cb_obstacle_filter.findData("conflict")
    tab.cb_obstacle_filter.setCurrentIndex(max(0, idx))
    assert tab.lst_obstacles.count() == 1
    assert "Drzwi Kolizja" in tab.lst_obstacles.item(0).text()

    idx_all = tab.cb_obstacle_filter.findData("all")
    tab.cb_obstacle_filter.setCurrentIndex(max(0, idx_all))
    assert tab.lst_obstacles.count() == 2


def test_tab_plan_workspace_shell_phase4_obstacle_filter_high_only(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module = ModuleDef(name="M_FILTER_H", width_mm=1000.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM16",
        name="Komplet Filter H",
        wall_name="Sciana Filter H",
        width_mm=3200.0,
        height_mm=2500.0,
        items=[AssemblyModuleItemDef(source_name="M_FILTER_H", instance_name="M_FILTER_H_1", offset_mm=200.0, module=module)],
    )
    wall = WallLayoutDef(
        name="Sciana Filter H",
        wall_a_width_mm=3200.0,
        room_height_mm=2500.0,
        obstacles=[
            WallObstacleDef(kind="window", name="Okno Bez Kolizji", x_mm=2600.0, bottom_offset_mm=0.0, width_mm=400.0, height_mm=800.0),
            WallObstacleDef(kind="door", name="Drzwi Medium", x_mm=200.0, bottom_offset_mm=0.0, width_mm=900.0, height_mm=2100.0),
            WallObstacleDef(kind="column", name="Slup High", x_mm=3150.0, bottom_offset_mm=0.0, width_mm=200.0, height_mm=2400.0),
        ],
    )
    WallStoreJson().overwrite(wall)
    AssemblyStoreJson().overwrite(assembly)

    tab = TabPlan()
    assert len(tab._obstacle_scene_payload) == 3
    assert tab.lst_obstacles.count() == 3

    idx = tab.cb_obstacle_filter.findData("high")
    tab.cb_obstacle_filter.setCurrentIndex(max(0, idx))
    assert tab.lst_obstacles.count() == 1
    assert "Slup High" in tab.lst_obstacles.item(0).text()


def test_tab_plan_workspace_shell_phase4_obstacle_list_prioritizes_high(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module = ModuleDef(name="M_SORT", width_mm=1000.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM17",
        name="Komplet Sort",
        wall_name="Sciana Sort",
        width_mm=3200.0,
        height_mm=2500.0,
        items=[AssemblyModuleItemDef(source_name="M_SORT", instance_name="M_SORT_1", offset_mm=200.0, module=module)],
    )
    wall = WallLayoutDef(
        name="Sciana Sort",
        wall_a_width_mm=3200.0,
        room_height_mm=2500.0,
        obstacles=[
            WallObstacleDef(kind="window", name="A Bez Kolizji", x_mm=2600.0, bottom_offset_mm=0.0, width_mm=400.0, height_mm=800.0),
            WallObstacleDef(kind="door", name="B Medium", x_mm=200.0, bottom_offset_mm=0.0, width_mm=900.0, height_mm=2100.0),
            WallObstacleDef(kind="column", name="C High", x_mm=3150.0, bottom_offset_mm=0.0, width_mm=200.0, height_mm=2400.0),
        ],
    )
    WallStoreJson().overwrite(wall)
    AssemblyStoreJson().overwrite(assembly)

    tab = TabPlan()
    idx_all = tab.cb_obstacle_filter.findData("all")
    tab.cb_obstacle_filter.setCurrentIndex(max(0, idx_all))
    assert tab.lst_obstacles.count() == 3
    first = tab.lst_obstacles.item(0).text()
    assert first.startswith("[H]")
    assert "C High" in first


def test_tab_plan_workspace_shell_phase4_filter_clears_hidden_obstacle_selection(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module = ModuleDef(name="M_FILTER_CLR", width_mm=1000.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM18",
        name="Komplet Filter Clear",
        wall_name="Sciana Filter Clear",
        width_mm=3200.0,
        height_mm=2500.0,
        items=[AssemblyModuleItemDef(source_name="M_FILTER_CLR", instance_name="M_FILTER_CLR_1", offset_mm=200.0, module=module)],
    )
    wall = WallLayoutDef(
        name="Sciana Filter Clear",
        wall_a_width_mm=3200.0,
        room_height_mm=2500.0,
        obstacles=[
            WallObstacleDef(kind="door", name="B Medium", x_mm=200.0, bottom_offset_mm=0.0, width_mm=900.0, height_mm=2100.0),
            WallObstacleDef(kind="column", name="C High", x_mm=3150.0, bottom_offset_mm=0.0, width_mm=200.0, height_mm=2400.0),
        ],
    )
    WallStoreJson().overwrite(wall)
    AssemblyStoreJson().overwrite(assembly)

    tab = TabPlan()
    medium = next(row for row in tab._obstacle_scene_payload if str(row.get("label", "")) == "B Medium")
    tab._on_scene_obstacle_clicked(str(medium.get("obstacle_id", "")))
    assert tab._selected_obstacle_id == str(medium.get("obstacle_id", ""))

    idx = tab.cb_obstacle_filter.findData("high")
    tab.cb_obstacle_filter.setCurrentIndex(max(0, idx))

    assert tab._selected_obstacle_id == ""
    assert tab.lst_obstacles.count() == 1
    assert "Przeszkoda: [brak]" in tab.lbl_obstacle_context.text()
    assert not tab.btn_obstacle_update.isEnabled()


def test_tab_plan_workspace_shell_phase4_utility_warning_zone_affects_conflict(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module = ModuleDef(name="M_ZONE", width_mm=500.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM11",
        name="Komplet Zone",
        wall_name="Sciana Zone",
        width_mm=3000.0,
        height_mm=2500.0,
        items=[AssemblyModuleItemDef(source_name="M_ZONE", instance_name="M_ZONE_1", offset_mm=1000.0, module=module)],
    )
    wall = WallLayoutDef(
        name="Sciana Zone",
        wall_a_width_mm=3000.0,
        room_height_mm=2500.0,
        obstacles=[
            WallObstacleDef(
                kind="utility",
                name="Punkt Utility",
                x_mm=1700.0,
                bottom_offset_mm=0.0,
                width_mm=50.0,
                height_mm=2400.0,
                depth_mm=300.0,  # warning_zone_mm
            )
        ],
    )
    WallStoreJson().overwrite(wall)
    AssemblyStoreJson().overwrite(assembly)

    tab = TabPlan()
    rows = tab._sorted_payload_rows()
    assert len(rows) == 1
    assert "obstacle_intersection_utility" in list(rows[0].get("warning_flags", []))
    assert len(list(rows[0].get("obstacle_warnings", []))) >= 1


def test_tab_plan_workspace_shell_phase4_module_selection_stays_stable_after_obstacle_selection(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module = ModuleDef(name="M_SEL", width_mm=800.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM8",
        name="Komplet Select",
        wall_name="Sciana Select",
        width_mm=3000.0,
        height_mm=2500.0,
        items=[AssemblyModuleItemDef(source_name="M_SEL", instance_name="M_SEL_1", offset_mm=100.0, module=module)],
    )
    wall = WallLayoutDef(
        name="Sciana Select",
        wall_a_width_mm=3000.0,
        room_height_mm=2500.0,
        obstacles=[WallObstacleDef(kind="window", name="Okno Select", x_mm=1200.0, bottom_offset_mm=900.0, width_mm=1000.0, height_mm=900.0)],
    )
    WallStoreJson().overwrite(wall)
    AssemblyStoreJson().overwrite(assembly)

    tab = TabPlan()
    assert len(tab._resolved_items) == 1
    assert len(tab._obstacle_scene_payload) == 1

    obstacle_id = str(tab._obstacle_scene_payload[0].get("obstacle_id", ""))
    tab._on_scene_obstacle_clicked(obstacle_id)
    assert tab._selected_obstacle_id == obstacle_id
    assert tab._selected_item is None

    tab._on_scene_module_clicked(tab._resolved_items[0])
    assert tab._selected_obstacle_id == ""
    assert tab._selected_item is not None
    assert str(getattr(tab._selected_item.module, "name", "") or "") == "M_SEL"
    assert "Nazwa: M_SEL" in tab.lbl_module_summary.text()


def test_tab_plan_workspace_shell_phase4_focus_conflicting_obstacle_from_module(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module = ModuleDef(name="M_FOCUS", width_mm=1000.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM9",
        name="Komplet Focus",
        wall_name="Sciana Focus",
        width_mm=2800.0,
        height_mm=2500.0,
        items=[AssemblyModuleItemDef(source_name="M_FOCUS", instance_name="M_FOCUS_1", offset_mm=0.0, module=module)],
    )
    wall = WallLayoutDef(
        name="Sciana Focus",
        wall_a_width_mm=2800.0,
        room_height_mm=2500.0,
        obstacles=[WallObstacleDef(kind="door", name="Drzwi Focus", x_mm=0.0, bottom_offset_mm=0.0, width_mm=1000.0, height_mm=2100.0)],
    )
    WallStoreJson().overwrite(wall)
    AssemblyStoreJson().overwrite(assembly)

    tab = TabPlan()
    assert tab._selected_item is not None
    row = tab._selected_payload_row()
    assert row is not None
    assert len(list(row.get("obstacle_warnings", []))) > 0
    obstacle_id = str(row.get("obstacle_warnings", [])[0].get("obstacle_id", "") or "")
    assert obstacle_id != ""

    tab._focus_first_obstacle_conflict()
    assert tab._mode_key == "sciana"
    assert tab._selected_obstacle_id == obstacle_id
    assert tab._selected_item is None
    assert "Drzwi Focus" in tab.lbl_obstacle_context.text()


def test_tab_plan_workspace_shell_phase4_cycles_conflicting_obstacles_from_module(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module = ModuleDef(name="M_OBS_CYCLE", width_mm=1800.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM13",
        name="Komplet Obs Cycle",
        wall_name="Sciana Obs Cycle",
        width_mm=3200.0,
        height_mm=2500.0,
        items=[AssemblyModuleItemDef(source_name="M_OBS_CYCLE", instance_name="M_OBS_CYCLE_1", offset_mm=200.0, module=module)],
    )
    wall = WallLayoutDef(
        name="Sciana Obs Cycle",
        wall_a_width_mm=3200.0,
        room_height_mm=2500.0,
        obstacles=[
            WallObstacleDef(kind="door", name="Drzwi Cycle 1", x_mm=200.0, bottom_offset_mm=0.0, width_mm=800.0, height_mm=2100.0),
            WallObstacleDef(kind="column", name="Slup Cycle 2", x_mm=1200.0, bottom_offset_mm=0.0, width_mm=400.0, height_mm=2400.0),
        ],
    )
    WallStoreJson().overwrite(wall)
    AssemblyStoreJson().overwrite(assembly)

    tab = TabPlan()
    assert tab._selected_item is not None
    row = tab._selected_payload_row()
    assert row is not None
    assert len(list(row.get("obstacle_warnings", []))) >= 2

    tab._focus_first_obstacle_conflict()
    first_obstacle = str(tab._selected_obstacle_id or "")
    assert first_obstacle != ""
    assert tab._mode_key == "sciana"

    tab._on_scene_module_clicked(tab._resolved_items[0])
    assert "Konflikty typy: " in tab.lbl_module_summary.text()
    assert "column:1" in tab.lbl_module_summary.text()
    assert "door:1" in tab.lbl_module_summary.text()
    tab._focus_first_obstacle_conflict()
    second_obstacle = str(tab._selected_obstacle_id or "")
    assert second_obstacle != ""
    assert second_obstacle != first_obstacle


def test_tab_plan_workspace_shell_phase4_keeps_unique_obstacle_warnings_after_recompute(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module = ModuleDef(name="M_OBS_UNIQ", width_mm=1800.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM14",
        name="Komplet Obs Uniq",
        wall_name="Sciana Obs Uniq",
        width_mm=3200.0,
        height_mm=2500.0,
        items=[AssemblyModuleItemDef(source_name="M_OBS_UNIQ", instance_name="M_OBS_UNIQ_1", offset_mm=200.0, module=module)],
    )
    wall = WallLayoutDef(
        name="Sciana Obs Uniq",
        wall_a_width_mm=3200.0,
        room_height_mm=2500.0,
        obstacles=[
            WallObstacleDef(kind="door", name="Drzwi Uniq 1", x_mm=200.0, bottom_offset_mm=0.0, width_mm=800.0, height_mm=2100.0),
            WallObstacleDef(kind="column", name="Slup Uniq 2", x_mm=1200.0, bottom_offset_mm=0.0, width_mm=400.0, height_mm=2400.0),
        ],
    )
    WallStoreJson().overwrite(wall)
    AssemblyStoreJson().overwrite(assembly)

    tab = TabPlan()
    row = tab._selected_payload_row()
    assert row is not None
    first_ids = [str(item.get("obstacle_id", "") or "") for item in list(row.get("obstacle_warnings", []))]
    assert len(first_ids) >= 2
    assert len(first_ids) == len(set(first_ids))

    tab._reload_context()
    row_after = tab._selected_payload_row()
    assert row_after is not None
    second_ids = [str(item.get("obstacle_id", "") or "") for item in list(row_after.get("obstacle_warnings", []))]
    assert len(second_ids) >= 2
    assert len(second_ids) == len(set(second_ids))


def test_tab_plan_workspace_shell_phase4_focus_conflicting_module_from_obstacle(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module = ModuleDef(name="M_BACK", width_mm=1000.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM10",
        name="Komplet Back",
        wall_name="Sciana Back",
        width_mm=2800.0,
        height_mm=2500.0,
        items=[AssemblyModuleItemDef(source_name="M_BACK", instance_name="M_BACK_1", offset_mm=0.0, module=module)],
    )
    wall = WallLayoutDef(
        name="Sciana Back",
        wall_a_width_mm=2800.0,
        room_height_mm=2500.0,
        obstacles=[WallObstacleDef(kind="door", name="Drzwi Back", x_mm=0.0, bottom_offset_mm=0.0, width_mm=1000.0, height_mm=2100.0)],
    )
    WallStoreJson().overwrite(wall)
    AssemblyStoreJson().overwrite(assembly)

    tab = TabPlan()
    obstacle_id = str(tab._obstacle_scene_payload[0].get("obstacle_id", ""))
    tab._on_scene_obstacle_clicked(obstacle_id)
    assert tab._selected_obstacle_id == obstacle_id
    assert tab._selected_item is None
    assert "Severity: medium" in tab.lbl_obstacle_context.text()
    assert "Moduly: M_BACK" in tab.lbl_obstacle_context.text()

    tab._focus_first_module_conflict_from_obstacle()
    assert tab._mode_key == "modul"
    assert tab._selected_obstacle_id == ""
    assert tab._selected_item is not None
    assert str(getattr(tab._selected_item.module, "name", "") or "") == "M_BACK"


def test_tab_plan_workspace_shell_phase4_cycles_conflicting_modules_from_obstacle(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    module1 = ModuleDef(name="M_CYCLE_1", width_mm=900.0, height_mm=720.0, depth_mm=560.0)
    module2 = ModuleDef(name="M_CYCLE_2", width_mm=900.0, height_mm=720.0, depth_mm=560.0)
    assembly = FurnitureAssemblyDef(
        assembly_id="ASM12",
        name="Komplet Cycle",
        wall_name="Sciana Cycle",
        width_mm=3200.0,
        height_mm=2500.0,
        items=[
            AssemblyModuleItemDef(source_name="M_CYCLE_1", instance_name="M_CYCLE_1_1", offset_mm=0.0, module=module1),
            AssemblyModuleItemDef(source_name="M_CYCLE_2", instance_name="M_CYCLE_2_1", offset_ref_mode="wall_left", offset_mm=950.0, module=module2),
        ],
    )
    wall = WallLayoutDef(
        name="Sciana Cycle",
        wall_a_width_mm=3200.0,
        room_height_mm=2500.0,
        obstacles=[WallObstacleDef(kind="door", name="Drzwi Cycle", x_mm=0.0, bottom_offset_mm=0.0, width_mm=1900.0, height_mm=2100.0)],
    )
    WallStoreJson().overwrite(wall)
    AssemblyStoreJson().overwrite(assembly)

    tab = TabPlan()
    obstacle_id = str(tab._obstacle_scene_payload[0].get("obstacle_id", ""))
    tab._on_scene_obstacle_clicked(obstacle_id)

    tab._focus_first_module_conflict_from_obstacle()
    assert tab._selected_item is not None
    first_name = str(getattr(tab._selected_item.module, "name", "") or "")
    assert first_name in {"M_CYCLE_1", "M_CYCLE_2"}

    tab._selected_obstacle_id = obstacle_id
    tab._on_scene_obstacle_clicked(obstacle_id)
    tab._focus_first_module_conflict_from_obstacle()
    assert tab._selected_item is not None
    second_name = str(getattr(tab._selected_item.module, "name", "") or "")
    assert second_name in {"M_CYCLE_1", "M_CYCLE_2"}
    assert second_name != first_name


def test_tab_plan_workspace_shell_phase4_clamp_obstacle_to_wall(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    wall = WallLayoutDef(
        name="Sciana Clamp",
        wall_a_width_mm=3000.0,
        room_height_mm=2500.0,
        obstacles=[WallObstacleDef(kind="column", name="Slup Clamp", x_mm=2800.0, bottom_offset_mm=0.0, width_mm=500.0, height_mm=2400.0)],
    )
    WallStoreJson().overwrite(wall)

    tab = TabPlan()
    tab.cb_wall.setCurrentIndex(1)
    tab._reload_context()
    assert len(tab._obstacle_scene_payload) == 1
    obstacle = tab._obstacle_scene_payload[0]
    assert "obstacle_out_of_wall" in list(obstacle.get("warning_flags", []))
    assert int(tab._layout_summary.get("obstacle_out_of_wall_count", 0)) == 1

    obstacle_id = str(obstacle.get("obstacle_id", ""))
    tab._on_scene_obstacle_clicked(obstacle_id)
    tab._on_obstacle_clamp_to_wall()

    assert len(tab._obstacle_scene_payload) == 1
    obstacle_after = tab._obstacle_scene_payload[0]
    assert "obstacle_out_of_wall" not in list(obstacle_after.get("warning_flags", []))
    assert float(obstacle_after.get("pos_x_mm", -1.0)) <= 2500.0
    assert int(tab._layout_summary.get("obstacle_out_of_wall_count", 0)) == 0


def test_tab_plan_workspace_shell_phase4_invalid_size_obstacle_count(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    wall = WallLayoutDef(
        name="Sciana Invalid Size",
        wall_a_width_mm=3000.0,
        room_height_mm=2500.0,
        obstacles=[],
    )
    WallStoreJson().overwrite(wall)

    tab = TabPlan()
    tab.cb_wall.setCurrentIndex(1)
    tab._reload_context()
    monkeypatch.setattr(
        tab,
        "_build_obstacle_scene_payload",
        lambda _wall: [
            {
                "obstacle_id": "Sciana Invalid Size:0",
                "obstacle_index": 0,
                "wall_name": "Sciana Invalid Size",
                "obstacle_type": "utility",
                "pos_x_mm": 500.0,
                "pos_y_mm": 500.0,
                "width_mm": 1.0,
                "height_mm": 1.0,
                "warning_zone_mm": 0.0,
                "label": "Punkt Invalid",
                "warning_flags": ["obstacle_invalid_size"],
                "intersecting_module_ids": [],
                "intersecting_module_count": 0,
                "is_selected": False,
            }
        ],
    )
    tab._recompute_layout_warnings_and_summary()
    assert int(tab._layout_summary.get("obstacle_invalid_size_count", 0)) == 1


def test_tab_plan_workspace_shell_phase4_obstacle_type_presets(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    wall = WallLayoutDef(name="Sciana Preset", wall_a_width_mm=3200.0, room_height_mm=2600.0)
    WallStoreJson().overwrite(wall)

    tab = TabPlan()
    tab.cb_wall.setCurrentIndex(1)
    tab._reload_context()
    tab._on_obstacle_new()

    idx_utility = tab.cb_obstacle_type.findData("utility")
    tab.cb_obstacle_type.setCurrentIndex(idx_utility)
    assert float(tab.sp_obstacle_w.value()) == 150.0
    assert float(tab.sp_obstacle_h.value()) == 300.0
    assert float(tab.sp_obstacle_zone.value()) == 300.0

    idx_door = tab.cb_obstacle_type.findData("door")
    tab.cb_obstacle_type.setCurrentIndex(idx_door)
    assert float(tab.sp_obstacle_w.value()) == 900.0
    assert float(tab.sp_obstacle_h.value()) == 2100.0
    assert float(tab.sp_obstacle_zone.value()) == 0.0
