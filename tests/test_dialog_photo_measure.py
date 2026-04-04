from PyQt6.QtCore import QPointF

from src.tabs.sciana.dialog_photo_measure import distance_mm, distance_px


def test_distance_px_uses_euclidean_metric() -> None:
    p1 = QPointF(0.0, 0.0)
    p2 = QPointF(3.0, 4.0)
    assert abs(distance_px(p1, p2) - 5.0) < 1e-9


def test_distance_mm_scales_pixel_distance() -> None:
    assert abs(distance_mm(200.0, 0.5) - 100.0) < 1e-9
    assert distance_mm(-1.0, 0.5) == 0.0
    assert distance_mm(10.0, -1.0) == 0.0
