from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from core.constructor3d_export import Constructor3DModule, save_model_list_ini
from core.constructor3d_project import import_project_modules


class CabinetItem(QtWidgets.QGraphicsRectItem):
    def __init__(self, page: "ScianaPage", cabinet_id: int):
        super().__init__()
        self.page = page
        self.cabinet_id = cabinet_id
        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsMovable
            | QtWidgets.QGraphicsItem.ItemIsSelectable
            | QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            self.page._item_moved(self.cabinet_id, value)
        if change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged and bool(value):
            self.page._select_cabinet(self.cabinet_id, from_scene=True)
        return super().itemChange(change, value)


class ScianaPage(QtWidgets.QWidget):
    """
    Plansza sciany: ustawianie szafek i eksport listy modeli do 3D-Constructor.
    """

    def __init__(self, ctx=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._cabinets: list[dict] = []
        self._items: dict[int, CabinetItem] = {}
        self._syncing = False
        self._next_id = 1

        self.scene = QtWidgets.QGraphicsScene(self)
        self.view = QtWidgets.QGraphicsView(self.scene)
        self.view.setRenderHints(QtGui.QPainter.Antialiasing)
        self.view.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.view.setMinimumHeight(420)

        self.tbl = QtWidgets.QTableWidget(0, 10)
        self.tbl.setHorizontalHeaderLabels(["#", "Szyfr", "Nazwa", "Dlug.", "Szer.", "Wys.", "X", "Y", "Z", "Kat"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.btnAdd = QtWidgets.QPushButton("Dodaj szafke")
        self.btnImport = QtWidgets.QPushButton("Import .project")
        self.btnDel = QtWidgets.QPushButton("Usun")
        self.btnSample = QtWidgets.QPushButton("Przyklad")
        self.btnExport = QtWidgets.QPushButton("Eksport do 3D-Constructor")
        self.lblStatus = QtWidgets.QLabel("")
        self.lblStatus.setWordWrap(True)

        top = QtWidgets.QHBoxLayout()
        top.addWidget(self.btnAdd)
        top.addWidget(self.btnImport)
        top.addWidget(self.btnDel)
        top.addWidget(self.btnSample)
        top.addStretch(1)
        top.addWidget(self.btnExport)

        split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        split.addWidget(self.view)
        split.addWidget(self.tbl)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        split.setSizes([560, 230])

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.addLayout(top)
        root.addWidget(split, 1)
        root.addWidget(self.lblStatus)

        self.btnAdd.clicked.connect(self.add_cabinet)
        self.btnImport.clicked.connect(self.import_project)
        self.btnDel.clicked.connect(self.delete_selected)
        self.btnSample.clicked.connect(self.add_sample)
        self.btnExport.clicked.connect(self.export_to_3dc)
        self.tbl.itemChanged.connect(self._table_changed)
        self.tbl.itemSelectionChanged.connect(self._table_selection_changed)

        self._draw_wall()
        self.add_sample()

    def _draw_wall(self):
        self.scene.clear()
        self._items.clear()
        pen = QtGui.QPen(QtGui.QColor(70, 70, 70), 2)
        brush = QtGui.QBrush(QtGui.QColor(250, 250, 250))
        self.scene.addRect(QtCore.QRectF(0, 0, 3600, 2600), pen, brush)
        for x in range(0, 3601, 300):
            line_pen = QtGui.QPen(QtGui.QColor(225, 225, 225), 1)
            self.scene.addLine(x, 0, x, 2600, line_pen)
        for y in range(0, 2601, 300):
            line_pen = QtGui.QPen(QtGui.QColor(225, 225, 225), 1)
            self.scene.addLine(0, y, 3600, y, line_pen)
        self.scene.setSceneRect(-100, -100, 3800, 2800)
        for cabinet in self._cabinets:
            self._add_scene_item(cabinet)

    def _add_scene_item(self, cabinet: dict):
        scale = 0.5
        item = CabinetItem(self, int(cabinet["id"]))
        w = max(80.0, float(cabinet.get("length", 600)) * scale)
        h = max(80.0, float(cabinet.get("height", 720)) * scale)
        item.setRect(0, 0, w, h)
        item.setPos(float(cabinet.get("x", 0)) * scale, float(cabinet.get("y", 0)) * scale)
        item.setRotation(float(cabinet.get("angle", 0)))
        item.setBrush(QtGui.QBrush(QtGui.QColor(230, 240, 255)))
        item.setPen(QtGui.QPen(QtGui.QColor(35, 95, 170), 2))
        item.setToolTip(str(cabinet.get("code", "")))
        self.scene.addItem(item)

        text = self.scene.addText(str(cabinet.get("code", "")))
        text.setDefaultTextColor(QtGui.QColor(20, 45, 80))
        text.setParentItem(item)
        text.setPos(8, 8)
        self._items[int(cabinet["id"])] = item

    def _new_cabinet(self, code: str, length: float, width: float, height: float, x: float, y: float):
        cabinet = {
            "id": self._next_id,
            "code": code,
            "name": code,
            "length": length,
            "width": width,
            "height": height,
            "x": x,
            "y": y,
            "z": 0.0,
            "angle": 0.0,
            "coordinate_system": -1,
        }
        self._next_id += 1
        self._cabinets.append(cabinet)
        return cabinet

    def add_cabinet(self):
        n = len(self._cabinets) + 1
        cabinet = self._new_cabinet(f"TK_N{n}.000", 600, 560, 825, (n - 1) * 650, 0)
        self._refresh_all()
        self._select_cabinet(int(cabinet["id"]))

    def import_project(self):
        default_dir = Path.home() / "Desktop" / "Do CNC"
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Importuj modul z 3D-Constructor",
            str(default_dir),
            "3D-Constructor Project (*.project *.xml);;Wszystkie pliki (*)",
        )
        if not path:
            return
        self.import_project_path(path)

    def import_project_path(self, path: str | Path):
        imported = import_project_modules(path)
        if not imported:
            self.lblStatus.setText(f"Brak modulow class=1 w pliku: {path}")
            return
        if self._cabinets:
            max_x = max(float(c.get("x", 0)) + float(c.get("length", 0)) for c in self._cabinets)
        else:
            max_x = 0.0
        for offset, module in enumerate(imported):
            cabinet = self._new_cabinet(
                str(module.get("code", "")),
                float(module.get("length", 600) or 600),
                float(module.get("width", 560) or 560),
                float(module.get("height", 720) or 720),
                max_x + 40.0 + float(module.get("x", 0) or 0),
                float(module.get("y", 0) or 0),
            )
            cabinet.update(module)
            cabinet["id"] = self._next_id - 1
        self._refresh_all()
        self.lblStatus.setText(f"Zaimportowano {len(imported)} modul(y) z: {path}")

    def add_sample(self):
        if self._cabinets:
            return
        self._new_cabinet("TK_N1.000", 500, 500, 825, 0, 0)
        self._new_cabinet("TK_N4.000", 300, 500, 825, 520, 0)
        self._new_cabinet("TK_N2.000", 600, 560, 2100, 840, 0)
        self._refresh_all()

    def delete_selected(self):
        row = self.tbl.currentRow()
        if row < 0:
            return
        cabinet_id = int(self.tbl.item(row, 0).text())
        self._cabinets = [c for c in self._cabinets if int(c["id"]) != cabinet_id]
        self._refresh_all()

    def _refresh_all(self):
        self._fill_table()
        self._draw_wall()

    def _fill_table(self):
        self._syncing = True
        self.tbl.setRowCount(0)
        keys = ["id", "code", "name", "length", "width", "height", "x", "y", "z", "angle"]
        for cabinet in self._cabinets:
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            for col, key in enumerate(keys):
                value = cabinet.get(key, "")
                if isinstance(value, float):
                    value = f"{value:g}"
                item = QtWidgets.QTableWidgetItem(str(value))
                if key == "id":
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.tbl.setItem(row, col, item)
        self._syncing = False

    def _table_changed(self, item: QtWidgets.QTableWidgetItem):
        if self._syncing or item is None:
            return
        row = item.row()
        if row < 0 or row >= len(self._cabinets):
            return
        cabinet = self._cabinets[row]
        keys = ["id", "code", "name", "length", "width", "height", "x", "y", "z", "angle"]
        key = keys[item.column()]
        if key == "id":
            return
        text = item.text().strip()
        if key in {"code", "name"}:
            cabinet[key] = text
        else:
            try:
                cabinet[key] = float(text.replace(",", "."))
            except ValueError:
                self._fill_table()
                return
        self._draw_wall()

    def _table_selection_changed(self):
        row = self.tbl.currentRow()
        if row < 0 or row >= len(self._cabinets):
            return
        self._select_cabinet(int(self._cabinets[row]["id"]))

    def _select_cabinet(self, cabinet_id: int, from_scene: bool = False):
        for item_id, item in self._items.items():
            item.setSelected(item_id == cabinet_id)
        if not from_scene:
            return
        for row, cabinet in enumerate(self._cabinets):
            if int(cabinet["id"]) == cabinet_id:
                self.tbl.blockSignals(True)
                self.tbl.selectRow(row)
                self.tbl.blockSignals(False)
                break

    def _item_moved(self, cabinet_id: int, pos: QtCore.QPointF):
        if self._syncing:
            return
        scale = 0.5
        for cabinet in self._cabinets:
            if int(cabinet["id"]) == int(cabinet_id):
                cabinet["x"] = round(float(pos.x()) / scale, 1)
                cabinet["y"] = round(float(pos.y()) / scale, 1)
                break
        self._fill_table()

    def _modules_for_export(self) -> list[Constructor3DModule]:
        modules = []
        for index, cabinet in enumerate(self._cabinets, 1):
            modules.append(
                Constructor3DModule(
                    index=index,
                    code=str(cabinet.get("code", "")),
                    length=float(cabinet.get("length", 0) or 0),
                    width=float(cabinet.get("width", 0) or 0),
                    height=float(cabinet.get("height", 0) or 0),
                    x=float(cabinet.get("x", 0) or 0),
                    y=float(cabinet.get("y", 0) or 0),
                    z=float(cabinet.get("z", 0) or 0),
                    angle=float(cabinet.get("angle", 0) or 0),
                    coordinate_system=int(cabinet.get("coordinate_system", -1) or -1),
                )
            )
        return modules

    def export_to_3dc(self):
        default = Path.home() / "Desktop" / "techmodel_3dc_models.ini"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Zapisz liste modeli 3D-Constructor",
            str(default),
            "3D-Constructor INI (*.ini);;Wszystkie pliki (*)",
        )
        if not path:
            return
        out_path = save_model_list_ini(path, self._modules_for_export())
        self.lblStatus.setText(
            f"Zapisano: {out_path}. W 3D-Constructor wybierz: Projekt -> Przyjmij liste modeli."
        )
