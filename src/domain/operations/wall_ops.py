from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from src.domain.wall_models import WallLayoutDef, WallObstacleDef, new_wall_id

from .adapters.wall_repository import JsonWallRepository, WallRepository
from .errors import NotFoundOperationError, ValidationOperationError
from .types import (
    OperationChange,
    OperationError,
    OperationMeta,
    OperationMode,
    OperationResult,
    OperationStatus,
    OperationTarget,
)


POINT_PREFIX = "WEB_POINT:"
POINT_KIND_MAP = {
    "bolt": "socket",
    "droplet": "plumbing",
    "flame": "pipe",
}
KIND_POINT_MAP = {v: k for k, v in POINT_KIND_MAP.items()}


@dataclass(frozen=True)
class WallOperationConstraints:
    min_x_mm: float = 0.0
    max_x_mm: float = 10000.0
    min_y_mm: float = 0.0
    max_y_mm: float = 10000.0


class WallOperations:
    SCHEMA_VERSION = "1.0"

    def __init__(
        self,
        repository: WallRepository | None = None,
        constraints: WallOperationConstraints | None = None,
    ) -> None:
        self._repository = repository if repository is not None else JsonWallRepository()
        self._constraints = constraints if constraints is not None else WallOperationConstraints()

    def execute(
        self,
        action: str,
        *,
        target: str | Dict[str, Any] | OperationTarget,
        params: Dict[str, Any] | None = None,
        mode: OperationMode = "preview",
        source: str = "unknown",
    ) -> OperationResult:
        normalized = str(action or "").strip().lower()
        payload = dict(params or {})

        if normalized in {"wall.add_point", "add_point"}:
            return self.add_point(target, payload, mode=mode, source=source)
        if normalized in {"wall.remove_point", "remove_point"}:
            return self.remove_point(target, payload, mode=mode, source=source)

        return self._error_result(
            action=str(action or ""),
            target=self._target_from_input(target),
            mode=mode,
            status="validation_error",
            source=source,
            errors=[OperationError(code="UNSUPPORTED_ACTION", message=f"Unsupported action: {action}")],
        )

    def add_point(
        self,
        target: str | Dict[str, Any] | OperationTarget,
        params: Dict[str, Any],
        *,
        mode: OperationMode,
        source: str,
    ) -> OperationResult:
        action = "wall.add_point"
        input_target = self._target_from_input(target)
        try:
            wall = self._resolve_wall(target)
            point_type = str(params.get("point_type", "") or "").strip().lower()
            kind = POINT_KIND_MAP.get(point_type, "")
            if not kind:
                raise ValidationOperationError(
                    message=f"Unsupported point type: {point_type}",
                    code="UNSUPPORTED_POINT_TYPE",
                    path="params.point_type",
                )

            x_mm = float(params.get("x_mm", 0.0) or 0.0)
            y_mm = float(params.get("y_mm", 0.0) or 0.0)
            self._validate_xy(x_mm, y_mm)

            point_id = str(params.get("point_id", "") or "").strip() or uuid.uuid4().hex[:8]
            obstacle_name = f"{POINT_PREFIX}{point_id}"

            preview = self._clone_wall(wall)
            preview.obstacles.append(
                WallObstacleDef(
                    kind=kind,
                    wall_side="A",
                    name=obstacle_name,
                    x_mm=x_mm,
                    bottom_offset_mm=y_mm,
                    width_mm=80.0,
                    height_mm=80.0,
                    depth_mm=50.0,
                )
            )

            target_ref = self._wall_target(preview)
            changes = [
                OperationChange(
                    path=f"wall.points.{point_id}",
                    label=f"Wall point ({point_type})",
                    before=None,
                    after={"id": point_id, "type": point_type, "x": x_mm, "y": y_mm},
                    kind="add",
                    target_ref=target_ref,
                )
            ]

            if mode == "apply":
                self._repository.save(preview)
                return self._ok_result(
                    action=action, target=target_ref, mode=mode, source=source, changes=changes, can_apply=False
                )
            return self._ok_result(
                action=action, target=target_ref, mode=mode, source=source, changes=changes, can_apply=True
            )
        except ValidationOperationError as exc:
            return self._error_result(
                action=action,
                target=input_target,
                mode=mode,
                status="validation_error",
                source=source,
                errors=[OperationError(code=exc.code, message=exc.message, path=exc.path)],
            )
        except Exception as exc:
            return self._error_result(
                action=action,
                target=input_target,
                mode=mode,
                status="error",
                source=source,
                errors=[OperationError(code="INTERNAL_ERROR", message=str(exc))],
            )

    def remove_point(
        self,
        target: str | Dict[str, Any] | OperationTarget,
        params: Dict[str, Any],
        *,
        mode: OperationMode,
        source: str,
    ) -> OperationResult:
        action = "wall.remove_point"
        input_target = self._target_from_input(target)
        try:
            wall = self._resolve_wall(target)
            point_id = str(params.get("point_id", "") or "").strip()
            if not point_id:
                raise ValidationOperationError(
                    message="point_id is required",
                    code="MISSING_FIELD",
                    path="params.point_id",
                )

            index, point_type, before_payload = self._find_point(wall, point_id)
            if index < 0:
                raise ValidationOperationError(
                    message=f"Wall point not found: {point_id}",
                    code="POINT_NOT_FOUND",
                    path="params.point_id",
                )

            preview = self._clone_wall(wall)
            preview.obstacles.pop(index)
            target_ref = self._wall_target(preview)
            changes = [
                OperationChange(
                    path=f"wall.points.{point_id}",
                    label=f"Wall point ({point_type})",
                    before=before_payload,
                    after=None,
                    kind="remove",
                    target_ref=target_ref,
                )
            ]

            if mode == "apply":
                self._repository.save(preview)
                return self._ok_result(
                    action=action, target=target_ref, mode=mode, source=source, changes=changes, can_apply=False
                )
            return self._ok_result(
                action=action, target=target_ref, mode=mode, source=source, changes=changes, can_apply=True
            )
        except ValidationOperationError as exc:
            return self._error_result(
                action=action,
                target=input_target,
                mode=mode,
                status="validation_error",
                source=source,
                errors=[OperationError(code=exc.code, message=exc.message, path=exc.path)],
            )
        except Exception as exc:
            return self._error_result(
                action=action,
                target=input_target,
                mode=mode,
                status="error",
                source=source,
                errors=[OperationError(code="INTERNAL_ERROR", message=str(exc))],
            )

    def get_points(self, wall_name: str) -> Dict[str, Any]:
        wall = self._ensure_wall_exists(wall_name)
        points = []
        for obs in list(getattr(wall, "obstacles", []) or []):
            point_id = self._extract_point_id(str(getattr(obs, "name", "") or ""))
            if not point_id:
                continue
            point_type = KIND_POINT_MAP.get(str(getattr(obs, "kind", "") or "").strip().lower(), "bolt")
            points.append(
                {
                    "id": point_id,
                    "type": point_type,
                    "x": float(getattr(obs, "x_mm", 0.0) or 0.0),
                    "y": float(getattr(obs, "bottom_offset_mm", 0.0) or 0.0),
                }
            )
        return {"name": wall.name, "points": points}

    def _resolve_wall(self, target: str | Dict[str, Any] | OperationTarget) -> WallLayoutDef:
        resolved_target = self._target_from_input(target)
        wall_name = str(resolved_target.name or "").strip() or str(resolved_target.id or "").strip()
        if not wall_name:
            raise NotFoundOperationError(message="Wall target not provided", path="target")
        wall = self._repository.get_by_name(wall_name)
        if wall is None:
            wall = WallLayoutDef(wall_id=new_wall_id(), name=wall_name)
            self._repository.save(wall)
        return wall

    def _ensure_wall_exists(self, wall_name: str) -> WallLayoutDef:
        wall = self._repository.get_by_name(str(wall_name or "").strip())
        if wall is None:
            wall = WallLayoutDef(wall_id=new_wall_id(), name=str(wall_name or ""))
            self._repository.save(wall)
        return wall

    @staticmethod
    def _clone_wall(wall: WallLayoutDef) -> WallLayoutDef:
        return WallLayoutDef.from_dict(wall.to_dict())

    @staticmethod
    def _extract_point_id(name: str) -> str:
        raw = str(name or "")
        if not raw.startswith(POINT_PREFIX):
            return ""
        return raw[len(POINT_PREFIX) :].strip()

    def _find_point(self, wall: WallLayoutDef, point_id: str) -> Tuple[int, str, Dict[str, Any]]:
        obstacles = list(getattr(wall, "obstacles", []) or [])
        for idx, obs in enumerate(obstacles):
            current_id = self._extract_point_id(str(getattr(obs, "name", "") or ""))
            if current_id != point_id:
                continue
            point_type = KIND_POINT_MAP.get(str(getattr(obs, "kind", "") or "").strip().lower(), "bolt")
            payload = {
                "id": point_id,
                "type": point_type,
                "x": float(getattr(obs, "x_mm", 0.0) or 0.0),
                "y": float(getattr(obs, "bottom_offset_mm", 0.0) or 0.0),
            }
            return idx, point_type, payload
        return -1, "", {}

    def _validate_xy(self, x_mm: float, y_mm: float) -> None:
        if x_mm < self._constraints.min_x_mm or x_mm > self._constraints.max_x_mm:
            raise ValidationOperationError(
                message=(
                    f"x_mm out of range ({self._constraints.min_x_mm:g}-"
                    f"{self._constraints.max_x_mm:g})"
                ),
                code="OUT_OF_RANGE",
                path="params.x_mm",
            )
        if y_mm < self._constraints.min_y_mm or y_mm > self._constraints.max_y_mm:
            raise ValidationOperationError(
                message=(
                    f"y_mm out of range ({self._constraints.min_y_mm:g}-"
                    f"{self._constraints.max_y_mm:g})"
                ),
                code="OUT_OF_RANGE",
                path="params.y_mm",
            )

    def _target_from_input(self, target: str | Dict[str, Any] | OperationTarget) -> OperationTarget:
        if isinstance(target, OperationTarget):
            return target
        if isinstance(target, str):
            raw = str(target or "").strip()
            return OperationTarget(type="wall", id=raw, name=raw)
        if isinstance(target, dict):
            return OperationTarget(
                type="wall",
                id=str(target.get("id", "") or ""),
                name=str(target.get("name", "") or ""),
                scope=str(target.get("scope", "") or ""),
            )
        return OperationTarget(type="wall")

    @staticmethod
    def _wall_target(wall: WallLayoutDef) -> OperationTarget:
        return OperationTarget(type="wall", id=str(getattr(wall, "wall_id", "") or ""), name=str(wall.name or ""))

    def _ok_result(
        self,
        *,
        action: str,
        target: OperationTarget,
        mode: OperationMode,
        source: str,
        changes: list[OperationChange],
        can_apply: bool,
    ) -> OperationResult:
        return OperationResult(
            version=self.SCHEMA_VERSION,
            status="ok",
            mode=mode,
            action=action,
            target=target,
            warnings=[],
            errors=[],
            changes=list(changes or []),
            can_apply=bool(can_apply),
            meta=OperationMeta(source=source),
        )

    def _error_result(
        self,
        *,
        action: str,
        target: OperationTarget,
        mode: OperationMode,
        status: OperationStatus,
        source: str,
        errors: list[OperationError],
    ) -> OperationResult:
        return OperationResult(
            version=self.SCHEMA_VERSION,
            status=status,
            mode=mode,
            action=action,
            target=target,
            warnings=[],
            errors=list(errors or []),
            changes=[],
            can_apply=False,
            meta=OperationMeta(source=source),
        )

