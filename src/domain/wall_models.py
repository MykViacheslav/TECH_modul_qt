from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class WallObstacleDef:
    kind: str = "projection"
    wall_side: str = "A"
    name: str = ""
    opening_direction: str = "fixed"
    x_mm: float = 0.0
    bottom_offset_mm: float = 0.0
    width_mm: float = 600.0
    height_mm: float = 1000.0
    depth_mm: float = 120.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "wall_side": self.wall_side,
            "name": self.name,
            "opening_direction": self.opening_direction,
            "x_mm": float(self.x_mm),
            "bottom_offset_mm": float(self.bottom_offset_mm),
            "width_mm": float(self.width_mm),
            "height_mm": float(self.height_mm),
            "depth_mm": float(self.depth_mm),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WallObstacleDef":
        data = data or {}
        return cls(
            kind=str(data.get("kind", "projection") or "projection"),
            wall_side=str(data.get("wall_side", "A") or "A"),
            name=str(data.get("name", "") or ""),
            opening_direction=str(data.get("opening_direction", "fixed") or "fixed"),
            x_mm=float(data.get("x_mm", 0.0) or 0.0),
            bottom_offset_mm=float(data.get("bottom_offset_mm", 0.0) or 0.0),
            width_mm=float(data.get("width_mm", 600.0) or 600.0),
            height_mm=float(data.get("height_mm", 1000.0) or 1000.0),
            depth_mm=float(data.get("depth_mm", 120.0) or 120.0),
        )


@dataclass
class WallPhotoDef:
    path: str = ""
    caption: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "caption": self.caption,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WallPhotoDef":
        data = data or {}
        return cls(
            path=str(data.get("path", "") or ""),
            caption=str(data.get("caption", "") or ""),
        )


@dataclass
class WallLayoutDef:
    name: str = "Sciana 1"
    client_name: str = ""
    order_name: str = ""
    worker_name: str = ""
    layout_type: str = "line"
    front_view_wall_side: str = "A"
    wall_a_width_mm: float = 4000.0
    wall_b_width_mm: float = 2600.0
    wall_c_width_mm: float = 2600.0
    room_height_mm: float = 2600.0
    base_depth_mm: float = 600.0
    base_plinth_mm: float = 100.0
    upper_clearance_mm: float = 0.0
    top_offset_mm: float = 0.0
    bottom_offset_mm: float = 0.0
    base_offset_left_mm: float = 0.0
    base_offset_right_mm: float = 0.0
    upper_offset_left_mm: float = 0.0
    upper_offset_right_mm: float = 0.0
    has_island: bool = False
    island_width_mm: float = 1800.0
    island_depth_mm: float = 900.0
    island_offset_x_mm: float = 1200.0
    island_offset_y_mm: float = 1400.0
    notes: str = ""
    obstacles: List[WallObstacleDef] = field(default_factory=list)
    photos: List[WallPhotoDef] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "client_name": self.client_name,
            "order_name": self.order_name,
            "worker_name": self.worker_name,
            "layout_type": self.layout_type,
            "front_view_wall_side": self.front_view_wall_side,
            "wall_a_width_mm": float(self.wall_a_width_mm),
            "wall_b_width_mm": float(self.wall_b_width_mm),
            "wall_c_width_mm": float(self.wall_c_width_mm),
            "room_height_mm": float(self.room_height_mm),
            "base_depth_mm": float(self.base_depth_mm),
            "base_plinth_mm": float(self.base_plinth_mm),
            "upper_clearance_mm": float(self.upper_clearance_mm),
            "top_offset_mm": float(self.top_offset_mm),
            "bottom_offset_mm": float(self.bottom_offset_mm),
            "base_offset_left_mm": float(self.base_offset_left_mm),
            "base_offset_right_mm": float(self.base_offset_right_mm),
            "upper_offset_left_mm": float(self.upper_offset_left_mm),
            "upper_offset_right_mm": float(self.upper_offset_right_mm),
            "has_island": bool(self.has_island),
            "island_width_mm": float(self.island_width_mm),
            "island_depth_mm": float(self.island_depth_mm),
            "island_offset_x_mm": float(self.island_offset_x_mm),
            "island_offset_y_mm": float(self.island_offset_y_mm),
            "notes": self.notes,
            "obstacles": [item.to_dict() for item in (self.obstacles or [])],
            "photos": [item.to_dict() for item in (self.photos or [])],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WallLayoutDef":
        data = data or {}
        raw_obstacles = data.get("obstacles") or []
        raw_photos = data.get("photos") or []

        obstacles: List[WallObstacleDef] = []
        for item in raw_obstacles:
            if isinstance(item, WallObstacleDef):
                obstacles.append(item)
            elif isinstance(item, dict):
                obstacles.append(WallObstacleDef.from_dict(item))

        photos: List[WallPhotoDef] = []
        for item in raw_photos:
            if isinstance(item, WallPhotoDef):
                photos.append(item)
            elif isinstance(item, dict):
                photos.append(WallPhotoDef.from_dict(item))

        return cls(
            name=str(data.get("name", "Sciana 1") or "Sciana 1"),
            client_name=str(data.get("client_name", "") or ""),
            order_name=str(data.get("order_name", "") or ""),
            worker_name=str(data.get("worker_name", "") or ""),
            layout_type=str(data.get("layout_type", "line") or "line"),
            front_view_wall_side=str(data.get("front_view_wall_side", "A") or "A"),
            wall_a_width_mm=float(data.get("wall_a_width_mm", 4000.0) or 4000.0),
            wall_b_width_mm=float(data.get("wall_b_width_mm", 2600.0) or 2600.0),
            wall_c_width_mm=float(data.get("wall_c_width_mm", 2600.0) or 2600.0),
            room_height_mm=float(data.get("room_height_mm", 2600.0) or 2600.0),
            base_depth_mm=float(data.get("base_depth_mm", 600.0) or 600.0),
            base_plinth_mm=float(data.get("base_plinth_mm", 100.0) or 100.0),
            upper_clearance_mm=float(data.get("upper_clearance_mm", 0.0) or 0.0),
            top_offset_mm=float(data.get("top_offset_mm", 0.0) or 0.0),
            bottom_offset_mm=float(data.get("bottom_offset_mm", 0.0) or 0.0),
            base_offset_left_mm=float(data.get("base_offset_left_mm", 0.0) or 0.0),
            base_offset_right_mm=float(data.get("base_offset_right_mm", 0.0) or 0.0),
            upper_offset_left_mm=float(data.get("upper_offset_left_mm", 0.0) or 0.0),
            upper_offset_right_mm=float(data.get("upper_offset_right_mm", 0.0) or 0.0),
            has_island=bool(data.get("has_island", False)),
            island_width_mm=float(data.get("island_width_mm", 1800.0) or 1800.0),
            island_depth_mm=float(data.get("island_depth_mm", 900.0) or 900.0),
            island_offset_x_mm=float(data.get("island_offset_x_mm", 1200.0) or 1200.0),
            island_offset_y_mm=float(data.get("island_offset_y_mm", 1400.0) or 1400.0),
            notes=str(data.get("notes", "") or ""),
            obstacles=obstacles,
            photos=photos,
        )
