from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


def _clean_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return float(default)


def _clean_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except Exception:
        return int(default)


def _clean_str(value: Any) -> str:
    return str(value or "").strip()


@dataclass
class ProjectHeader:
    project_name: str = ""
    client_name: str = ""
    order_code: str = ""
    order_name: str = ""
    status: str = ""
    source_kind: str = ""
    source_path: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "client_name": self.client_name,
            "order_code": self.order_code,
            "order_name": self.order_name,
            "status": self.status,
            "source_kind": self.source_kind,
            "source_path": self.source_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectHeader":
        data = data or {}
        return cls(
            project_name=_clean_str(data.get("project_name", "")),
            client_name=_clean_str(data.get("client_name", "")),
            order_code=_clean_str(data.get("order_code", "")),
            order_name=_clean_str(data.get("order_name", "")),
            status=_clean_str(data.get("status", "")),
            source_kind=_clean_str(data.get("source_kind", "")),
            source_path=_clean_str(data.get("source_path", "")),
            created_at=_clean_str(data.get("created_at", "")),
            updated_at=_clean_str(data.get("updated_at", "")),
        )


@dataclass
class ProjectQuoteContext:
    mode: str = ""
    pricing_policy: str = ""
    margin_percent: float = 0.0
    vat_percent: float = 0.0
    transport_flat: float = 0.0
    montage_flat: float = 0.0
    labor_cost: float = 0.0
    policy_multiplier: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "pricing_policy": self.pricing_policy,
            "margin_percent": float(self.margin_percent),
            "vat_percent": float(self.vat_percent),
            "transport_flat": float(self.transport_flat),
            "montage_flat": float(self.montage_flat),
            "labor_cost": float(self.labor_cost),
            "policy_multiplier": float(self.policy_multiplier),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectQuoteContext":
        data = data or {}
        return cls(
            mode=_clean_str(data.get("mode", "")),
            pricing_policy=_clean_str(data.get("pricing_policy", "")),
            margin_percent=_clean_float(data.get("margin_percent", 0.0)),
            vat_percent=_clean_float(data.get("vat_percent", 0.0)),
            transport_flat=_clean_float(data.get("transport_flat", 0.0)),
            montage_flat=_clean_float(data.get("montage_flat", 0.0)),
            labor_cost=_clean_float(data.get("labor_cost", 0.0)),
            policy_multiplier=_clean_float(data.get("policy_multiplier", 1.0), 1.0),
        )


@dataclass
class ProjectAssembly:
    assembly_id: str = ""
    name: str = ""
    order_name: str = ""
    client_name: str = ""
    wall_name: str = ""
    width_mm: float = 0.0
    height_mm: float = 0.0
    depth_mm: float = 0.0
    gap_mm: float = 0.0
    material_profile_key: str = ""
    labor_cost_pln: float = 0.0
    transport_cost_pln: float = 0.0
    montage_cost_pln: float = 0.0
    margin_percent: float = 0.0
    items: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assembly_id": self.assembly_id,
            "name": self.name,
            "order_name": self.order_name,
            "client_name": self.client_name,
            "wall_name": self.wall_name,
            "width_mm": float(self.width_mm),
            "height_mm": float(self.height_mm),
            "depth_mm": float(self.depth_mm),
            "gap_mm": float(self.gap_mm),
            "material_profile_key": self.material_profile_key,
            "labor_cost_pln": float(self.labor_cost_pln),
            "transport_cost_pln": float(self.transport_cost_pln),
            "montage_cost_pln": float(self.montage_cost_pln),
            "margin_percent": float(self.margin_percent),
            "items": [dict(item) for item in self.items if isinstance(item, dict)],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectAssembly":
        data = data or {}
        raw_items = data.get("items", []) or []
        return cls(
            assembly_id=_clean_str(data.get("assembly_id", "")),
            name=_clean_str(data.get("name", "")),
            order_name=_clean_str(data.get("order_name", "")),
            client_name=_clean_str(data.get("client_name", "")),
            wall_name=_clean_str(data.get("wall_name", "")),
            width_mm=_clean_float(data.get("width_mm", 0.0)),
            height_mm=_clean_float(data.get("height_mm", 0.0)),
            depth_mm=_clean_float(data.get("depth_mm", 0.0)),
            gap_mm=_clean_float(data.get("gap_mm", 0.0)),
            material_profile_key=_clean_str(data.get("material_profile_key", "")),
            labor_cost_pln=_clean_float(data.get("labor_cost_pln", 0.0)),
            transport_cost_pln=_clean_float(data.get("transport_cost_pln", 0.0)),
            montage_cost_pln=_clean_float(data.get("montage_cost_pln", 0.0)),
            margin_percent=_clean_float(data.get("margin_percent", 0.0)),
            items=[dict(item) for item in raw_items if isinstance(item, dict)],
        )


@dataclass
class ProjectQuoteLine:
    line_id: str = ""
    source_kind: str = ""
    source_ref: str = ""
    group: str = ""
    module_name: str = ""
    position_name: str = ""
    qty: float = 0.0
    unit: str = ""
    length_mm: float = 0.0
    width_mm: float = 0.0
    thickness_mm: float = 0.0
    material_name: str = ""
    edgeband_desc: str = ""
    cost_material: float = 0.0
    cost_edgeband: float = 0.0
    cost_labor: float = 0.0
    cost_extra: float = 0.0
    line_total: float = 0.0
    status: str = ""
    accuracy: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line_id": self.line_id,
            "source_kind": self.source_kind,
            "source_ref": self.source_ref,
            "group": self.group,
            "module_name": self.module_name,
            "position_name": self.position_name,
            "qty": float(self.qty),
            "unit": self.unit,
            "length_mm": float(self.length_mm),
            "width_mm": float(self.width_mm),
            "thickness_mm": float(self.thickness_mm),
            "material_name": self.material_name,
            "edgeband_desc": self.edgeband_desc,
            "cost_material": float(self.cost_material),
            "cost_edgeband": float(self.cost_edgeband),
            "cost_labor": float(self.cost_labor),
            "cost_extra": float(self.cost_extra),
            "line_total": float(self.line_total),
            "status": self.status,
            "accuracy": self.accuracy,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectQuoteLine":
        data = data or {}
        return cls(
            line_id=_clean_str(data.get("line_id", "")),
            source_kind=_clean_str(data.get("source_kind", "")),
            source_ref=_clean_str(data.get("source_ref", "")),
            group=_clean_str(data.get("group", "")),
            module_name=_clean_str(data.get("module_name", "")),
            position_name=_clean_str(data.get("position_name", "")),
            qty=_clean_float(data.get("qty", 0.0)),
            unit=_clean_str(data.get("unit", "")),
            length_mm=_clean_float(data.get("length_mm", 0.0)),
            width_mm=_clean_float(data.get("width_mm", 0.0)),
            thickness_mm=_clean_float(data.get("thickness_mm", 0.0)),
            material_name=_clean_str(data.get("material_name", "")),
            edgeband_desc=_clean_str(data.get("edgeband_desc", "")),
            cost_material=_clean_float(data.get("cost_material", 0.0)),
            cost_edgeband=_clean_float(data.get("cost_edgeband", 0.0)),
            cost_labor=_clean_float(data.get("cost_labor", 0.0)),
            cost_extra=_clean_float(data.get("cost_extra", 0.0)),
            line_total=_clean_float(data.get("line_total", 0.0)),
            status=_clean_str(data.get("status", "")),
            accuracy=_clean_str(data.get("accuracy", "")),
            note=_clean_str(data.get("note", "")),
        )


@dataclass
class ProjectServiceLine:
    service_id: str = ""
    service_name: str = ""
    source_kind: str = ""
    source_ref: str = ""
    qty: float = 1.0
    unit: str = "szt"
    amount: float = 0.0
    status: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "source_kind": self.source_kind,
            "source_ref": self.source_ref,
            "qty": float(self.qty),
            "unit": self.unit,
            "amount": float(self.amount),
            "status": self.status,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectServiceLine":
        data = data or {}
        return cls(
            service_id=_clean_str(data.get("service_id", "")),
            service_name=_clean_str(data.get("service_name", "")),
            source_kind=_clean_str(data.get("source_kind", "")),
            source_ref=_clean_str(data.get("source_ref", "")),
            qty=_clean_float(data.get("qty", 1.0), 1.0),
            unit=_clean_str(data.get("unit", "szt")) or "szt",
            amount=_clean_float(data.get("amount", 0.0)),
            status=_clean_str(data.get("status", "")),
            note=_clean_str(data.get("note", "")),
        )


@dataclass
class ProjectImport3D:
    project_path: str = ""
    project_name: str = ""
    project_date: str = ""
    project_version: str = ""
    module_name: str = ""
    module_length_mm: float = 0.0
    module_width_mm: float = 0.0
    module_height_mm: float = 0.0
    formatki_count: int = 0
    fronty_count: int = 0
    okucia_count: int = 0
    laczniki_count: int = 0
    operations_count: int = 0
    total_area_m2: float = 0.0
    total_edgeband_mb: float = 0.0
    import_status: str = ""
    control_rows: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_path": self.project_path,
            "project_name": self.project_name,
            "project_date": self.project_date,
            "project_version": self.project_version,
            "module_name": self.module_name,
            "module_length_mm": float(self.module_length_mm),
            "module_width_mm": float(self.module_width_mm),
            "module_height_mm": float(self.module_height_mm),
            "formatki_count": int(self.formatki_count),
            "fronty_count": int(self.fronty_count),
            "okucia_count": int(self.okucia_count),
            "laczniki_count": int(self.laczniki_count),
            "operations_count": int(self.operations_count),
            "total_area_m2": float(self.total_area_m2),
            "total_edgeband_mb": float(self.total_edgeband_mb),
            "import_status": self.import_status,
            "control_rows": [dict(row) for row in self.control_rows if isinstance(row, dict)],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectImport3D":
        data = data or {}
        return cls(
            project_path=_clean_str(data.get("project_path", "")),
            project_name=_clean_str(data.get("project_name", "")),
            project_date=_clean_str(data.get("project_date", "")),
            project_version=_clean_str(data.get("project_version", "")),
            module_name=_clean_str(data.get("module_name", "")),
            module_length_mm=_clean_float(data.get("module_length_mm", 0.0)),
            module_width_mm=_clean_float(data.get("module_width_mm", 0.0)),
            module_height_mm=_clean_float(data.get("module_height_mm", 0.0)),
            formatki_count=_clean_int(data.get("formatki_count", 0)),
            fronty_count=_clean_int(data.get("fronty_count", 0)),
            okucia_count=_clean_int(data.get("okucia_count", 0)),
            laczniki_count=_clean_int(data.get("laczniki_count", 0)),
            operations_count=_clean_int(data.get("operations_count", 0)),
            total_area_m2=_clean_float(data.get("total_area_m2", 0.0)),
            total_edgeband_mb=_clean_float(data.get("total_edgeband_mb", 0.0)),
            import_status=_clean_str(data.get("import_status", "")),
            control_rows=[dict(row) for row in (data.get("control_rows", []) or []) if isinstance(row, dict)],
        )


@dataclass
class ProjectMapping:
    material_map: Dict[str, str] = field(default_factory=dict)
    edgeband_map: Dict[str, str] = field(default_factory=dict)
    hardware_map: Dict[str, str] = field(default_factory=dict)
    operation_map: Dict[str, str] = field(default_factory=dict)
    mapping_status: str = ""
    last_saved_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material_map": dict(self.material_map),
            "edgeband_map": dict(self.edgeband_map),
            "hardware_map": dict(self.hardware_map),
            "operation_map": dict(self.operation_map),
            "mapping_status": self.mapping_status,
            "last_saved_at": self.last_saved_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectMapping":
        data = data or {}
        return cls(
            material_map=dict(data.get("material_map", {}) or {}),
            edgeband_map=dict(data.get("edgeband_map", {}) or {}),
            hardware_map=dict(data.get("hardware_map", {}) or {}),
            operation_map=dict(data.get("operation_map", {}) or {}),
            mapping_status=_clean_str(data.get("mapping_status", "")),
            last_saved_at=_clean_str(data.get("last_saved_at", "")),
        )


@dataclass
class ProjectGibLabResult:
    result_path: str = ""
    result_kind: str = ""
    real_sheets_count: int = 0
    real_area_m2: float = 0.0
    real_edgeband_mb: float = 0.0
    scrap_m2: float = 0.0
    leftovers: List[Dict[str, Any]] = field(default_factory=list)
    difference_vs_theory: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_path": self.result_path,
            "result_kind": self.result_kind,
            "real_sheets_count": int(self.real_sheets_count),
            "real_area_m2": float(self.real_area_m2),
            "real_edgeband_mb": float(self.real_edgeband_mb),
            "scrap_m2": float(self.scrap_m2),
            "leftovers": [dict(row) for row in self.leftovers if isinstance(row, dict)],
            "difference_vs_theory": dict(self.difference_vs_theory),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectGibLabResult":
        data = data or {}
        return cls(
            result_path=_clean_str(data.get("result_path", "")),
            result_kind=_clean_str(data.get("result_kind", "")),
            real_sheets_count=_clean_int(data.get("real_sheets_count", 0)),
            real_area_m2=_clean_float(data.get("real_area_m2", 0.0)),
            real_edgeband_mb=_clean_float(data.get("real_edgeband_mb", 0.0)),
            scrap_m2=_clean_float(data.get("scrap_m2", 0.0)),
            leftovers=[dict(row) for row in (data.get("leftovers", []) or []) if isinstance(row, dict)],
            difference_vs_theory=dict(data.get("difference_vs_theory", {}) or {}),
        )


@dataclass
class ProjectPricingSnapshot:
    technical_total: float = 0.0
    material_value: float = 0.0
    services_total: float = 0.0
    extras_total: float = 0.0
    base_total: float = 0.0
    sale_total: float = 0.0
    brutto_total: float = 0.0
    profit_total: float = 0.0
    computed_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "technical_total": float(self.technical_total),
            "material_value": float(self.material_value),
            "services_total": float(self.services_total),
            "extras_total": float(self.extras_total),
            "base_total": float(self.base_total),
            "sale_total": float(self.sale_total),
            "brutto_total": float(self.brutto_total),
            "profit_total": float(self.profit_total),
            "computed_at": self.computed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectPricingSnapshot":
        data = data or {}
        return cls(
            technical_total=_clean_float(data.get("technical_total", 0.0)),
            material_value=_clean_float(data.get("material_value", 0.0)),
            services_total=_clean_float(data.get("services_total", 0.0)),
            extras_total=_clean_float(data.get("extras_total", 0.0)),
            base_total=_clean_float(data.get("base_total", 0.0)),
            sale_total=_clean_float(data.get("sale_total", 0.0)),
            brutto_total=_clean_float(data.get("brutto_total", 0.0)),
            profit_total=_clean_float(data.get("profit_total", 0.0)),
            computed_at=_clean_str(data.get("computed_at", "")),
        )


@dataclass
class ProjectObstacle:
    id: str = ""
    type: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    depth: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "x": float(self.x),
            "y": float(self.y),
            "width": float(self.width),
            "height": float(self.height),
            "depth": float(self.depth),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectObstacle":
        data = data or {}
        return cls(
            id=_clean_str(data.get("id", "")),
            type=_clean_str(data.get("type", "")),
            x=_clean_float(data.get("x", 0.0)),
            y=_clean_float(data.get("y", 0.0)),
            width=_clean_float(data.get("width", 0.0)),
            height=_clean_float(data.get("height", 0.0)),
            depth=_clean_float(data.get("depth", 0.0)),
        )


@dataclass
class ProjectAudit:
    built_from: List[str] = field(default_factory=list)
    built_at: str = ""
    source_versions: List[str] = field(default_factory=list)
    adapter_name: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "built_from": list(self.built_from),
            "built_at": self.built_at,
            "source_versions": list(self.source_versions),
            "adapter_name": self.adapter_name,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectAudit":
        data = data or {}
        return cls(
            built_from=[_clean_str(x) for x in (data.get("built_from", []) or []) if _clean_str(x)],
            built_at=_clean_str(data.get("built_at", "")),
            source_versions=[_clean_str(x) for x in (data.get("source_versions", []) or []) if _clean_str(x)],
            adapter_name=_clean_str(data.get("adapter_name", "")),
            notes=_clean_str(data.get("notes", "")),
        )


@dataclass
class ProjectModel:
    project_id: str = ""
    project_name: str = ""
    project_type: str = ""
    status: str = ""
    created_at: str = ""
    updated_at: str = ""
    source: str = ""
    header: ProjectHeader = field(default_factory=ProjectHeader)
    quote_context: ProjectQuoteContext = field(default_factory=ProjectQuoteContext)
    assemblies: List[ProjectAssembly] = field(default_factory=list)
    quote_lines: List[ProjectQuoteLine] = field(default_factory=list)
    services: List[ProjectServiceLine] = field(default_factory=list)
    import_3d: ProjectImport3D = field(default_factory=ProjectImport3D)
    mapping: ProjectMapping = field(default_factory=ProjectMapping)
    giblab_result: ProjectGibLabResult = field(default_factory=ProjectGibLabResult)
    pricing_snapshot: ProjectPricingSnapshot = field(default_factory=ProjectPricingSnapshot)
    audit: ProjectAudit = field(default_factory=ProjectAudit)
    obstacles: List[ProjectObstacle] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "project_type": self.project_type,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "header": self.header.to_dict(),
            "quote_context": self.quote_context.to_dict(),
            "assemblies": [item.to_dict() for item in self.assemblies],
            "quote_lines": [item.to_dict() for item in self.quote_lines],
            "services": [item.to_dict() for item in self.services],
            "import_3d": self.import_3d.to_dict(),
            "mapping": self.mapping.to_dict(),
            "giblab_result": self.giblab_result.to_dict(),
            "pricing_snapshot": self.pricing_snapshot.to_dict(),
            "audit": self.audit.to_dict(),
            "obstacles": [item.to_dict() for item in self.obstacles],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectModel":
        data = data or {}
        return cls(
            project_id=_clean_str(data.get("project_id", "")),
            project_name=_clean_str(data.get("project_name", "")),
            project_type=_clean_str(data.get("project_type", "")),
            status=_clean_str(data.get("status", "")),
            created_at=_clean_str(data.get("created_at", "")),
            updated_at=_clean_str(data.get("updated_at", "")),
            source=_clean_str(data.get("source", "")),
            header=ProjectHeader.from_dict(data.get("header", {}) or {}),
            quote_context=ProjectQuoteContext.from_dict(data.get("quote_context", {}) or {}),
            assemblies=[ProjectAssembly.from_dict(item) for item in (data.get("assemblies", []) or []) if isinstance(item, dict)],
            quote_lines=[ProjectQuoteLine.from_dict(item) for item in (data.get("quote_lines", []) or []) if isinstance(item, dict)],
            services=[ProjectServiceLine.from_dict(item) for item in (data.get("services", []) or []) if isinstance(item, dict)],
            import_3d=ProjectImport3D.from_dict(data.get("import_3d", {}) or {}),
            mapping=ProjectMapping.from_dict(data.get("mapping", {}) or {}),
            giblab_result=ProjectGibLabResult.from_dict(data.get("giblab_result", {}) or {}),
            pricing_snapshot=ProjectPricingSnapshot.from_dict(data.get("pricing_snapshot", {}) or {}),
            audit=ProjectAudit.from_dict(data.get("audit", {}) or {}),
            obstacles=[ProjectObstacle.from_dict(item) for item in (data.get("obstacles", []) or []) if isinstance(item, dict)],
        )
