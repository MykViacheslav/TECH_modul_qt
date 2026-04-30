from __future__ import annotations

import math
from pathlib import Path

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPen, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)


def distance_px(p1: QPointF, p2: QPointF) -> float:
    dx = float(p2.x() - p1.x())
    dy = float(p2.y() - p1.y())
    return math.hypot(dx, dy)


def distance_mm(px_distance: float, mm_per_px: float) -> float:
    return float(max(0.0, px_distance) * max(0.0, mm_per_px))


class PhotoMeasureCanvas(QGraphicsView):
    sig_points_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._overlay_items: list[object] = []
        self._points: list[QPointF] = []
        self._is_resizing = False

    @property
    def points(self) -> list[QPointF]:
        return list(self._points)

    def has_image(self) -> bool:
        return self._pixmap_item is not None and not self._pixmap_item.pixmap().isNull()

    def load_image(self, path: str) -> bool:
        pixmap = QPixmap(str(path or "").strip())
        if pixmap.isNull():
            self._scene.clear()
            self._pixmap_item = None
            self._points = []
            return False
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._points = []
        self._overlay_items = []
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.sig_points_changed.emit()
        return True

    def clear_points(self) -> None:
        self._points = []
        self._clear_overlay()
        self.sig_points_changed.emit()

    def pixel_distance(self) -> float:
        if len(self._points) < 2:
            return 0.0
        return distance_px(self._points[0], self._points[1])

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self._is_resizing:
            return
        if self.has_image():
            self._is_resizing = True
            try:
                self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            finally:
                self._is_resizing = False

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() != Qt.MouseButton.LeftButton or not self.has_image():
            super().mousePressEvent(event)
            return
        scene_pos = self.mapToScene(event.pos())
        point = self._clamp_to_image(scene_pos)
        if len(self._points) >= 2:
            self._points = []
            self._clear_overlay()
        self._points.append(point)
        self._redraw_overlay()
        self.sig_points_changed.emit()
        event.accept()

    def _clamp_to_image(self, point: QPointF) -> QPointF:
        if self._pixmap_item is None:
            return point
        rect = self._pixmap_item.boundingRect()
        x = min(max(float(point.x()), float(rect.left())), float(rect.right()))
        y = min(max(float(point.y()), float(rect.top())), float(rect.bottom()))
        return QPointF(x, y)

    def _clear_overlay(self) -> None:
        for item in self._overlay_items:
            try:
                self._scene.removeItem(item)  # type: ignore[arg-type]
            except Exception:
                pass
        self._overlay_items = []

    def _redraw_overlay(self) -> None:
        self._clear_overlay()
        if not self._points:
            return
        pen_point = QPen(QColor("#0b63ce"))
        pen_point.setWidth(2)
        brush_point = QBrush(QColor("#0b63ce"))
        for point in self._points:
            marker = QGraphicsEllipseItem(point.x() - 4.0, point.y() - 4.0, 8.0, 8.0)
            marker.setPen(pen_point)
            marker.setBrush(brush_point)
            marker.setZValue(10.0)
            self._scene.addItem(marker)
            self._overlay_items.append(marker)
        if len(self._points) >= 2:
            p1, p2 = self._points[0], self._points[1]
            line = QGraphicsLineItem(p1.x(), p1.y(), p2.x(), p2.y())
            pen_line = QPen(QColor("#ef4444"))
            pen_line.setWidth(2)
            line.setPen(pen_line)
            line.setZValue(9.0)
            self._scene.addItem(line)
            self._overlay_items.append(line)


class PhotoMeasureDialog(QDialog):
    MEASUREMENT_KINDS: tuple[tuple[str, str], ...] = (
        ("distance", "Odległość"),
        ("width", "Szerokość"),
        ("height", "Wysokość"),
        ("depth", "Głębokość"),
    )

    def __init__(self, parent: QWidget | None = None, photo_path: str = "", quote_reference: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Pomiar ze zdjęcia")
        self.setMinimumSize(900, 680)

        self._measurement_payload: dict[str, object] | None = None
        self._mm_per_px = 0.0
        self._quote_reference = str(quote_reference or "").strip()

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        path_row = QHBoxLayout()
        self.ed_photo_path = QLineEdit()
        self.ed_photo_path.setPlaceholderText("Ścieżka do zdjęcia")
        self.btn_pick_photo = QPushButton("Wybierz")
        self.btn_pick_photo.clicked.connect(self._pick_photo)
        self.btn_load_photo = QPushButton("Wczytaj")
        self.btn_load_photo.clicked.connect(self._load_photo)
        path_row.addWidget(self.ed_photo_path, 1)
        path_row.addWidget(self.btn_pick_photo)
        path_row.addWidget(self.btn_load_photo)
        root.addLayout(path_row)

        self.canvas = PhotoMeasureCanvas(self)
        self.canvas.setMinimumHeight(380)
        self.canvas.sig_points_changed.connect(self._refresh_distance_labels)
        root.addWidget(self.canvas, 1)

        form = QFormLayout()
        self.sp_known_mm = QDoubleSpinBox()
        self.sp_known_mm.setRange(1.0, 100000.0)
        self.sp_known_mm.setDecimals(1)
        self.sp_known_mm.setValue(1000.0)
        self.sp_known_mm.setSuffix(" mm")
        self.btn_calibrate = QPushButton("Ustaw kalibrację z 2 punktów")
        self.btn_calibrate.clicked.connect(self._set_calibration)
        cal_row = QWidget()
        cal_layout = QHBoxLayout(cal_row)
        cal_layout.setContentsMargins(0, 0, 0, 0)
        cal_layout.addWidget(self.sp_known_mm)
        cal_layout.addWidget(self.btn_calibrate)
        form.addRow("Znany odcinek", cal_row)

        self.lab_px_distance = QLabel("Odcinek (px): -")
        self.lab_scale = QLabel("Skala: -")
        self.lab_result_mm = QLabel("Pomiar (mm): -")
        form.addRow("Info", self.lab_px_distance)
        form.addRow("", self.lab_scale)
        form.addRow("", self.lab_result_mm)

        self.ed_measure_name = QLineEdit()
        self.ed_measure_name.setPlaceholderText("np. Ściana A netto")
        form.addRow("Nazwa pomiaru", self.ed_measure_name)

        self.cb_measure_kind = QLineEdit()
        self.cb_measure_kind.setText("distance")
        self.cb_measure_kind.setReadOnly(True)
        form.addRow("Typ (MVP)", self.cb_measure_kind)

        self.ed_measure_note = QLineEdit()
        self.ed_measure_note.setPlaceholderText("Notatka")
        form.addRow("Notatka", self.ed_measure_note)

        root.addLayout(form)

        self.btn_compute = QPushButton("Przelicz pomiar")
        self.btn_compute.clicked.connect(self._compute_measurement)
        root.addWidget(self.btn_compute)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_with_payload)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.ed_photo_path.setText(str(photo_path or "").strip())
        if str(photo_path or "").strip():
            self._load_photo()
        self._refresh_distance_labels()

    def measurement_payload(self) -> dict[str, object] | None:
        return dict(self._measurement_payload) if isinstance(self._measurement_payload, dict) else None

    def _pick_photo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz zdjęcie do pomiaru",
            "",
            "Obrazy (*.png *.jpg *.jpeg *.bmp *.webp);;Wszystkie pliki (*.*)",
        )
        if path:
            self.ed_photo_path.setText(str(path))

    def _load_photo(self) -> None:
        path = str(self.ed_photo_path.text().strip())
        if not path:
            QMessageBox.warning(self, "Brak pliku", "Wybierz ścieżkę do zdjęcia.")
            return
        if not Path(path).exists():
            QMessageBox.warning(self, "Brak pliku", f"Nie znaleziono pliku:\n{path}")
            return
        if not self.canvas.load_image(path):
            QMessageBox.warning(self, "Błąd obrazu", "Nie udało się odczytać obrazu.")
            return
        self._refresh_distance_labels()

    def _refresh_distance_labels(self) -> None:
        px = self.canvas.pixel_distance()
        self.lab_px_distance.setText(f"Odcinek (px): {px:.2f}" if px > 0.0 else "Odcinek (px): -")
        self.lab_scale.setText(f"Skala: {self._mm_per_px:.6f} mm/px" if self._mm_per_px > 0.0 else "Skala: -")
        if px > 0.0 and self._mm_per_px > 0.0:
            mm = distance_mm(px, self._mm_per_px)
            self.lab_result_mm.setText(f"Pomiar (mm): {mm:.1f}")
        else:
            self.lab_result_mm.setText("Pomiar (mm): -")

    def _set_calibration(self) -> None:
        px = self.canvas.pixel_distance()
        known_mm = float(self.sp_known_mm.value())
        if px <= 0.0:
            QMessageBox.warning(self, "Kalibracja", "Kliknij 2 punkty na znanym odcinku.")
            return
        if known_mm <= 0.0:
            QMessageBox.warning(self, "Kalibracja", "Podaj dodatnią długość znanego odcinka.")
            return
        self._mm_per_px = float(known_mm / px)
        self._refresh_distance_labels()

    def _compute_measurement(self) -> None:
        px = self.canvas.pixel_distance()
        if px <= 0.0:
            QMessageBox.warning(self, "Pomiar", "Kliknij 2 punkty pomiarowe.")
            return
        if self._mm_per_px <= 0.0:
            QMessageBox.warning(self, "Pomiar", "Najpierw ustaw kalibrację.")
            return
        self._refresh_distance_labels()

    def _accept_with_payload(self) -> None:
        px = self.canvas.pixel_distance()
        if px <= 0.0 or self._mm_per_px <= 0.0:
            QMessageBox.warning(
                self,
                "Pomiar",
                "Ustaw kalibrację i zaznacz 2 punkty pomiarowe, zanim zatwierdzisz.",
            )
            return
        mm_value = distance_mm(px, self._mm_per_px)
        measure_name = str(self.ed_measure_name.text().strip() or "Pomiar ze zdjęcia")
        self._measurement_payload = {
            "name": measure_name,
            "kind": "distance",
            "value_mm": float(mm_value),
            "photo_path": str(self.ed_photo_path.text().strip()),
            "note": str(self.ed_measure_note.text().strip()),
            "quote_reference": self._quote_reference,
            "calibration_mm_per_px": float(self._mm_per_px),
        }
        self.accept()
