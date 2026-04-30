from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from src.core.module_parts_service import build_module_parts
from src.domain.module_models import ModuleDef
from src.storage.catalog_store_json import CatalogStoreJson

from .adapters.module_repository import JsonModuleRepository, ModuleRepository
from .errors import DomainOperationError, NotFoundOperationError, ValidationOperationError
from .types import (
    OperationChange,
    OperationError,
    OperationMeta,
    OperationMode,
    OperationResult,
    OperationStatus,
    OperationTarget,
)


@dataclass(frozen=True)
class ModuleDimensionConstraints:
    depth_min_mm: float = 100.0
    depth_max_mm: float = 1200.0
    width_min_mm: float = 150.0
    width_max_mm: float = 2800.0
    height_min_mm: float = 100.0
    height_max_mm: float = 2500.0
    shelf_count_min: int = 0
    shelf_count_max: int = 24


class ModuleOperations:
    SCHEMA_VERSION = "1.0"

    def __init__(
        self,
        repository: ModuleRepository | None = None,
        catalog: CatalogStoreJson | None = None,
        constraints: ModuleDimensionConstraints | None = None,
    ) -> None:
        self._repository = repository if repository is not None else JsonModuleRepository()
        self._catalog = catalog if catalog is not None else CatalogStoreJson()
        self._constraints = constraints if constraints is not None else ModuleDimensionConstraints()

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

        if normalized in {"module.set_depth", "set_depth"}:
            return self.set_depth(target, depth_mm=payload.get("depth_mm"), mode=mode, source=source)
        if normalized in {"module.set_width", "set_width"}:
            return self.set_width(target, width_mm=payload.get("width_mm"), mode=mode, source=source)
        if normalized in {"module.set_height", "set_height"}:
            return self.set_height(target, height_mm=payload.get("height_mm"), mode=mode, source=source)
        if normalized in {"module.add_shelves", "add_shelves"}:
            return self.add_shelves(target, delta_count=payload.get("delta_count"), mode=mode, source=source)
        if normalized in {"module.change_material", "change_material"}:
            return self.change_material(
                target,
                material_key=payload.get("material_key"),
                part_group=payload.get("part_group", "carcass"),
                mode=mode,
                source=source,
            )
        if normalized in {"module.set_material", "set_material"}:
            return self.set_material(
                target,
                material_id=payload.get("material_id"),
                mode=mode,
                source=source,
            )
        if normalized in {"module.change_edgeband", "change_edgeband"}:
            return self.change_edgeband(
                target,
                edgeband_key=payload.get("edgeband_key"),
                part_group=payload.get("part_group", "carcass"),
                mode=mode,
                source=source,
            )
        if normalized in {"module.update_properties", "update_properties"}:
            return self.update_properties(
                target,
                properties=payload,
                mode=mode,
                source=source,
            )
        if normalized in {"module.update_part", "update_part"}:
            return self.update_part(
                target,
                part_id=payload.get("part_id"),
                properties=payload.get("properties", {}),
                mode=mode,
                source=source,
            )
        if normalized in {"module.apply_scheme", "apply_scheme"}:
            return self.apply_scheme(
                target,
                scheme_key=payload.get("scheme_key"),
                mode=mode,
                source=source,
            )

        return self._error_result(
            action=str(action or ""),
            target=self._target_from_input(target),
            mode=mode,
            status="validation_error",
            source=source,
            errors=[OperationError(code="UNSUPPORTED_ACTION", message=f"Unsupported action: {action}")],
        )

    def set_depth(
        self,
        target: str | Dict[str, Any] | OperationTarget,
        *,
        depth_mm: Any,
        mode: OperationMode = "preview",
        source: str = "unknown",
    ) -> OperationResult:
        return self._set_dimension(
            action="module.set_depth",
            path="module.depth_mm",
            label="Module depth",
            target=target,
            value=depth_mm,
            min_value=self._constraints.depth_min_mm,
            max_value=self._constraints.depth_max_mm,
            attr="depth_mm",
            unit="mm",
            mode=mode,
            source=source,
        )

    def set_width(
        self,
        target: str | Dict[str, Any] | OperationTarget,
        *,
        width_mm: Any,
        mode: OperationMode = "preview",
        source: str = "unknown",
    ) -> OperationResult:
        return self._set_dimension(
            action="module.set_width",
            path="module.width_mm",
            label="Module width",
            target=target,
            value=width_mm,
            min_value=self._constraints.width_min_mm,
            max_value=self._constraints.width_max_mm,
            attr="width_mm",
            unit="mm",
            mode=mode,
            source=source,
        )

    def set_height(
        self,
        target: str | Dict[str, Any] | OperationTarget,
        *,
        height_mm: Any,
        mode: OperationMode = "preview",
        source: str = "unknown",
    ) -> OperationResult:
        return self._set_dimension(
            action="module.set_height",
            path="module.height_mm",
            label="Module height",
            target=target,
            value=height_mm,
            min_value=self._constraints.height_min_mm,
            max_value=self._constraints.height_max_mm,
            attr="height_mm",
            unit="mm",
            mode=mode,
            source=source,
        )

    def add_shelves(
        self,
        target: str | Dict[str, Any] | OperationTarget,
        *,
        delta_count: Any,
        mode: OperationMode = "preview",
        source: str = "unknown",
    ) -> OperationResult:
        action = "module.add_shelves"
        input_target = self._target_from_input(target)
        try:
            module = self._resolve_module(target)
            delta = int(delta_count)
            new_count = int(module.shelf_count) + delta
            if new_count < self._constraints.shelf_count_min or new_count > self._constraints.shelf_count_max:
                raise ValidationOperationError(
                    message=(
                        "Shelf count out of range "
                        f"({self._constraints.shelf_count_min}-{self._constraints.shelf_count_max})"
                    ),
                    code="OUT_OF_RANGE",
                    path="module.shelf_count",
                )

            preview = self._clone_module(module)
            preview.shelf_count = int(new_count)
            preview.parts = build_module_parts(preview, self._catalog)

            target_ref = self._module_target(preview)
            changes = [
                OperationChange(
                    path="module.shelf_count",
                    label="Shelf count",
                    before=int(module.shelf_count),
                    after=int(preview.shelf_count),
                    unit="pcs",
                    kind="update",
                    target_ref=target_ref,
                )
            ]

            if mode == "apply":
                self._repository.save(preview)
                return self._ok_result(
                    action=action,
                    target=target_ref,
                    mode=mode,
                    source=source,
                    changes=changes,
                    can_apply=False,
                )

            return self._ok_result(
                action=action,
                target=target_ref,
                mode=mode,
                source=source,
                changes=changes,
                can_apply=True,
            )
        except DomainOperationError as exc:
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

    def change_material(
        self,
        target: str | Dict[str, Any] | OperationTarget,
        *,
        material_key: Any,
        part_group: Any = "carcass",
        mode: OperationMode = "preview",
        source: str = "unknown",
    ) -> OperationResult:
        action = "module.change_material"
        input_target = self._target_from_input(target)

        try:
            module = self._resolve_module(target)
            material = str(material_key or "").strip()
            group = str(part_group or "").strip().lower()

            if not material:
                raise ValidationOperationError(
                    message="Material key is required",
                    code="MISSING_FIELD",
                    path="module.materials",
                )
            if not group:
                raise ValidationOperationError(
                    message="Part group is required",
                    code="MISSING_FIELD",
                    path="module.materials",
                )
            if self._catalog.get_material(material) is None:
                raise ValidationOperationError(
                    message=f"Unknown material key: {material}",
                    code="UNKNOWN_MATERIAL",
                    path=f"module.materials.{group}",
                )

            preview = self._clone_module(module)
            before = str(preview.materials.get(group, "") or "")
            preview.materials[group] = material
            preview.parts = build_module_parts(preview, self._catalog)

            target_ref = self._module_target(preview)
            changes = [
                OperationChange(
                    path=f"module.materials.{group}",
                    label=f"Material ({group})",
                    before=before,
                    after=material,
                    unit="",
                    kind="update",
                    target_ref=target_ref,
                )
            ]

            if mode == "apply":
                self._repository.save(preview)
                return self._ok_result(
                    action=action,
                    target=target_ref,
                    mode=mode,
                    source=source,
                    changes=changes,
                    can_apply=False,
                )

            return self._ok_result(
                action=action,
                target=target_ref,
                mode=mode,
                source=source,
                changes=changes,
                can_apply=True,
            )
        except DomainOperationError as exc:
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

    def change_edgeband(
        self,
        target: str | Dict[str, Any] | OperationTarget,
        *,
        edgeband_key: Any,
        part_group: Any = "carcass",
        mode: OperationMode = "preview",
        source: str = "unknown",
    ) -> OperationResult:
        action = "module.change_edgeband"
        input_target = self._target_from_input(target)

        try:
            module = self._resolve_module(target)
            edgeband = str(edgeband_key or "").strip()
            group = str(part_group or "").strip().lower()

            if not edgeband:
                raise ValidationOperationError(
                    message="Edgeband key is required",
                    code="MISSING_FIELD",
                    path="module.edgebands",
                )
            
            # For now we use the same catalog for edgebands as materials
            if self._catalog.get_material(edgeband) is None:
                 raise ValidationOperationError(
                    message=f"Unknown edgeband key: {edgeband}",
                    code="UNKNOWN_EDGEBAND",
                    path=f"module.edgebands.{group}",
                )

            preview = self._clone_module(module)
            before = str(preview.edgebands.get(group, "") or "")
            preview.edgebands[group] = edgeband
            
            target_ref = self._module_target(preview)
            changes = [
                OperationChange(
                    path=f"module.edgebands.{group}",
                    label=f"Edgeband ({group})",
                    before=before,
                    after=edgeband,
                    unit="",
                    kind="update",
                    target_ref=target_ref,
                )
            ]

            if mode == "apply":
                self._repository.save(preview)
                return self._ok_result(
                    action=action,
                    target=target_ref,
                    mode=mode,
                    source=source,
                    changes=changes,
                    can_apply=False,
                )

            return self._ok_result(
                action=action,
                target=target_ref,
                mode=mode,
                source=source,
                changes=changes,
                can_apply=True,
            )
        except DomainOperationError as exc:
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

    def _set_dimension(
        self,
        *,
        action: str,
        path: str,
        label: str,
        target: str | Dict[str, Any] | OperationTarget,
        value: Any,
        min_value: float,
        max_value: float,
        attr: str,
        unit: str,
        mode: OperationMode,
        source: str,
    ) -> OperationResult:
        input_target = self._target_from_input(target)
        try:
            module = self._resolve_module(target)
            new_value = float(value)
            if new_value < float(min_value) or new_value > float(max_value):
                raise ValidationOperationError(
                    message=f"Value out of range ({min_value:g}-{max_value:g} {unit})",
                    code="OUT_OF_RANGE",
                    path=path,
                )

            preview = self._clone_module(module)
            before = float(getattr(preview, attr))
            setattr(preview, attr, float(new_value))
            preview.parts = build_module_parts(preview, self._catalog)

            target_ref = self._module_target(preview)
            changes = [
                OperationChange(
                    path=path,
                    label=label,
                    before=before,
                    after=float(getattr(preview, attr)),
                    unit=unit,
                    kind="update",
                    target_ref=target_ref,
                )
            ]

            if mode == "apply":
                self._repository.save(preview)
                return self._ok_result(
                    action=action,
                    target=target_ref,
                    mode=mode,
                    source=source,
                    changes=changes,
                    can_apply=False,
                )

            return self._ok_result(
                action=action,
                target=target_ref,
                mode=mode,
                source=source,
                changes=changes,
                can_apply=True,
            )
        except DomainOperationError as exc:
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


    def update_part(
        self,
        target: str | Dict[str, Any] | OperationTarget,
        *,
        part_id: str,
        properties: Dict[str, Any],
        mode: OperationMode = "preview",
        source: str = "unknown",
    ) -> OperationResult:
        action = "module.update_part"
        input_target = self._target_from_input(target)

        try:
            module = self._resolve_module(target)
            preview = self._clone_module(module)
            
            if not part_id:
                raise ValidationOperationError(
                    message="Part ID is required",
                    code="MISSING_FIELD",
                    path="part_id",
                )

            if not preview.parts:
                from src.core.module_parts_service import build_module_parts
                preview.parts = build_module_parts(preview, self._catalog)

            part = preview.parts.get(part_id)
            if not part:
                raise ValidationOperationError(
                    message=f"Part {part_id} not found",
                    code="NOT_FOUND",
                    path=f"module.parts.{part_id}",
                )

            changes = []
            if "edge_banding" in properties:
                new_eb = properties["edge_banding"]
                before_eb = dict(part.edge_banding or {})
                part.edge_banding = dict(new_eb)
                changes.append(
                    OperationChange(
                        path=f"module.parts.{part_id}.edge_banding",
                        label=f"Okleiny dla {part.name_pl}",
                        before=before_eb,
                        after=new_eb,
                        unit="",
                        kind="update",
                        target_ref=self._module_target(preview),
                    )
                )
            
            if "material_override_key" in properties:
                val = str(properties["material_override_key"] or "").strip()
                before_mat = part.material_override_key
                if before_mat != val:
                    part.material_override_key = val
                    part.material_key = val if val else part.material_key
                    changes.append(
                        OperationChange(
                            path=f"module.parts.{part_id}.material_override_key",
                            label=f"Material Nadpisanie dla {part.name_pl}",
                            before=before_mat,
                            after=val,
                            unit="",
                            kind="update",
                            target_ref=self._module_target(preview),
                        )
                    )

            if "grain_direction" in properties:
                val = str(properties["grain_direction"] or "none").strip()
                before_grain = part.grain_direction
                if before_grain != val:
                    part.grain_direction = val
                    changes.append(
                        OperationChange(
                            path=f"module.parts.{part_id}.grain_direction",
                            label=f"SĹ‚oje dla {part.name_pl}",
                            before=before_grain,
                            after=val,
                            unit="",
                            kind="update",
                            target_ref=self._module_target(preview),
                        )
                    )

            if "veneer_active" in properties:
                val = bool(properties["veneer_active"])
                before_val = bool(part.veneer_active)
                if before_val != val:
                    part.veneer_active = val
                    changes.append(
                        OperationChange(
                            path=f"module.parts.{part_id}.veneer_active",
                            label=f"Fornir dla {part.name_pl}",
                            before=before_val,
                            after=val,
                            unit="",
                            kind="update",
                            target_ref=self._module_target(preview),
                        )
                    )

            if "lacquer_active" in properties:
                val = bool(properties["lacquer_active"])
                before_val = bool(part.lacquer_active)
                if before_val != val:
                    part.lacquer_active = val
                    changes.append(
                        OperationChange(
                            path=f"module.parts.{part_id}.lacquer_active",
                            label=f"Lakier dla {part.name_pl}",
                            before=before_val,
                            after=val,
                            unit="",
                            kind="update",
                            target_ref=self._module_target(preview),
                        )
                    )

            if not changes:
                 return self._ok_result(action=action, target=self._module_target(module), mode=mode, source=source, changes=[], can_apply=True)
            
            if mode == "apply":
                self._repository.save(preview)
                return self._ok_result(
                    action=action,
                    target=self._module_target(preview),
                    mode=mode,
                    source=source,
                    changes=changes,
                    can_apply=False,
                )

            return self._ok_result(
                action=action,
                target=self._module_target(preview),
                mode=mode,
                source=source,
                changes=changes,
                can_apply=True,
            )
        except DomainOperationError as exc:
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

    def apply_scheme(
        self,
        target: str | Dict[str, Any] | OperationTarget,
        *,
        scheme_key: str,
        mode: OperationMode = "preview",
        source: str = "unknown",
    ) -> OperationResult:
        action = "module.apply_scheme"
        input_target = self._target_from_input(target)

        schemes = {
            "standard": {
                "carcass_joint_type": "minifix",
                "carcass_joint_type_bottom": "type2",
                "carcass_top_mode": "full",
                "back_mounting_mode": "insert",
                "hinge_vendor": "blum",
                "drawer_vendor": "blum_tandembox"
            },
            "production": {
                "carcass_joint_type": "confirmat",
                "carcass_joint_type_bottom": "type2",
                "carcass_top_mode": "rails_h",
                "back_mounting_mode": "overlay",
                "hinge_vendor": "gtv",
                "drawer_vendor": "gtv_modernbox"
            },
            "modern_clamex": {
                "carcass_joint_type": "clamex",
                "carcass_joint_type_bottom": "clamex",
                "carcass_top_mode": "full",
                "back_mounting_mode": "recess",
                "hinge_vendor": "blum",
                "drawer_vendor": "blum_legrabox"
            }
        }

        scheme_props = schemes.get(scheme_key)
        if not scheme_props:
             return self._error_result(action=action, target=input_target, mode=mode, status="validation_error", source=source, errors=[OperationError(code="INVALID_SCHEME", message=f"Unknown scheme: {scheme_key}")])

        return self.update_properties(target, properties=scheme_props, mode=mode, source=source)

    def update_properties(
        self,
        target: str | Dict[str, Any] | OperationTarget,
        *,
        properties: Dict[str, Any],
        mode: OperationMode = "preview",
        source: str = "unknown",
    ) -> OperationResult:
        action = "module.update_properties"
        input_target = self._target_from_input(target)

        try:
            module = self._resolve_module(target)
            preview = self._clone_module(module)
            
            changes = []
            allowed_fields = {
                "name", "code", "description", "notes", "quantity", "angle_deg",
                "shelf_count", "divider_count", "drawer_count", 
                "carcass_top_mode", "carcass_bottom_mode", "back_mounting_mode",
                "hinge_vendor", "drawer_vendor", "facade_mode", "front_grain_direction",
                "back_recess_depth_mm", "back_clearance_mm",
                "carcass_joint_type", "leg_type", "legs_height_mm",
                "leg_offset_front", "leg_offset_back", "leg_offset_side",
                "has_plinth", "plinth_height_mm", "plinth_inset_mm",
                "front_gap_top", "front_gap_bottom", "front_gap_left", "front_gap_right",
                "top_rail_offset_mm", "bottom_rail_offset_mm",
                "handle_type", "handle_length", "handle_orientation", "handle_pos_x", "handle_pos_y",
                "lock_dimensions", "visible_in_projection", "drawer_guide_type",
                "cabinet_kind", "cabinet_type"
            }

            for key, value in properties.items():
                if key.startswith("finish_"):
                    # Special handling for finishes
                    f_key = key.replace("finish_", "")
                    before = preview.materials_finish.get(f_key, False)
                    preview.materials_finish[f_key] = bool(value)
                    if before != bool(value):
                        changes.append(
                            OperationChange(
                                path=f"module.materials_finish.{f_key}",
                                label=f"Wykończenie: {f_key.replace('_', ' ').title()}",
                                before=before,
                                after=bool(value),
                                unit="",
                                kind="update",
                                target_ref=self._module_target(preview),
                            )
                        )
                    continue

                if key not in allowed_fields:
                    continue
                
                # Alias handling
                if key == "cabinet_type":
                    key = "cabinet_kind"
                
                before = getattr(preview, key, None)
                # Auto-cast based on existing type
                if isinstance(before, int):
                    value = int(value or 0)
                elif isinstance(before, float):
                    value = float(value or 0.0)
                
                if before == value:
                    continue
                    
                setattr(preview, key, value)
                changes.append(
                    OperationChange(
                        path=f"module.{key}",
                        label=key.replace("_", " ").title(),
                        before=before,
                        after=value,
                        unit="",
                        kind="update",
                        target_ref=self._module_target(preview),
                    )
                )

            if not changes:
                 return self._ok_result(action=action, target=self._module_target(module), mode=mode, source=source, changes=[], can_apply=True)

            # Rebuild parts after property changes
            preview.parts = build_module_parts(preview, self._catalog)
            
            if mode == "apply":
                self._repository.save(preview)
                return self._ok_result(
                    action=action,
                    target=self._module_target(preview),
                    mode=mode,
                    source=source,
                    changes=changes,
                    can_apply=False,
                )

            return self._ok_result(
                action=action,
                target=self._module_target(preview),
                mode=mode,
                source=source,
                changes=changes,
                can_apply=True,
            )
        except DomainOperationError as exc:
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

    def _resolve_module(self, target: str | Dict[str, Any] | OperationTarget) -> ModuleDef:
        resolved_target = self._target_from_input(target)

        module = None
        if str(resolved_target.id or "").strip():
            module = self._repository.get_by_id(str(resolved_target.id))
        if module is None and str(resolved_target.name or "").strip():
            module = self._repository.get_by_name(str(resolved_target.name))
        if module is None:
            raise NotFoundOperationError(message="Module target not found", path="target")
        return module

    @staticmethod
    def _clone_module(module: ModuleDef) -> ModuleDef:
        return ModuleDef.from_dict(module.to_dict())

    def _target_from_input(self, target: str | Dict[str, Any] | OperationTarget) -> OperationTarget:
        if isinstance(target, OperationTarget):
            return target
        if isinstance(target, str):
            raw = str(target or "").strip()
            return OperationTarget(type="module", id=raw, name=raw)
        if isinstance(target, dict):
            return OperationTarget(
                type="module",
                id=str(target.get("id", "") or ""),
                name=str(target.get("name", "") or ""),
                scope=str(target.get("scope", "") or ""),
            )
        return OperationTarget(type="module")

    @staticmethod
    def _module_target(module: ModuleDef) -> OperationTarget:
        return OperationTarget(
            type="module",
            id=str(getattr(module, "module_id", "") or ""),
            name=str(getattr(module, "name", "") or ""),
        )

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

    def set_material(
        self,
        target: str | Dict[str, Any] | OperationTarget,
        *,
        material_id: Any,
        mode: OperationMode = "preview",
        source: str = "unknown",
    ) -> OperationResult:
        action = "module.set_material"
        input_target = self._target_from_input(target)

        try:
            module = self._resolve_module(target)
            m_id = material_id
            if m_id is None:
                raise ValidationOperationError(
                    message="Material ID is required",
                    code="MISSING_FIELD",
                    path="module.material_id",
                )

            preview = self._clone_module(module)
            before = preview.material_id
            preview.material_id = int(m_id)

            target_ref = self._module_target(preview)
            changes = [
                OperationChange(
                    path="module.material_id",
                    label="Material",
                    before=before,
                    after=preview.material_id,
                    unit="id",
                    kind="update",
                    target_ref=target_ref,
                )
            ]

            if mode == "apply":
                self._repository.save(preview)
                return self._ok_result(
                    action=action,
                    target=target_ref,
                    mode=mode,
                    source=source,
                    changes=changes,
                    can_apply=False,
                )

            return self._ok_result(
                action=action,
                target=target_ref,
                mode=mode,
                source=source,
                changes=changes,
                can_apply=True,
            )
        except DomainOperationError as exc:
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
