from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class _NodeSpec:
    node_id: str
    title: str
    subtitle: str
    kind: str
    pos: tuple[float, float]
    size: tuple[float, float]
    fill: str
    border: str
    files: tuple[str, ...]
    reads: tuple[str, ...]
    writes: tuple[str, ...]
    note: str = ""


@dataclass(frozen=True)
class _EdgeSpec:
    src: str
    dst: str
    kind: str = "data"


class _FlowNodeItem(QGraphicsRectItem):
    def __init__(self, spec: _NodeSpec, click_cb: Callable[[str], None]) -> None:
        super().__init__(0.0, 0.0, spec.size[0], spec.size[1])
        self.spec = spec
        self._click_cb = click_cb
        self.setBrush(QBrush(QColor(spec.fill)))
        self.setPen(QPen(QColor(spec.border), 2.0))
        self.setToolTip(f"{spec.title}\n{spec.subtitle}")
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)

        accent = QGraphicsRectItem(0.0, 0.0, 8.0, spec.size[1], self)
        accent.setBrush(QBrush(QColor(spec.border)))
        accent.setPen(QPen(Qt.GlobalColor.transparent))

        title = QGraphicsTextItem(spec.title, self)
        title.setDefaultTextColor(QColor("#0f172a"))
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setTextWidth(max(8.0, spec.size[0] - 24.0))
        title.setPos(14.0, 8.0)

        subtitle = QGraphicsTextItem(spec.subtitle, self)
        subtitle.setDefaultTextColor(QColor("#94a3b8"))
        subtitle.setFont(QFont("Segoe UI", 8))
        subtitle.setTextWidth(max(8.0, spec.size[0] - 24.0))
        subtitle.setPos(14.0, 38.0)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self._click_cb(self.spec.node_id)
        super().mousePressEvent(event)


class _FlowEdgeItem(QGraphicsPathItem):
    def __init__(self, src: _FlowNodeItem, dst: _FlowNodeItem, kind: str = "data") -> None:
        super().__init__()
        self.src = src
        self.dst = dst
        self.kind = kind
        self._base_color = QColor("#64748b")
        if kind == "flow":
            self._base_color = QColor("#c2410c")
        elif kind == "return":
            self._base_color = QColor("#2563eb")
        self.setZValue(-10.0)
        self.update_geometry()
        self.set_highlighted(False, False)

    def update_geometry(self) -> None:
        src_rect = self.src.sceneBoundingRect()
        dst_rect = self.dst.sceneBoundingRect()
        src_center = src_rect.center()
        dst_center = dst_rect.center()
        if dst_center.x() >= src_center.x():
            start = QPointF(src_rect.right(), src_center.y())
            end = QPointF(dst_rect.left(), dst_center.y())
        else:
            start = QPointF(src_rect.left(), src_center.y())
            end = QPointF(dst_rect.right(), dst_center.y())
        path = QPainterPath(start)
        mid_x = (start.x() + end.x()) * 0.5
        if abs(end.x() - start.x()) < 140.0:
            path.lineTo(QPointF(mid_x, start.y()))
            path.lineTo(QPointF(mid_x, end.y()))
            path.lineTo(end)
        else:
            path.cubicTo(QPointF(mid_x, start.y()), QPointF(mid_x, end.y()), end)
        self.setPath(path)

    def set_highlighted(self, active: bool, dimmed: bool) -> None:
        color = QColor(self._base_color)
        color.setAlpha(230 if active else 55 if dimmed else 100)
        pen = QPen(color, 3.0 if active else 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        if self.kind == "data":
            pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setOpacity(1.0 if active else 0.35 if dimmed else 0.55)

    def paint(self, painter: QPainter, option, widget=None) -> None:  # type: ignore[override]
        super().paint(painter, option, widget)
        path = self.path()
        if path.isEmpty():
            return
        end = path.pointAtPercent(1.0)
        prev = path.pointAtPercent(max(0.0, 1.0 - 0.015))
        angle = math.atan2(-(end.y() - prev.y()), end.x() - prev.x())
        size = 8.0
        p1 = QPointF(
            end.x() - math.cos(angle + math.pi / 6.0) * size,
            end.y() + math.sin(angle + math.pi / 6.0) * size,
        )
        p2 = QPointF(
            end.x() - math.cos(angle - math.pi / 6.0) * size,
            end.y() + math.sin(angle - math.pi / 6.0) * size,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.pen().color())
        painter.drawPolygon(QPolygonF([end, p1, p2]))


class _StructureCanvas(QGraphicsView):
    def __init__(self, click_cb: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._click_cb = click_cb
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QColor("#fbfcfe"))
        self._nodes: dict[str, _FlowNodeItem] = {}
        self._edges: list[_FlowEdgeItem] = []
        self._base_nodes: list[_NodeSpec] = []
        self._base_edges: list[_EdgeSpec] = []
        self._extra_edges: list[_EdgeSpec] = []
        self._selected = ""
        self._edit_mode = False
        self._drag_source_id = ""
        self._drag_preview: QGraphicsPathItem | None = None
        self.setMouseTracking(True)

    def build(self, nodes: list[_NodeSpec], edges: list[_EdgeSpec]) -> None:
        self._base_nodes = list(nodes)
        self._base_edges = list(edges)
        self._rebuild_scene()

    def set_edit_mode(self, enabled: bool) -> None:
        self._edit_mode = bool(enabled)
        self._cancel_drag_preview()

    def add_user_edge(self, src_id: str, dst_id: str, kind: str = "flow") -> bool:
        src_id = str(src_id or "").strip()
        dst_id = str(dst_id or "").strip()
        if not src_id or not dst_id or src_id == dst_id:
            return False
        spec = _EdgeSpec(src_id, dst_id, kind)
        if spec in self._base_edges or spec in self._extra_edges:
            return False
        self._extra_edges.append(spec)
        self._add_edge_item(spec)
        self._refresh_highlight(self._selected)
        return True

    def clear_user_edges(self) -> None:
        self._extra_edges.clear()
        self._rebuild_scene()

    def _rebuild_scene(self) -> None:
        selected = str(self._selected or "").strip()
        self._scene.clear()
        self._nodes.clear()
        self._edges.clear()
        self._cancel_drag_preview()

        self._add_heading(30, 20, "ZRODLA DANYCH")
        self._add_heading(350, 20, "TABY")
        self._add_heading(980, 20, "PRZEPLYW I WYJSCIA")

        for spec in self._base_nodes:
            item = _FlowNodeItem(spec, self._on_click)
            item.setPos(*spec.pos)
            self._scene.addItem(item)
            self._nodes[spec.node_id] = item

        for edge_spec in [*self._base_edges, *self._extra_edges]:
            self._add_edge_item(edge_spec)

        self._selected = selected
        self._refresh_highlight(self._selected)
        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-40, -40, 60, 60))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _add_edge_item(self, edge_spec: _EdgeSpec) -> None:
        src = self._nodes.get(edge_spec.src)
        dst = self._nodes.get(edge_spec.dst)
        if src is None or dst is None:
            return
        edge = _FlowEdgeItem(src, dst, edge_spec.kind)
        self._scene.addItem(edge)
        self._edges.append(edge)

    def _node_item_at(self, pos) -> _FlowNodeItem | None:
        item = self.itemAt(pos)
        while item is not None:
            if isinstance(item, _FlowNodeItem):
                return item
            item = item.parentItem()
        return None

    def _make_preview_path(self, start: QPointF, end: QPointF) -> QPainterPath:
        path = QPainterPath(start)
        mid_x = (start.x() + end.x()) * 0.5
        if abs(end.x() - start.x()) < 120.0:
            path.lineTo(QPointF(mid_x, start.y()))
            path.lineTo(QPointF(mid_x, end.y()))
            path.lineTo(end)
        else:
            path.cubicTo(QPointF(mid_x, start.y()), QPointF(mid_x, end.y()), end)
        return path

    def _start_drag_preview(self, start: QPointF) -> None:
        self._cancel_drag_preview()
        preview = QGraphicsPathItem()
        pen = QPen(QColor("#0f766e"), 2.4)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        preview.setPen(pen)
        preview.setZValue(-2.0)
        preview.setPath(QPainterPath(start))
        self._scene.addItem(preview)
        self._drag_preview = preview

    def _update_drag_preview(self, start: QPointF, end: QPointF) -> None:
        if self._drag_preview is None:
            return
        self._drag_preview.setPath(self._make_preview_path(start, end))

    def _cancel_drag_preview(self) -> None:
        if self._drag_preview is not None:
            self._scene.removeItem(self._drag_preview)
            self._drag_preview = None
        self._drag_source_id = ""

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if self._edit_mode and event.button() == Qt.MouseButton.LeftButton:
            node = self._node_item_at(event.position().toPoint())
            if node is not None:
                self._drag_source_id = node.spec.node_id
                self._selected = node.spec.node_id
                self._refresh_highlight(self._selected)
                self._click_cb(self._selected)
                self._start_drag_preview(node.sceneBoundingRect().center())
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._edit_mode and self._drag_source_id and self._drag_preview is not None:
            source = self._nodes.get(self._drag_source_id)
            if source is not None:
                self._update_drag_preview(source.sceneBoundingRect().center(), self.mapToScene(event.position().toPoint()))
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if self._edit_mode and self._drag_source_id and event.button() == Qt.MouseButton.LeftButton:
            source_id = self._drag_source_id
            target = self._node_item_at(event.position().toPoint())
            self._cancel_drag_preview()
            if target is not None and target.spec.node_id != source_id:
                if self.add_user_edge(source_id, target.spec.node_id, "flow"):
                    self._selected = target.spec.node_id
                    self._refresh_highlight(self._selected)
                    self._click_cb(self._selected)
            else:
                self._refresh_highlight(self._selected)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _add_heading(self, x: float, y: float, text: str) -> None:
        item = QGraphicsSimpleTextItem(text)
        item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        item.setBrush(QColor("#64748b"))
        item.setPos(x, y)
        self._scene.addItem(item)

    def _on_click(self, node_id: str) -> None:
        self._selected = str(node_id or "").strip()
        self._refresh_highlight(self._selected)
        self._click_cb(self._selected)

    def _refresh_highlight(self, node_id: str) -> None:
        for node in self._nodes.values():
            selected = bool(node_id) and node.spec.node_id == node_id
            dimmed = bool(node_id) and not selected
            if selected:
                node.setOpacity(1.0)
                node.setPen(QPen(QColor(node.spec.border), 3.0))
            elif dimmed:
                node.setOpacity(0.50)
                node.setPen(QPen(QColor(node.spec.border), 1.5))
            else:
                node.setOpacity(1.0)
                node.setPen(QPen(QColor(node.spec.border), 2.0))
        for edge in self._edges:
            active = bool(node_id) and (edge.src.spec.node_id == node_id or edge.dst.spec.node_id == node_id)
            dimmed = bool(node_id) and not active
            edge.set_highlighted(active, dimmed)

    def clear_selection(self) -> None:
        self._selected = ""
        self._refresh_highlight("")
        self._click_cb("")

    def selected_node_id(self) -> str:
        return self._selected


class TabStruktura(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("STRUKTURA")
        title.setStyleSheet("font-size:26px; font-weight:800; color:#e8efff;")
        root.addWidget(title)

        subtitle = QLabel(
            "Kliknij prostokat, a zobaczysz linie przeplywu i zrodla danych. "
            "To jest mapa tego, skad ekran bierze dane i gdzie je wysyla dalej."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size:13px; color:#94a3b8;")
        root.addWidget(subtitle)

        row = QHBoxLayout()
        self.btn_reset = QPushButton("Pokaz caly diagram", self)
        self.btn_reset.setMinimumHeight(32)
        self.btn_reset.clicked.connect(self._reset_selection)
        row.addWidget(self.btn_reset, 0)
        self.btn_edit_links = QPushButton("Rysuj linie", self)
        self.btn_edit_links.setCheckable(True)
        self.btn_edit_links.setMinimumHeight(32)
        self.btn_edit_links.clicked.connect(self._toggle_link_mode)
        row.addWidget(self.btn_edit_links, 0)
        self.btn_clear_links = QPushButton("Wyczysc linie", self)
        self.btn_clear_links.setMinimumHeight(32)
        self.btn_clear_links.clicked.connect(self._clear_user_links)
        row.addWidget(self.btn_clear_links, 0)
        self.lab_hint = QLabel(
            "Legenda: zielone = zrodla danych, pomaranczowe = przeplyw tabow, niebieskie = powroty / odpowiedzi. "
            "W trybie rysowania przeciagaj miedzy prostokatami, zeby dopiac nowa linie.",
            self,
        )
        self.lab_hint.setStyleSheet("color:#64748b; font-size:12px;")
        row.addWidget(self.lab_hint, 1)
        root.addLayout(row)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        canvas_card = QFrame(self); canvas_card.setProperty("uiCard", True)
        canvas_card.setStyleSheet("QFrame { border: 1px solid #d9e0ea; border-radius: 12px; background:transparent; }")
        canvas_layout = QVBoxLayout(canvas_card)
        canvas_layout.setContentsMargins(10, 10, 10, 10)
        canvas_layout.setSpacing(8)

        self.canvas = _StructureCanvas(self._on_node_selected, canvas_card)
        self.canvas.setMinimumSize(1400, 900)
        canvas_layout.addWidget(self.canvas, 1)

        details_card = QFrame(self); details_card.setProperty("uiCard", True)
        details_card.setStyleSheet("QFrame { border: 1px solid #d9e0ea; border-radius: 12px; background:#fbfcfe; }")
        details_layout = QVBoxLayout(details_card)
        details_layout.setContentsMargins(10, 10, 10, 10)
        details_layout.setSpacing(8)

        details_title = QLabel("Szczegoly wybranego prostokata", self)
        details_title.setStyleSheet("font-size:16px; font-weight:800; color:#e8efff;")
        details_layout.addWidget(details_title)

        self.details = QTextBrowser(self)
        self.details.setStyleSheet(
            "QTextBrowser { background:transparent; border:1px solid #d9e0ea; border-radius:10px; padding:10px; }"
        )
        details_layout.addWidget(self.details, 1)

        self.quick_note = QLabel(
            "Wskazowka: kliknij node, zeby podswietlic jego wejscia i wyjscia. "
            "Wlacz 'Rysuj linie' i przeciagnij miedzy blokami, zeby stworzyc nowe polaczenie.",
            self,
        )
        self.quick_note.setWordWrap(True)
        self.quick_note.setStyleSheet("color:#64748b; font-size:12px;")
        details_layout.addWidget(self.quick_note, 0)

        splitter.addWidget(canvas_card)
        splitter.addWidget(details_card)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 2)

        self._nodes = self._build_nodes()
        self._edges = self._build_edges()
        self.canvas.build(self._nodes, self._edges)
        self._on_node_selected("ZAMOWIENIE")

    def _reset_selection(self) -> None:
        self.canvas.clear_selection()

    def _toggle_link_mode(self, checked: bool) -> None:
        self.canvas.set_edit_mode(checked)
        if checked:
            self.btn_edit_links.setText("Rysowanie: ON")
            self.lab_hint.setText(
                "Tryb rysowania wlaczony. Przeciagnij z jednego prostokata do drugiego, a linia zostanie dodana."
            )
        else:
            self.btn_edit_links.setText("Rysuj linie")
            self.lab_hint.setText(
                "Legenda: zielone = zrodla danych, pomaranczowe = przeplyw tabow, niebieskie = powroty / odpowiedzi."
            )

    def _clear_user_links(self) -> None:
        self.canvas.clear_user_edges()

    def _build_nodes(self) -> list[_NodeSpec]:
        return [
            _NodeSpec("SRC_CLIENTS", "Klienci", "data/clients.json", "source", (30, 80), (250, 76), "#064e3b", "#10b981", ("C:/PythonProject/TECH_modul/data/clients.json",), (), ("ZAMOWIENIE",)),
            _NodeSpec("SRC_WORKERS", "Pracownicy", "data/workers.json", "source", (30, 178), (250, 76), "#064e3b", "#10b981", ("C:/PythonProject/TECH_modul/data/workers.json",), (), ("ZAMOWIENIE", "CZAS_PRACY", "DASHBOARD")),
            _NodeSpec("SRC_ORDERS", "Zamowienia", "data/orders.json", "source", (30, 276), (250, 76), "#064e3b", "#10b981", ("C:/PythonProject/TECH_modul/data/orders.json",), (), ("ZAMOWIENIE", "WYCENA", "KALENDARZ", "DASHBOARD")),
            _NodeSpec("SRC_MODULES", "Moduly", "data/modules.json", "source", (30, 374), (250, 76), "#064e3b", "#10b981", ("C:/PythonProject/TECH_modul/data/modules.json",), (), ("MODUL", "KOMPLET", "SCIANA", "BAZA_MODUL")),
            _NodeSpec("SRC_MATERIALS", "Materialy", "data/baza_materialu.json", "source", (30, 472), (250, 76), "#064e3b", "#10b981", ("C:/PythonProject/TECH_modul/data/baza_materialu.json",), (), ("WYCENA", "SEKCJE", "MODUL", "KOMPLET", "SCIANA", "ZAKUPY")),
            _NodeSpec("SRC_QUICK", "Szybkie wyceny", "archive / in_progress", "source", (30, 570), (250, 76), "#064e3b", "#10b981", ("C:/PythonProject/TECH_modul/data/quick_quote_archive.json", "C:/PythonProject/TECH_modul/data/quick_quote_in_progress.json"), (), ("WYCENA", "SEKCJE", "BAZA_SZYBKICH_WYCEN")),
            _NodeSpec("SRC_SERVICES", "Uslugi", "data/services.json", "source", (30, 668), (250, 76), "#064e3b", "#10b981", ("C:/PythonProject/TECH_modul/data/services.json",), (), ("USLUGI",)),
            _NodeSpec("SRC_CATALOG", "Katalog", "catalog / receptury", "source", (30, 766), (250, 76), "#064e3b", "#10b981", ("C:/PythonProject/TECH_modul/data/catalog.json", "C:/PythonProject/TECH_modul/data/receptura.json"), (), ("WYCENA", "MODUL", "SCIANA", "KOMPLET", "USLUGI")),
            _NodeSpec("SRC_CALENDAR", "Kalendarz", "statusy i terminy", "source", (30, 864), (250, 76), "#064e3b", "#10b981", ("C:/PythonProject/TECH_modul/data/calendar.json", "C:/PythonProject/TECH_modul/data/orders.json"), (), ("KALENDARZ", "ZAMOWIENIE", "SCIANA", "KOMPLET", "DASHBOARD")),
            _NodeSpec("SRC_TIME", "Czas pracy", "work time / stawki", "source", (30, 962), (250, 76), "#064e3b", "#10b981", ("C:/PythonProject/TECH_modul/data/work_time.json", "C:/PythonProject/TECH_modul/data/workers.json"), (), ("CZAS_PRACY", "WYCENA", "DASHBOARD")),
            _NodeSpec("START", "START", "punkt wejscia", "tab", (350, 80), (260, 86), "#fff7ed", "#c2410c", ("C:/PythonProject/TECH_modul/src/tabs/start/tab_start.py",), ("Briefing dnia",), ("ZAMOWIENIE", "USLUGI", "BAZY")),
            _NodeSpec("ZAMOWIENIE", "ZAMOWIENIE", "draft projektu, pozycje i zalaczniki", "tab", (350, 220), (260, 92), "#eff6ff", "#2563eb", ("C:/PythonProject/TECH_modul/src/tabs/zamowienie/tab_nowe_zamowienie.py", "C:/PythonProject/TECH_modul/src/app/main_window_wiring.py"), ("Klienci", "Pracownicy", "Bazy", "Pozycje do wyceny", "Zalaczniki", "Statusy", "Kalendarz"), ("POZYCJE", "WYCENA", "SEKCJE", "SCIANA", "KOMPLET", "KALENDARZ")),
            _NodeSpec("POZYCJE", "POZYCJE", "wybor pozycji i zalaczniki", "tab", (350, 322), (260, 78), "#ecfeff", "#0891b2", ("C:/PythonProject/TECH_modul/src/tabs/zamowienie/tab_nowe_zamowienie.py",), ("Pozycje do wyceny", "Zalaczniki", "Wycena pozycji", "Powrot do zamowienia"), ("WYCENA", "ZAMOWIENIE")),
            _NodeSpec("WYCENA", "Wycena pozycji", "koszt, marza, oferta", "tab", (350, 360), (260, 92), "#eff6ff", "#2563eb", ("C:/PythonProject/TECH_modul/src/tabs/wycena/tab_wycena.py", "C:/PythonProject/TECH_modul/src/tabs/baza_szybkich_wycen/tab_baza_szybkich_wycen.py"), ("Zamowienie", "Quick quote archive", "Quick quote in progress", "Bazy materialow", "Czas pracy"), ("SEKCJE", "BAZA_SZYBKICH_WYCEN", "SCIANA", "KOMPLET")),
            _NodeSpec("SEKCJE", "Szybka wycena", "szybka wycena pozycji i podgląd formatek", "tab", (350, 500), (260, 92), "#eff6ff", "#2563eb", ("C:/PythonProject/TECH_modul/src/tabs/szybka_wycena/tab_szybka_wycena.py",), ("Materiały", "Moduły", "Szybkie wyceny", "Klient", "Pozycje"), ("POZYCJE", "WYCENA", "MODUL", "SCIANA", "KOMPLET", "BAZA_SZYBKICH_WYCEN")),
            _NodeSpec("USLUGI", "USLUGI", "pozycje i formatki", "tab", (350, 640), (260, 92), "#fff1f2", "#be123c", ("C:/PythonProject/TECH_modul/src/tabs/uslugi/tab_uslugi.py",), ("Materialy", "Klient", "Formatki"), ("WYCENA", "ZAMOWIENIE")),
            _NodeSpec("MODUL", "MODUL", "formatki i obrzeza", "tab", (680, 220), (260, 92), "#f5f3ff", "#7c3aed", ("C:/PythonProject/TECH_modul/src/tabs/modul/tab_modul.py", "C:/PythonProject/TECH_modul/src/core/module_parts_service.py"), ("Modules.json", "Catalog", "domyslne materialy"), ("SCIANA", "KOMPLET", "BAZA_MODUL")),
            _NodeSpec("KOMPLET", "KOMPLET", "modul roboczy i materialy", "tab", (680, 360), (260, 92), "#f5f3ff", "#7c3aed", ("C:/PythonProject/TECH_modul/src/tabs/sciana/tab_sciana.py", "C:/PythonProject/TECH_modul/src/tabs/sciana/tab_sciana_layout.py"), ("Zamowienie", "Modul", "Materialy", "Kalendarz"), ("ZAMOWIENIE", "ZAKUPY")),
            _NodeSpec("SCIANA", "SCIANA", "uklad sciany i kolizje", "tab", (680, 500), (260, 92), "#f5f3ff", "#7c3aed", ("C:/PythonProject/TECH_modul/src/tabs/sciana/tab_sciana_layout.py",), ("Zamowienie", "Modul", "Kalendarz", "Materialy"), ("KOMPLET", "ZAMOWIENIE")),
            _NodeSpec("DASHBOARD", "Dashboard", "zestawienie wynikow", "tab", (680, 640), (260, 92), "#ecfeff", "#0f766e", ("C:/PythonProject/TECH_modul/src/tabs/dashboard/tab_dashboard.py",), ("Zamowienia", "Czas pracy", "Zakupy", "Finanse", "Wycena"), ("ALARMY", "KALENDARZ")),
            _NodeSpec("ALARMY", "ALARMY", "ostrzezenia i sygnaly", "tab", (680, 780), (260, 92), "#fff7ed", "#d97706", ("C:/PythonProject/TECH_modul/src/tabs/alarmy/tab_alarmy.py",), ("Kalendarz", "Zamowienia", "Zdarzenia"), ("DASHBOARD",)),
            _NodeSpec("KALENDARZ", "KALENDARZ", "terminy i statusy", "tab", (980, 220), (260, 92), "#eff6ff", "#2563eb", ("C:/PythonProject/TECH_modul/src/tabs/kalendarz/tab_kalendarz.py",), ("Zamowienie", "Sciana", "Komplet", "Czas pracy"), ("DASHBOARD", "ALARMY")),
            _NodeSpec("CZAS_PRACY", "Czas pracy", "planowane vs realne", "tab", (980, 360), (260, 92), "#eff6ff", "#2563eb", ("C:/PythonProject/TECH_modul/src/tabs/czas_pracy/tab_czas_pracy.py",), ("Pracownicy", "Zamowienia", "Realne godziny"), ("DASHBOARD", "WYCENA")),
            _NodeSpec("ZAKUPY", "ZAKUPY", "materialy i dostawcy", "tab", (980, 500), (260, 92), "#eff6ff", "#2563eb", ("C:/PythonProject/TECH_modul/src/tabs/zakupy/tab_zakupy.py",), ("Komplet", "Sciana", "Materialy", "Faktury"), ("DASHBOARD",)),
            _NodeSpec("BAZY", "BAZY", "hub danych", "tab", (980, 640), (260, 92), "transparent", "#334155", ("C:/PythonProject/TECH_modul/src/tabs/bazy/tab_bazy.py",), ("Klienci", "Materialy", "Moduly", "Szybkie wyceny"), ("BAZA_MODUL", "BAZA_MATERIALU", "BAZA_SZYBKICH_WYCEN")),
            _NodeSpec("BAZA_MODUL", "BAZA_modul", "modules.json", "tab", (1280, 220), (260, 92), "transparent", "#334155", ("C:/PythonProject/TECH_modul/src/tabs/baza_modul/tab_baza_modul.py", "C:/PythonProject/TECH_modul/data/modules.json"), (), ("MODUL", "KOMPLET", "SCIANA")),
            _NodeSpec("BAZA_MATERIALU", "Baza materialu", "baza_materialu.json", "tab", (1280, 360), (260, 92), "transparent", "#334155", ("C:/PythonProject/TECH_modul/src/tabs/baza_materialu/tab_baza_materialu.py", "C:/PythonProject/TECH_modul/data/baza_materialu.json"), (), ("WYCENA", "SEKCJE", "MODUL", "ZAKUPY", "USLUGI")),
            _NodeSpec("BAZA_SZYBKICH_WYCEN", "Baza szybkich wycen", "quick_quote_archive.json", "tab", (1280, 500), (260, 92), "transparent", "#334155", ("C:/PythonProject/TECH_modul/src/tabs/baza_szybkich_wycen/tab_baza_szybkich_wycen.py", "C:/PythonProject/TECH_modul/data/quick_quote_archive.json"), (), ("WYCENA", "SEKCJE")),
            _NodeSpec("USTAWIENIA", "USTAWIENIA", "ustawienia programu", "tab", (1280, 640), (260, 92), "#fff7ed", "#c2410c", ("C:/PythonProject/TECH_modul/src/tabs/rysunek/tab_rysunek.py",), ("Motyw", "Font", "Role"), ("STRUKTURA",)),
            _NodeSpec("STRUKTURA", "STRUKTURA", "ta mapa przeplywu", "tab", (1280, 780), (260, 92), "#064e3b", "#10b981", ("C:/PythonProject/TECH_modul/src/tabs/struktura/tab_struktura.py",), ("Wszystkie zakladki", "Zrodla danych"), ("START",)),
            _NodeSpec("STANOWISKA", "STANOWISKA", "podglad ekranow hali", "tab", (1280, 920), (260, 92), "#eef2ff", "#4f46e5", ("C:/PythonProject/TECH_modul/src/tabs/stanowiska/tab_stanowiska.py", "C:/PythonProject/TECH_modul/src/server/stanowisko_page.py"), ("Zamowienia", "Pracownicy", "Kalendarz"), ("EKRANY", "QR_TELEFON")),
            _NodeSpec("EKRANY", "EKRANY", "podglad stanowiska i botow", "tab", (1280, 1060), (260, 92), "#ecfeff", "#0f766e", ("C:/PythonProject/TECH_modul/src/tabs/ekrany/tab_ekrany.py",), ("Zamowienia", "Pracownicy", "Kalendarz", "Czas pracy"), ("STANOWISKA",)),
            _NodeSpec("QR_TELEFON", "QR TELEFON", "skanery / kiosk / pomiary", "tab", (1280, 1200), (260, 92), "#fdf2f8", "#be185d", ("C:/PythonProject/TECH_modul/src/tabs/qr_telefon/tab_qr_telefon.py", "C:/PythonProject/TECH_modul/src/server/data_server.py", "C:/PythonProject/TECH_modul/src/server/package_scanner_page.py", "C:/PythonProject/TECH_modul/src/server/kiosk_page.py", "C:/PythonProject/TECH_modul/src/server/measure_mobile_page.py"), ("Adres serwera", "Linki mobilne", "QR skanera", "Kiosk czasu", "Pomiary"), ("STANOWISKA",)),
        ]

    def _build_edges(self) -> list[_EdgeSpec]:
        return [
            _EdgeSpec("SRC_CLIENTS", "ZAMOWIENIE", "data"),
            _EdgeSpec("SRC_WORKERS", "ZAMOWIENIE", "data"),
            _EdgeSpec("SRC_ORDERS", "ZAMOWIENIE", "data"),
            _EdgeSpec("SRC_ORDERS", "WYCENA", "data"),
            _EdgeSpec("SRC_ORDERS", "KALENDARZ", "data"),
            _EdgeSpec("SRC_MODULES", "MODUL", "data"),
            _EdgeSpec("SRC_MODULES", "KOMPLET", "data"),
            _EdgeSpec("SRC_MODULES", "SCIANA", "data"),
            _EdgeSpec("SRC_MODULES", "BAZA_MODUL", "data"),
            _EdgeSpec("SRC_MATERIALS", "WYCENA", "data"),
            _EdgeSpec("SRC_MATERIALS", "SEKCJE", "data"),
            _EdgeSpec("SRC_MATERIALS", "MODUL", "data"),
            _EdgeSpec("SRC_MATERIALS", "KOMPLET", "data"),
            _EdgeSpec("SRC_MATERIALS", "SCIANA", "data"),
            _EdgeSpec("SRC_MATERIALS", "ZAKUPY", "data"),
            _EdgeSpec("SRC_QUICK", "WYCENA", "data"),
            _EdgeSpec("SRC_QUICK", "SEKCJE", "data"),
            _EdgeSpec("SRC_QUICK", "BAZA_SZYBKICH_WYCEN", "data"),
            _EdgeSpec("SRC_SERVICES", "USLUGI", "data"),
            _EdgeSpec("SRC_CATALOG", "WYCENA", "data"),
            _EdgeSpec("SRC_CATALOG", "MODUL", "data"),
            _EdgeSpec("SRC_CATALOG", "SCIANA", "data"),
            _EdgeSpec("SRC_CATALOG", "KOMPLET", "data"),
            _EdgeSpec("SRC_CATALOG", "USLUGI", "data"),
            _EdgeSpec("SRC_CALENDAR", "KALENDARZ", "data"),
            _EdgeSpec("SRC_CALENDAR", "ZAMOWIENIE", "data"),
            _EdgeSpec("SRC_CALENDAR", "SCIANA", "data"),
            _EdgeSpec("SRC_CALENDAR", "KOMPLET", "data"),
            _EdgeSpec("SRC_CALENDAR", "DASHBOARD", "data"),
            _EdgeSpec("SRC_TIME", "CZAS_PRACY", "data"),
            _EdgeSpec("SRC_TIME", "WYCENA", "data"),
            _EdgeSpec("SRC_TIME", "DASHBOARD", "data"),
            _EdgeSpec("START", "ZAMOWIENIE", "flow"),
            _EdgeSpec("ZAMOWIENIE", "POZYCJE", "flow"),
            _EdgeSpec("POZYCJE", "WYCENA", "flow"),
            _EdgeSpec("WYCENA", "ZAMOWIENIE", "return"),
            _EdgeSpec("ZAMOWIENIE", "WYCENA", "flow"),
            _EdgeSpec("ZAMOWIENIE", "SEKCJE", "flow"),
            _EdgeSpec("WYCENA", "SEKCJE", "flow"),
            _EdgeSpec("SEKCJE", "MODUL", "flow"),
            _EdgeSpec("SEKCJE", "SCIANA", "flow"),
            _EdgeSpec("SEKCJE", "KOMPLET", "flow"),
            _EdgeSpec("WYCENA", "BAZA_SZYBKICH_WYCEN", "flow"),
            _EdgeSpec("MODUL", "SCIANA", "flow"),
            _EdgeSpec("MODUL", "KOMPLET", "flow"),
            _EdgeSpec("SCIANA", "KOMPLET", "return"),
            _EdgeSpec("SCIANA", "ZAMOWIENIE", "return"),
            _EdgeSpec("KOMPLET", "ZAMOWIENIE", "return"),
            _EdgeSpec("KOMPLET", "ZAKUPY", "flow"),
            _EdgeSpec("KALENDARZ", "DASHBOARD", "flow"),
            _EdgeSpec("CZAS_PRACY", "DASHBOARD", "flow"),
            _EdgeSpec("ZAKUPY", "DASHBOARD", "flow"),
            _EdgeSpec("BAZY", "BAZA_MODUL", "flow"),
            _EdgeSpec("BAZY", "BAZA_MATERIALU", "flow"),
            _EdgeSpec("BAZY", "BAZA_SZYBKICH_WYCEN", "flow"),
            _EdgeSpec("SRC_ORDERS", "STANOWISKA", "data"),
            _EdgeSpec("SRC_WORKERS", "STANOWISKA", "data"),
            _EdgeSpec("SRC_CALENDAR", "STANOWISKA", "data"),
            _EdgeSpec("SRC_ORDERS", "EKRANY", "data"),
            _EdgeSpec("SRC_WORKERS", "EKRANY", "data"),
            _EdgeSpec("SRC_TIME", "EKRANY", "data"),
            _EdgeSpec("USTAWIENIA", "QR_TELEFON", "flow"),
            _EdgeSpec("DASHBOARD", "ALARMY", "flow"),
            _EdgeSpec("USTAWIENIA", "STRUKTURA", "flow"),
        ]

    def _reset_selection(self) -> None:
        self.canvas.clear_selection()

    def _friendly_name(self, node_id: str) -> str:
        mapping = {
            "SRC_CLIENTS": "Klienci",
            "SRC_WORKERS": "Pracownicy",
            "SRC_ORDERS": "Zamowienia",
            "SRC_MODULES": "Moduly",
            "SRC_MATERIALS": "Materialy",
            "SRC_QUICK": "Szybkie wyceny",
            "SRC_SERVICES": "Uslugi",
            "SRC_CATALOG": "Katalog",
            "SRC_CALENDAR": "Kalendarz",
            "SRC_TIME": "Czas pracy",
            "START": "Start",
            "ZAMOWIENIE": "Zamowienie",
            "POZYCJE": "Pozycje i zalaczniki",
            "WYCENA": "Wycena pozycji",
            "SEKCJE": "Szybka wycena",
            "USLUGI": "Usługi",
            "MODUL": "Modul",
            "KOMPLET": "Komplet",
            "SCIANA": "Sciana",
            "DASHBOARD": "Dashboard",
            "ALARMY": "ALARMY",
            "KALENDARZ": "Kalendarz",
            "CZAS_PRACY": "Czas pracy",
            "ZAKUPY": "Zakupy",
            "BAZY": "Bazy",
            "BAZA_MODUL": "BAZA_modul",
            "BAZA_MATERIALU": "Baza materialu",
            "BAZA_SZYBKICH_WYCEN": "Baza szybkich wycen",
            "USTAWIENIA": "Ustawienia",
            "STRUKTURA": "Struktura",
            "STANOWISKA": "Stanowiska",
            "EKRANY": "Ekrany",
            "QR_TELEFON": "QR TELEFON",
        }
        return mapping.get(node_id, node_id)

    def _on_node_selected(self, node_id: str) -> None:
        key = str(node_id or "").strip()
        if not key:
            self.details.setHtml(
                "<h3>Brak zaznaczenia</h3><p>Kliknij prostokat, a pokażę skąd bierze dane i gdzie je oddaje dalej.</p>"
            )
            return

        spec = next((node for node in self._nodes if node.node_id == key), None)
        if spec is None:
            self.details.setHtml("<h3>Nieznany node</h3>")
            return

        incoming = [edge.src for edge in self._edges if edge.dst == key]
        outgoing = [edge.dst for edge in self._edges if edge.src == key]
        sources_text = "".join(f"<li>{self._friendly_name(src)}</li>" for src in incoming) or "<li>brak</li>"
        targets_text = "".join(f"<li>{self._friendly_name(dst)}</li>" for dst in outgoing) or "<li>brak</li>"
        files_text = "".join(f"<li><code>{file}</code></li>" for file in spec.files) or "<li>brak</li>"
        reads_text = "".join(f"<li>{text}</li>" for text in spec.reads) or "<li>brak</li>"
        writes_text = "".join(f"<li>{text}</li>" for text in spec.writes) or "<li>brak</li>"

        html = f"""
        <html>
          <body style="font-family:'Segoe UI'; color:#e8efff;">
            <h2 style="margin:0 0 8px 0;">{spec.title}</h2>
            <div style="color:#64748b; margin-bottom:10px;">{spec.subtitle}</div>
            <p><b>Rola:</b> {spec.kind.upper()}</p>
            <p><b>Co czytam:</b></p>
            <ul>{reads_text}</ul>
            <p><b>Skad przychodza linie:</b></p>
            <ul>{sources_text}</ul>
            <p><b>Dokad ida dalej:</b></p>
            <ul>{targets_text}</ul>
            <p><b>Pliki / moduly:</b></p>
            <ul>{files_text}</ul>
            <p><b>Uwagi:</b> {spec.note or '[brak]'}</p>
            <p><b>Co zapisuje / oddaje:</b></p>
            <ul>{writes_text}</ul>
          </body>
        </html>
        """
        self.details.setHtml(html)
