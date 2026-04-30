from __future__ import annotations
import signal
from fastapi import FastAPI, HTTPException, Response, UploadFile, File, Header, Depends, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, date, timedelta
import hashlib
import sys
import os
import re
import sqlite3
import json
import unicodedata
from pathlib import Path
from types import SimpleNamespace

# Dodajemy naszÄ… gĹ‚ĂłwnÄ… Ĺ›cieĹĽkÄ™ do sys.path, aby API mogĹ‚o korzystaÄ‡ z istniejÄ…cego domain/logic
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.data_manager import data_manager
from src.api.import_router import router as import_router
from src.api.pdf_service import generate_offer_pdf
from src.api.production_service import ProductionService
from src.domain.operations.module_ops import ModuleOperations
from src.domain.operations.wall_ops import WallOperations
from src.domain.operations.adapters.sqlite_project_module_repository import SqliteProjectModuleRepository
from src.core.costing.module_costs import calculate_module_cost_breakdown
from src.services.module_export_3dc_service import export_module_to_3dc_project_xml, export_project_to_3dc_xml
from src.services.gitlab_sync_service import git_sync_project_file
from src.services.invoice_pdf_import_service import parse_invoice_pdf_bytes
from src.services.invoice_email_import_service import fetch_invoice_pdf_attachments
from src.services.service_pricing_phase1 import (
    SERVICE_MODES,
    SERVICE_PRICING_PAYLOAD_SCHEMA_VERSION,
    price_service_item,
)

# RCP / Kiosk Logic
from src.server.kiosk_service import KioskService
from src.storage.work_time_store_json import WorkTimeStoreJson
from src.storage.alarm_store_json import AlarmStoreJson
from src.storage.company_expenses_store_json import CompanyExpensesStoreJson
from src.domain.alarm_models import AlarmDef
from src.services.telegram_hub_service import TelegramHubService
from src.storage.sqlite_db import get_calendar_event_store
from src.domain.calendar_event import CalendarEvent, normalize_web_event_type
from src.domain.work_time_costing import WorkTimeCostBreakdown, compute_work_time_cost
from src.core.auth_models import Role, Action, has_permission, ROLE_MAPPING

app = FastAPI(title="TECH MODUĹ  Pro API", version="0.1.0")
module_repo = SqliteProjectModuleRepository(data_manager=data_manager)
module_operations = ModuleOperations(repository=module_repo)
wall_operations = WallOperations()
production_service = ProductionService(data_manager)
kiosk_service = KioskService()
work_time_store = WorkTimeStoreJson()
alarm_store = AlarmStoreJson()
calendar_store = get_calendar_event_store()


class CurrentUser(BaseModel):
    name: str
    role: str
    user_id: str | None = None


def get_current_user_info(
    request: Request
) -> CurrentUser:
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Nie zalogowano. Brak sesji.")
        
    user = data_manager.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Sesja wygasła lub jest nieprawidłowa.")
        
    return CurrentUser(
        name=user["name"],
        role=user["role"],
        user_id=str(user["id"])
    )


def require_permission(user: CurrentUser, action: Action):
    if not has_permission(user.role, action):
        raise HTTPException(
            status_code=403,
            detail=_error_detail(f"Brak uprawnieĹ„ do akcji: {action.value}")
        )


def _error_detail(message: str) -> Dict[str, Any]:
    return {"errors": [{"message": str(message or "Błąd walidacji")}]} 


def _normalize_limit(raw: int | None, default: int = 200, max_value: int = 1000) -> int:
    try:
        value = int(raw if raw is not None else default)
    except Exception:
        value = default
    if value < 1:
        value = 1
    if value > max_value:
        value = max_value
    return value


def _validate_iso_date(value: str, *, field_name: str, required: bool = False) -> str:
    text = str(value or "").strip()
    if not text:
        if required:
            raise HTTPException(status_code=400, detail=_error_detail(f"Pole '{field_name}' jest wymagane"))
        return ""
    try:
        datetime.strptime(text[:10], "%Y-%m-%d")
    except Exception:
        raise HTTPException(status_code=400, detail=_error_detail(f"Pole '{field_name}' musi mieć format YYYY-MM-DD"))
    return text


def _parse_date_only(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _normalize_work_type_token(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").lower().strip()
    return re.sub(r"\s+", " ", text)


def _safe_hour_cost(breakdown: WorkTimeCostBreakdown) -> float | None:
    if float(breakdown.total_hours or 0.0) <= 0.0:
        return None
    return round(float(breakdown.total_cost or 0.0) / float(breakdown.total_hours or 0.0), 2)


def _normalize_calendar_datetime(value: str, *, field_name: str, required: bool = False) -> str:
    text = str(value or "").strip()
    if not text:
        if required:
            raise HTTPException(status_code=400, detail=_error_detail(f"Pole '{field_name}' jest wymagane"))
        return ""
    try:
        if "T" in text:
            datetime.fromisoformat(text)
        else:
            datetime.strptime(text[:10], "%Y-%m-%d")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=_error_detail(f"Pole '{field_name}' musi miec format YYYY-MM-DD lub YYYY-MM-DDTHH:MM"),
        )
    return text


def _normalize_work_status(raw_status: str, *, force_blocked: bool = False) -> tuple[str, str, str]:
    if force_blocked:
        return ("blocked", "Ryzyko", "red")

    normalized = str(raw_status or "").strip().lower()
    done_values = {"wykonane", "zakończone", "zakonczone", "zamkniete", "closed", "finished", "oplacone", "paid"}
    in_progress_values = {"w_trakcie", "w toku", "in_progress", "realizacja", "active"}
    blocked_values = {"zablokowane", "blokada", "critical", "krytyczny", "problem"}
    planned_values = {"planowane", "draft", "nowe", "oczekuje", "do zaplaty", "todo"}

    if normalized in done_values:
        return ("done", "Zakonczone", "emerald")
    if normalized in in_progress_values:
        return ("in_progress", "W trakcie", "blue")
    if normalized in blocked_values:
        return ("blocked", "Ryzyko", "red")
    if normalized in planned_values:
        return ("planned", "Planowane", "amber")
    return ("unknown", "Nieokreslone", "slate")


def _resolve_workspace_mount_type(module_row: Dict[str, Any]) -> str:
    cabinet_type = str(module_row.get("cabinet_type") or "").strip().lower()
    if cabinet_type in {"wall", "corner_wall"}:
        return "wall"
    if cabinet_type in {"base", "corner_base", "tall"}:
        return "floor"

    family = str(module_row.get("module_family") or "").strip().lower()
    if any(token in family for token in ("wall", "upper", "overhead", "hanging")):
        return "wall"
    return "floor"

# Konfiguracja CORS dla bezpiecznego poĹ‚Ä…czenia z frontendem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # W produkcji ogranicz do localhost:3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ładowanie routerów
app.include_router(import_router)

# Phase 1 Safe Work Mode: read-only CSV/JSON export endpoints for core data.
from src.api.csv_exports import csv_export_router  # noqa: E402
app.include_router(csv_export_router)

# --- MODELE DANYCH (Pydantic) ---
class ProjectCreate(BaseModel):
    title: str
    client_name: str

class MarginUpdate(BaseModel):
    margin: int


class CompanyExpenseItemPayload(BaseModel):
    expense_id: str | None = None
    name: str
    amount: float
    account_type: str | None = "bank"
    source_type: str | None = "bank_faktura"


class CompanyExpensesUpdatePayload(BaseModel):
    fixed: List[CompanyExpenseItemPayload]
    workers_count: int
    hours_per_worker: float

class ObstaclesUpdate(BaseModel):
    obstacles: List[Dict]


class ModulePlacementUpdate(BaseModel):
    x_mm: float | None = None
    y_mm: float | None = None
    z_mm: float | None = None
    rotation_deg: float | None = None


class WallConfigUpdate(BaseModel):
    width: float
    height: float
    room_depth: float | None = None
    depth: float | None = None


class OrderCreate(BaseModel):
    project_id: int
    client_name: str
    title: str
    deadline: str = ""
    deadline_from: str = ""
    deadline_to: str = ""
    budget: float = 0.0
    status: str = "DRAFT"
    spec_json: str = "{}"


class ServicePricingPreviewRequest(BaseModel):
    item: Dict[str, Any]
    tariff_profile: str = ""


class CalendarEventCreate(BaseModel):
    event_type: str = "other"
    type: str | None = None
    title: str
    date: str = ""
    date_end: str = ""
    start_at: str = ""
    end_at: str = ""
    all_day: bool = True
    station: str = ""
    worker_name: str = ""
    assigned_to: str = ""
    order_code: str = ""
    project_ref: str = ""
    client_name: str = ""
    location: str = ""
    notes: str = ""
    status: str = "planned"


class CalendarEventUpdate(BaseModel):
    event_type: str | None = None
    type: str | None = None
    title: str | None = None
    date: str | None = None
    date_end: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    all_day: bool | None = None
    station: str | None = None
    worker_name: str | None = None
    assigned_to: str | None = None
    order_code: str | None = None
    project_ref: str | None = None
    client_name: str | None = None
    location: str | None = None
    notes: str | None = None
    status: str | None = None



class AlarmAckPayload(BaseModel):
    acknowledged: bool = True
    note: str = ""


class OperationIssuePatch(BaseModel):
    status: str | None = None
    owner: str | None = None
    priority_manual: str | None = None
    due_date: str | None = None
    notes: str | None = None


class OperationRouteRecommendRequest(BaseModel):
    planned_date: str = ""
    crew: str = ""
    limit: int = 5


class ClientCreate(BaseModel):
    name: str
    location: str = ""
    address: str = ""
    email: str = ""
    phone: str = ""
    type: str = "person"
    status: str = "active"


class MaterialCreate(BaseModel):
    name: str
    price_per_m2: float
    thickness: int
    material_code: str = ""
    category: str = "boards"
    material_kind: str = "other"
    unit: str = "m2"
    is_library: bool = True
    stock_quantity: float = 0.0
    min_stock: float = 0.0
    purchase_type: str = "nothing"
    supplier: str = ""
    wholesaler: str = ""
    format_length_mm: float = 0.0
    format_width_mm: float = 0.0
    pack_size: float = 0.0
    parameter_json: str = "{}"
    texture_url: str = ""
    color_hex: str = "#ffffff"


class MaterialUpdate(BaseModel):
    name: str | None = None
    price_per_m2: float | None = None
    thickness: int | None = None
    material_code: str | None = None
    category: str | None = None
    material_kind: str | None = None
    unit: str | None = None
    min_stock: float | None = None
    purchase_type: str | None = None
    supplier: str | None = None
    wholesaler: str | None = None
    parameter_json: str | None = None
    format_length_mm: float | None = None
    format_width_mm: float | None = None
    pack_size: float | None = None


class ManufacturerSchema(BaseModel):
    name: str
    code: str | None = None
    website_url: str | None = None
    country: str | None = None
    notes: str | None = None
    is_active: bool = True


class CatalogItemSchema(BaseModel):
    name: str
    internal_code: str | None = None
    producer_code: str | None = None
    manufacturer_id: int | None = None
    category_id: int | None = None
    item_type: str | None = None
    default_thickness_mm: float | None = None
    base_unit: str = "pcs"
    is_active: bool = True


# --- Inventory + Order Cost Write-Off models ---

class PurchaseDocumentLineInput(BaseModel):
    material_id: int | None = None
    description_snapshot: str = ""
    qty: float = 0.0
    unit: str = "pcs"
    unit_price_net: float = 0.0
    vat_rate: float = 23.0
    is_stock_item: bool = True
    order_id: int | None = None
    note: str = ""


class PurchaseDocumentCreate(BaseModel):
    supplier_name: str
    document_number: str
    document_date: str
    document_type: str = "invoice"
    currency: str = "PLN"
    total_net: float = 0.0
    total_gross: float = 0.0
    payment_status: str = "unpaid"
    payment_method: str = ""
    note: str = ""
    lines: List[PurchaseDocumentLineInput] = []


class PurchaseReceiveRequest(BaseModel):
    payment_method: str = ""
    created_by: str = ""


class OrderCostEntryCreate(BaseModel):
    order_id: int
    cost_type: str = "MATERIAL"
    source_type: str = ""
    source_id: int | None = None
    amount_net: float = 0.0
    vat_rate: float = 23.0
    amount_gross: float = 0.0
    qty: float | None = None
    unit: str | None = None
    description: str = ""
    note: str = ""
    created_by: str = ""


class ReserveMaterialRequest(BaseModel):
    material_id: int
    order_id: int
    qty: float
    unit: str = "pcs"
    note: str = ""
    created_by: str = ""


class CancelReservationRequest(BaseModel):
    reservation_movement_id: int
    created_by: str = ""


class IssueMaterialRequest(BaseModel):
    material_id: int
    order_id: int
    qty: float
    unit: str = "pcs"
    unit_cost_override: float | None = None
    note: str = ""
    created_by: str = ""


class ReturnMaterialRequest(BaseModel):
    material_id: int
    order_id: int
    qty: float
    unit: str = "pcs"
    related_issue_movement_id: int | None = None
    note: str = ""
    created_by: str = ""


class ScrapMaterialRequest(BaseModel):
    material_id: int
    qty: float
    unit: str = "pcs"
    order_id: int | None = None
    charge_to_order: bool = False
    note: str = ""
    created_by: str = ""


class CorrectionRequest(BaseModel):
    material_id: int
    qty_delta: float
    unit: str = "pcs"
    note: str = ""
    created_by: str = ""


# --- NEW CATALOG & KNOWLEDGE BASE ---
from src.storage.catalog_store_sqlite import CatalogStoreSqlite
catalog_store = CatalogStoreSqlite()


@app.get("/catalog/manufacturers")
async def get_manufacturers():
    return catalog_store.get_manufacturers()


@app.post("/catalog/manufacturers")
async def create_manufacturer(m: ManufacturerSchema):
    from src.domain.catalog_models import Manufacturer
    m_obj = Manufacturer(id=None, **m.dict())
    m_id = catalog_store.create_manufacturer(m_obj)
    return {"status": "success", "id": m_id}


@app.get("/catalog/categories")
async def get_catalog_categories():
    return catalog_store.get_categories()


@app.get("/catalog/items")
async def get_catalog_items(category_id: int | None = None, usage_type: str | None = None, include_deleted: bool = False):
    return catalog_store.get_catalog_items(category_id=category_id, usage_type=usage_type, include_deleted=include_deleted)


@app.post("/catalog/items")
async def create_catalog_item(item: CatalogItemSchema):
    from src.domain.catalog_models import CatalogItem
    obj = CatalogItem(id=None, **item.dict())
    item_id = catalog_store.create_catalog_item(obj)
    return {"status": "success", "id": item_id}


@app.post("/catalog/import-csv")
async def import_catalog_csv(file: UploadFile = File(...)):
    import csv
    import io
    
    contents = await file.read()
    decoded = contents.decode("utf-8")
    f = io.StringIO(decoded)
    reader = csv.DictReader(f)
    
    rows = [row for row in reader]
    stats = catalog_store.import_from_csv(rows)
    return {"status": "success", "stats": stats}

# --- ENDPOINTY PROJEKTĂ“W ---
@app.get("/projects")
async def get_projects(include_deleted: bool = False):
    return data_manager.get_all_projects(include_deleted=include_deleted)

@app.post("/db/materials")
async def create_db_material(m: MaterialCreate):
    m_id = data_manager.create_material(
        name=m.name,
        price_per_m2=m.price_per_m2,
        thickness=m.thickness,
        category=m.category,
        material_kind=m.material_kind,
        unit=m.unit,
        is_library=m.is_library,
        stock_quantity=m.stock_quantity,
        min_stock=m.min_stock,
        purchase_type=m.purchase_type,
        supplier=m.supplier,
        wholesaler=m.wholesaler,
        material_code=m.material_code,
        format_length_mm=m.format_length_mm,
        format_width_mm=m.format_width_mm,
        pack_size=m.pack_size,
        parameter_json=m.parameter_json,
        texture_url=m.texture_url,
        color_hex=m.color_hex,
    )
    return {"status": "success", "id": m_id}


@app.patch("/db/materials/{material_id}")
async def patch_db_material(material_id: int, payload: MaterialUpdate):
    updates = payload.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail=_error_detail("Brak pol do aktualizacji"))
    ok = data_manager.update_material(material_id=int(material_id), updates=updates)
    if not ok:
        raise HTTPException(status_code=404, detail=_error_detail("Nie znaleziono materialu lub brak zmian"))
    return {"status": "success"}

@app.post("/projects")
async def create_project(project: ProjectCreate):
    project_id = data_manager.create_project(project.title, project.client_name)
    return {"status": "success", "id": project_id}

@app.put("/projects/{project_id}/margin")
async def update_margin(project_id: int, update: MarginUpdate):
    data_manager.update_project_margin(project_id, update.margin)
    return {"status": "success"}

@app.get("/projects/{project_id}/obstacles")
async def get_project_obstacles(project_id: int):
    return data_manager.get_project_obstacles(project_id)

@app.put("/projects/{project_id}/obstacles")
async def update_project_obstacles(project_id: int, update: ObstaclesUpdate):
    success = data_manager.update_project_obstacles(project_id, update.obstacles)
    return {"status": "success" if success else "error"}


@app.patch("/projects/{project_id}/modules/{module_id}/placement")
async def update_project_module_placement(project_id: int, module_id: int, payload: ModulePlacementUpdate):
    modules = data_manager.get_project_modules(project_id)
    selected = None
    for module in modules:
        if int(module.get("id", -1)) == int(module_id):
            selected = module
            break
    if selected is None:
        raise HTTPException(status_code=404, detail=_error_detail("Nie znaleziono modulu w projekcie"))

    has_payload_fields = any(
        value is not None for value in (payload.x_mm, payload.y_mm, payload.z_mm, payload.rotation_deg)
    )
    if not has_payload_fields:
        raise HTTPException(status_code=400, detail=_error_detail("Brak pol placement do aktualizacji"))

    mount_type = _resolve_workspace_mount_type(selected)
    updates: Dict[str, float] = {}
    if payload.x_mm is not None:
        next_x = max(0.0, float(payload.x_mm))
        data_manager.update_module_property(int(module_id), "x", next_x)
        updates["x_mm"] = next_x
    if payload.y_mm is not None:
        next_y = max(0.0, float(payload.y_mm))
        if mount_type == "floor":
            next_y = 0.0
        data_manager.update_module_property(int(module_id), "y", next_y)
        updates["y_mm"] = next_y
    if payload.z_mm is not None:
        next_z = max(0.0, float(payload.z_mm))
        data_manager.update_module_property(int(module_id), "z", next_z)
        updates["z_mm"] = next_z
    if payload.rotation_deg is not None:
        data_manager.update_module_property(int(module_id), "rotation", float(payload.rotation_deg))
        updates["rotation_deg"] = float(payload.rotation_deg)

    # Moduly stojace sa kotwiczone do podlogi, zeby nie "lataly" po scenie.
    if mount_type == "floor" and "y_mm" not in updates:
        data_manager.update_module_property(int(module_id), "y", 0.0)
        updates["y_mm"] = 0.0

    return {
        "status": "success",
        "module_id": int(module_id),
        "placement": updates,
    }

# --- ENDPOINTY TECHNICZNE (ĹšCIANA, MODUĹ) ---
@app.put("/config/wall/{project_id}")
async def update_wall_config(project_id: int, payload: WallConfigUpdate):
    wall_name = f"WEB_PROJECT_{int(project_id)}"
    wall = wall_operations.get_points(wall_name)
    points = list(wall.get("points") or [])

    width = max(1000, int(round(float(payload.width or 0.0))))
    height = max(1000, int(round(float(payload.height or 0.0))))
    depth_raw = payload.room_depth if payload.room_depth is not None else payload.depth
    default_depth = max(1800, int(round(width * 0.78)))
    depth = max(1200, int(round(float(depth_raw if depth_raw is not None else default_depth))))

    saved = data_manager.upsert_project_wall_config(
        project_id=int(project_id),
        width_mm=width,
        height_mm=height,
        depth_mm=depth,
    )

    return {
        "id": int(project_id),
        "wall_name": wall_name,
        "points_count": len(points),
        "width": int(round(float(saved.get("width_mm", width) or width))),
        "height": int(round(float(saved.get("height_mm", height) or height))),
        "room_depth": int(round(float(saved.get("depth_mm", depth) or depth))),
        "left_angle": 90,
        "right_angle": 90,
    }


@app.get("/config/wall/{project_id}")
async def get_wall_config(project_id: int):
    wall_name = f"WEB_PROJECT_{int(project_id)}"
    wall = wall_operations.get_points(wall_name)
    points = list(wall.get("points") or [])
    if len(points) == 0:
        width = 3250
        height = 2500
    else:
        max_x = max(float(p.get("x", 0.0) or 0.0) for p in points)
        max_y = max(float(p.get("y", 0.0) or 0.0) for p in points)
        width = max(1000, int(max_x + 300))
        height = max(1000, int(max_y + 300))

    saved = data_manager.get_project_wall_config(int(project_id))
    if saved:
        width = max(1000, int(round(float(saved.get("width_mm", width) or width))))
        height = max(1000, int(round(float(saved.get("height_mm", height) or height))))
        room_depth = max(1200, int(round(float(saved.get("depth_mm", max(1800, int(round(width * 0.78))))))))
    else:
        room_depth = max(1800, int(round(width * 0.78)))

    return {
        "id": int(project_id),
        "wall_name": wall_name,
        "points_count": len(points),
        "width": width,
        "height": height,
        "room_depth": room_depth,
        "left_angle": 90,
        "right_angle": 90,
    }

@app.get("/config/modules/{project_id}")
async def get_project_modules(project_id: int):
    """Zwraca listÄ™ moduĹ‚Ăłw (szafek) projektu z SQLite."""
    return data_manager.get_project_modules(project_id)
@app.get("/projects/{project_id}/assembly-summary")
async def get_project_assembly_summary(project_id: int):
    """Zwraca backendowe podsumowanie modulow projektu dla widoku /assembly."""
    return data_manager.get_project_assembly_summary(project_id)


@app.get("/projects/{project_id}/workspace-summary")
async def get_project_workspace_summary(project_id: int):
    return data_manager.get_project_workspace_summary(project_id)


@app.get("/projects/{project_id}/finance-summary")
async def get_project_finance_summary(project_id: int):
    return data_manager.get_project_finance_summary(project_id)


@app.get("/projects/{project_id}/wall-summary")
async def get_project_wall_summary(project_id: int):
    wall_name = f"WEB_PROJECT_{int(project_id)}"
    wall = wall_operations.get_points(wall_name)
    points = list(wall.get("points") or [])
    return {
        "project_id": int(project_id),
        "wall_name": wall_name,
        "points_count": len(points),
    }
    
@app.get("/projects/{project_id}/material-summary")
async def get_project_material_summary(project_id: int):
    return data_manager.get_project_material_summary(project_id)


@app.get("/projects/{project_id}/unified-summary")
async def get_project_unified_summary(project_id: int):
    """Skladane podsumowanie z 4 zrodel - zgodne z desktopowym UnifiedSummaryPanel."""
    finance = data_manager.get_project_finance_summary(project_id)
    assembly = data_manager.get_project_assembly_summary(project_id)
    workspace = data_manager.get_project_workspace_summary(project_id)
    materials = data_manager.get_project_material_summary(project_id)

    base_cost = float(finance.get("base_cost") or 0.0)
    total_net = float(finance.get("total_net") or 0.0)
    total_gross = float(finance.get("total_gross") or 0.0)
    profit = float(finance.get("profit") or 0.0)
    vat = float(finance.get("vat") or 0.0)
    margin = int(finance.get("margin") or 30)

    pricing = {
        "material_value": base_cost,
        "services_total": 0.0,
        "extras_total": 0.0,
        "base_total": base_cost,
        "sale_total": total_net,
        "brutto_total": total_gross,
        "profit_total": profit,
        "technical_total": base_cost,
        "vat": vat,
        "margin_percent": margin,
    }

    sources: list[str] = []
    if int(assembly.get("modules_count") or 0) > 0:
        sources.append("assembly")
    if int(workspace.get("orders_count") or 0) > 0:
        sources.append("workspace")
    if base_cost > 0:
        sources.append("finance")
    if materials:
        sources.append("materials")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    audit = {
        "built_from": sources,
        "adapter_name": "compose_summaries()",
        "built_at": now,
        "notes": f"Cross-tab compose: {len(sources)} source(s)",
    }

    return {
        "project_id": int(project_id),
        "project_title": str(workspace.get("project_title") or ""),
        "client_name": str(workspace.get("client_name") or ""),
        "pricing": pricing,
        "scope": {
            "modules_count": int(assembly.get("modules_count") or 0),
            "orders_count": int(workspace.get("orders_count") or 0),
            "draft_orders_count": int(workspace.get("draft_orders_count") or 0),
            "materials_used": len(materials or []),
        },
        "audit": audit,
        "computed_at": now,
    }


class ValuationSheetRequest(BaseModel):
    text: str

@app.post("/agent/parse-valuation-sheet")
async def parse_valuation_sheet(data: ValuationSheetRequest):
    return agent.parse_valuation_sheet(data.text)


@app.get("/api/production/project/{project_id}/summary")
async def api_get_project_production_summary(project_id: int):
    """Zwraca podsumowanie produkcyjne: lista formatek i zużycie materiałów."""
    return production_service.get_project_production_summary(project_id)


@app.get("/api/production/project/{project_id}/export/project")
async def export_project_3dc(project_id: int):
    """Eksportuje cały projekt do formatu .project i synchronizuje z GitLabem."""
    finance = data_manager.get_project_finance_summary(project_id)
    module_defs = production_service.get_project_module_defs(project_id)
    
    export_dir = os.path.join(os.getcwd(), "exports", "projects")
    os.makedirs(export_dir, exist_ok=True)
    
    filename = f"Project_PRJ_{project_id}.project"
    file_path = os.path.join(export_dir, filename)
    
    try:
        # 1. Eksport do XML
        export_project_to_3dc_xml(module_defs, finance.get("project_title", "Projekt"), file_path)
        
        # 2. GitLab Sync
        from src.services.gitlab_sync_service import git_sync_project_file
        git_sync_project_file(file_path, f"Eksport projektu {project_id} do .project")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/xml"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd eksportu projektu: {str(e)}")

@app.get("/api/production/project/{project_id}/export/csv")
async def export_project_csv(project_id: int):
    """Generatues and returns the industrial cutting list in CSV format and syncs with GitLab."""
    csv_content = production_service.export_cutting_list_csv(project_id)
    
    # 1. Save to exports folder for GIT sync
    export_dir = os.path.join(os.getcwd(), "exports", "cutting_lists")
    os.makedirs(export_dir, exist_ok=True)
    filename = f"CuttingList_PRJ_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = os.path.join(export_dir, filename)
    
    with open(file_path, "w", encoding="utf-8-sig") as f:
        f.write(csv_content)
        
    # 2. GitLab Sync
    from src.services.gitlab_sync_service import git_sync_project_file
    git_sync_project_file(file_path, f"Eksport listy cięcia CSV dla projektu {project_id}")

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@app.get("/projects/{project_id}/export-pdf")
async def export_project_pdf(project_id: int):
    """Generuje i zwraca ofertę PDF dla projektu."""
    finance = data_manager.get_project_finance_summary(project_id)
    modules = data_manager.get_project_modules(project_id)
    
    if not finance.get("project_title"):
        raise HTTPException(status_code=404, detail="Projekt nie istnieje.")

    # Fetch Real Pricing from Production engine
    prod_summary = production_service.get_project_production_summary(project_id)
    total_net = prod_summary.get("pricing", {}).get("final_price", finance["total_net"])
    vat = round(total_net * 0.23, 2)
    total_gross = round(total_net + vat, 2)

    # Distribute real cost across modules proportionally by generic size (or evenly if dimensions are 0)
    total_volume = sum((m["width"] * m["height"] * m["depth"]) for m in modules) or 1
    
    project_data = {
        "id": project_id,
        "title": finance["project_title"],
        "client_name": finance["client_name"],
        "total_net": total_net,
        "vat": vat,
        "total_gross": total_gross,
        "modules": [
            {
                "name": m["name"],
                "width": m["width"],
                "height": m["height"],
                "depth": m["depth"],
                "price_net": round(total_net * ((m["width"] * m["height"] * m["depth"]) / total_volume), 2)
            } for m in modules
        ],
        "material_stats": prod_summary.get("material_stats", []),
        "pricing_breakdown": prod_summary.get("pricing", {})
    }

    # 3. Wygeneruj plik tymczasowy
    tmp_dir = "temp/pdf"
    os.makedirs(tmp_dir, exist_ok=True)
    file_path = os.path.join(tmp_dir, f"Oferta_{project_id}.pdf")
    
    generate_offer_pdf(project_data, file_path)

    return FileResponse(
        path=file_path,
        filename=f"Oferta_TECH_MODUL_{project_id}.pdf",
        media_type="application/pdf"
    )

@app.get("/projects/{project_id}/calendar-events")
async def get_project_calendar_events(project_id: int):
    return {
        "project_id": int(project_id),
        "events": data_manager.get_project_calendar_events(project_id=project_id),
    }


@app.get("/api/calendar/events")
async def get_calendar_events(limit: int = 500):
    safe_limit = _normalize_limit(limit, default=500, max_value=2000)
    events = calendar_store.get_all(limit=safe_limit)
    return {
        "status": "ok",
        "limit": safe_limit,
        "events": [e.to_dict() for e in events],
    }


@app.post("/api/calendar/events")
async def create_calendar_event(payload: CalendarEventCreate):
    start_at = _normalize_calendar_datetime(payload.start_at or payload.date, field_name="start_at", required=True)
    end_at = _normalize_calendar_datetime(payload.end_at or payload.date_end, field_name="end_at", required=False)
    event_type = normalize_web_event_type(payload.type or payload.event_type)
    event = CalendarEvent.new(
        title=payload.title,
        date=start_at,
        date_end=end_at,
        all_day=payload.all_day,
        event_type=event_type,
        station=payload.station,
        order_code=payload.project_ref or payload.order_code,
        worker_name=payload.assigned_to or payload.worker_name,
        client_name=payload.client_name,
        location=payload.location,
        notes=payload.notes,
        status=payload.status,
    )
    new_event = calendar_store.save(event)
    return {"status": "ok", "event": new_event.to_dict()}


@app.patch("/api/calendar/events/{event_id}")
async def update_calendar_event(event_id: str, payload: CalendarEventUpdate):
    event = calendar_store.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=_error_detail("Nie znaleziono eventu"))
    
    update_data = payload.dict(exclude_unset=True)
    if "title" in update_data:
        event.title = str(update_data["title"] or "")
    if "type" in update_data or "event_type" in update_data:
        event.event_type = normalize_web_event_type(str(update_data.get("type") or update_data.get("event_type") or event.event_type))
    if "start_at" in update_data or "date" in update_data:
        event.date = _normalize_calendar_datetime(str(update_data.get("start_at") or update_data.get("date") or ""), field_name="start_at", required=True)
    if "end_at" in update_data or "date_end" in update_data:
        event.date_end = _normalize_calendar_datetime(str(update_data.get("end_at") or update_data.get("date_end") or ""), field_name="end_at", required=False)
    if "all_day" in update_data:
        event.all_day = bool(update_data["all_day"])
    if "station" in update_data:
        event.station = str(update_data["station"] or "")
    if "assigned_to" in update_data or "worker_name" in update_data:
        event.worker_name = str(update_data.get("assigned_to") or update_data.get("worker_name") or "")
    if "project_ref" in update_data or "order_code" in update_data:
        event.order_code = str(update_data.get("project_ref") or update_data.get("order_code") or "")
    if "client_name" in update_data:
        event.client_name = str(update_data["client_name"] or "")
    if "location" in update_data:
        event.location = str(update_data["location"] or "")
    if "notes" in update_data:
        event.notes = str(update_data["notes"] or "")
    if "status" in update_data:
        event.status = str(update_data["status"] or "planned")
    
    updated_event = calendar_store.save(event)
    return {"status": "ok", "event": updated_event.to_dict()}


@app.delete("/api/calendar/events/{event_id}")
async def delete_calendar_event(event_id: str):
    success = calendar_store.delete(event_id)
    if not success:
        raise HTTPException(status_code=404, detail=_error_detail("Nie znaleziono eventu lub błąd usuwania"))
    return {"status": "ok"}

@app.get("/api/calendar/workboard")
async def get_calendar_workboard(
    project_id: int | None = None,
    days_back: int = 30,
    days_forward: int = 365,
    limit: int = 500,
    include_undated: bool = True,
):
    safe_limit = _normalize_limit(limit, default=500, max_value=5000)
    safe_days_back = _normalize_limit(days_back, default=30, max_value=3650)
    safe_days_forward = _normalize_limit(days_forward, default=365, max_value=3650)

    today = date.today()
    window_start = today - timedelta(days=safe_days_back)
    window_end = today + timedelta(days=safe_days_forward)

    scoped_project_id = int(project_id) if project_id not in {None, 0, ""} else None
    scoped_project_title = ""
    if scoped_project_id is not None:
        try:
            for project_row in data_manager.get_all_projects():
                if int(project_row.get("id", 0) or 0) == scoped_project_id:
                    scoped_project_title = str(project_row.get("title", "") or "")
                    break
        except Exception:
            scoped_project_title = ""

    events = calendar_store.get_all(limit=safe_limit)

    items: list[Dict[str, Any]] = []

    for e in events:
        if scoped_project_id is not None:
            event_project_ref = str(getattr(e, "order_code", "") or "")
            if event_project_ref and event_project_ref != str(scoped_project_id) and event_project_ref != scoped_project_title:
                continue

        # Check if in window
        ev_date = _parse_date_only(e.date)
        if not ev_date and not include_undated:
            continue
            
        if ev_date:
            if ev_date < window_start or ev_date > window_end:
                continue
        
        # Map to CalendarWorkItem format
        status_info = _normalize_work_status(e.status)
        
        items.append({
            "id": e.id,
            "source": "calendar",
            "kind": e.event_type,
            "title": e.title,
            "subtitle": f"{e.client_name} | {e.location}" if e.client_name or e.location else "",
            "date_from": e.date,
            "date_to": e.date_end,
            "status_key": status_info[0],
            "status_label": status_info[1],
            "color_key": status_info[2],
            "assignees": [e.worker_name] if e.worker_name else [],
            "order_id": None, # Could try to link by order_code if needed
            "is_overdue": ev_date and ev_date < today and status_info[0] != "done",
            "source_route": "/calendar",
            "confidence": "READY"
        })

    try:
        orders = data_manager.get_orders(project_id=scoped_project_id) if scoped_project_id is not None else data_manager.get_orders()
    except Exception:
        orders = []

    for order in orders:
        d_from = str(order.get("deadline_from", "") or "")
        d_to = str(order.get("deadline_to", "") or "")
        if not d_from or not _parse_date_only(d_from):
            continue
        if _parse_date_only(d_from) < window_start or _parse_date_only(d_from) > window_end:
            continue
        status_info = _normalize_work_status(str(order.get("status", "") or "planned"))
        items.append(
            {
                "id": f"order-{order.get('id', '')}",
                "source": "order_calendar",
                "kind": "order_event",
                "title": str(order.get("title", "") or order.get("order_name", "") or "Order"),
                "subtitle": str(order.get("client_name", "") or ""),
                "date_from": d_from,
                "date_to": d_to,
                "status_key": status_info[0],
                "status_label": status_info[1],
                "color_key": status_info[2],
                "assignees": [],
                "order_id": order.get("id"),
                "is_overdue": _parse_date_only(d_from) < today and status_info[0] != "done",
                "source_route": "/orders/new",
                "confidence": "READY",
            }
        )

    # 2. Add Production Routes & Issues
    try:
        from src.core.operations_store import OperationsStore
        ops = OperationsStore()
        routes = ops.list_routes()
        issues = ops.filter_issues(active_only=False)
    except:
        routes, issues = [], []

    for r in routes:
        if scoped_project_id is not None:
            route_project_id = str(getattr(r, "project_id", "") or "")
            route_project_name = str(getattr(r, "project_name", "") or "")
            if route_project_id and route_project_id != str(scoped_project_id):
                continue
            if scoped_project_title and route_project_name and route_project_name != scoped_project_title:
                continue
        d_from = str(getattr(r, "planned_date", "") or "")
        if not d_from or not _parse_date_only(d_from): continue
        if _parse_date_only(d_from) < window_start or _parse_date_only(d_from) > window_end: continue
        
        status_info = _normalize_work_status(getattr(r, "status", ""))
        items.append({
            "id": f"route-{getattr(r, 'id', '')}",
            "source": "production_route",
            "kind": "production_task",
            "title": str(getattr(r, "task_type", "Zadanie")).replace("_", " ").title(),
            "subtitle": str(getattr(r, "project_name", "") or getattr(r, "client_name", "")),
            "date_from": d_from,
            "status_key": status_info[0],
            "status_label": status_info[1],
            "color_key": status_info[2],
            "assignees": [chunk.strip() for chunk in re.split(r"[;,/|]", str(getattr(r, "crew", "") or "")) if chunk.strip()],
            "is_overdue": _parse_date_only(d_from) < today and status_info[0] != "done",
            "source_route": "/operations",
            "confidence": "READY"
        })

    for issue in issues:
        if scoped_project_id is not None:
            issue_project_id = str(getattr(issue, "project_id", "") or "")
            issue_project_name = str(getattr(issue, "project_name", "") or "")
            if issue_project_id and issue_project_id != str(scoped_project_id):
                continue
            if scoped_project_title and issue_project_name and issue_project_name != scoped_project_title:
                continue
        d_due = str(getattr(issue, "due_date", "") or "")
        d_created = str(getattr(issue, "created_at", "") or "")[:10]
        d_ref = d_due or d_created
        if not d_ref or not _parse_date_only(d_ref): continue
        if _parse_date_only(d_ref) < window_start or _parse_date_only(d_ref) > window_end: continue
        priority_text = str(getattr(issue, "priority_manual", "") or "").strip().lower()
        issue_is_overdue = bool(getattr(issue, "is_overdue", lambda: False)()) if callable(getattr(issue, "is_overdue", None)) else False
        status_info = _normalize_work_status(
            getattr(issue, "status", ""),
            force_blocked=issue_is_overdue or priority_text in {"krytyczny", "critical"},
        )
        items.append({
            "id": f"issue-{getattr(issue, 'id', '')}",
            "source": "operations_issue",
            "kind": "issue",
            "title": str(getattr(issue, "title", "Issue")),
            "subtitle": str(getattr(issue, "project_name", "") or getattr(issue, "client_name", "")),
            "date_from": d_ref,
            "status_key": status_info[0],
            "status_label": status_info[1],
            "color_key": status_info[2],
            "assignees": [getattr(issue, "owner", "")] if getattr(issue, "owner", "") else [],
            "is_overdue": issue_is_overdue or (_parse_date_only(d_ref) < today and status_info[0] != "done"),
            "source_route": "/operations",
            "confidence": "READY"
        })

    try:
        worker_rows = kiosk_service.list_workers()
    except Exception:
        worker_rows = []

    active_workers_count = 0
    if scoped_project_id is not None:
        active_workers_count = sum(
            1
            for row in worker_rows
            if bool(row.get("active"))
            and (
                str(((row.get("session") or {}).get("project_code") or "")) == scoped_project_title
                or str(((row.get("session") or {}).get("project_id") or "")) == str(scoped_project_id)
            )
        )
    else:
        active_workers_count = sum(1 for row in worker_rows if bool(row.get("active")))

    return {
        "status": "ok",
        "project_id": scoped_project_id,
        "project_title": scoped_project_title,
        "generated_at": datetime.now().isoformat(),
        "window": {
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
            "days_back": safe_days_back,
            "days_forward": safe_days_forward,
        },
        "summary": {
            "total_items": len(items),
            "overdue_count": sum(1 for i in items if i.get("is_overdue")),
            "active_workers_count": active_workers_count,
        },
        "items": items,
        "confidence": "READY"
    }





@app.get("/projects/{project_id}/mvp-readiness")
def get_project_mvp_readiness(project_id: int):
    return _build_project_mvp_readiness_payload(project_id)


def _build_project_mvp_readiness_payload(project_id: int) -> Dict[str, Any]:
    project_id = int(project_id)
    modules_count = len(data_manager.get_project_modules(project_id))
    orders_count = len(data_manager.get_orders(project_id=project_id))
    wall_name = f"WEB_PROJECT_{project_id}"
    wall_points_count = len(list((wall_operations.get_points(wall_name) or {}).get("points") or []))
    materials_count = len(data_manager.get_materials())
    clients_count = len(data_manager.get_clients())

    check_labels = {
        "has_modules": "Brak modułów",
        "has_orders": "Brak zamówień",
        "has_wall_points": "Brak punktów ściany",
        "has_materials": "Brak materiałów",
        "has_clients": "Brak kontrahentów",
    }
    checks = {
        "has_modules": modules_count > 0,
        "has_orders": orders_count > 0,
        "has_wall_points": wall_points_count > 0,
        "has_materials": materials_count > 0,
        "has_clients": clients_count > 0,
    }
    total_checks = len(checks)
    passed_checks = sum(1 for v in checks.values() if bool(v))
    readiness_percent = int(round((passed_checks / total_checks) * 100)) if total_checks > 0 else 0
    action_catalog = {
        "has_modules": {"code": "add_module", "label": "Dodaj minimum jeden moduł", "priority": 1, "route": "/configuration"},
        "has_orders": {"code": "create_order", "label": "Dodaj minimum jedno zamówienie", "priority": 1, "route": "/orders/new"},
        "has_wall_points": {"code": "add_wall_point", "label": "Dodaj punkt ściany", "priority": 1, "route": "/wall"},
        "has_materials": {"code": "create_material", "label": "Dodaj materiał do bazy", "priority": 2, "route": "/database"},
        "has_clients": {"code": "create_client", "label": "Dodaj kontrahenta do bazy", "priority": 2, "route": "/database/clients"},
    }
    ready = all(bool(v) for v in checks.values())
    missing = [k for k, v in checks.items() if not bool(v)]
    missing_details = []
    for key in missing:
        missing_details.append(
            {
                "check": key,
                "label": str(check_labels.get(key, key)),
                "priority": 1 if key in {"has_modules", "has_orders", "has_wall_points"} else 2,
            }
        )
    missing_details.sort(key=lambda item: (int(item.get("priority", 99)), str(item.get("check", ""))))
    missing_labels = [str(item.get("label", "")) for item in missing_details]
    next_actions = []
    for key in missing:
        action = action_catalog.get(key)
        if action is None:
            continue
        next_actions.append(
            {
                "for_check": key,
                "code": str(action["code"]),
                "label": str(action["label"]),
                "priority": int(action["priority"]),
                "route": str(action["route"]),
            }
        )
    next_actions.sort(key=lambda item: (int(item.get("priority", 99)), str(item.get("code", ""))))
    next_action = next_actions[0] if len(next_actions) > 0 else None
    return {
        "project_id": project_id,
        "ready": ready,
        "checks": checks,
        "missing": missing,
        "missing_labels": missing_labels,
        "missing_details": missing_details,
        "counts": {
            "modules": modules_count,
            "orders": orders_count,
            "wall_points": wall_points_count,
            "materials": materials_count,
            "clients": clients_count,
        },
        "score": {
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "percent": readiness_percent,
        },
        "next_actions": next_actions,
        "next_action": next_action,
    }


@app.get("/projects/mvp-readiness-summary")
def get_projects_mvp_readiness_summary():
    projects = data_manager.get_all_projects()
    rows = []
    ready_projects = 0
    blocking_reasons: Dict[str, int] = {}
    blocking_reasons_details_map: Dict[str, Dict[str, Any]] = {}
    action_queue_map: Dict[str, Dict[str, Any]] = {}
    score_sum = 0

    for project in projects:
        project_id = int(project.get("id", 0) or 0)
        if project_id <= 0:
            continue
        readiness = _build_project_mvp_readiness_payload(project_id)
        is_ready = bool(readiness.get("ready", False))
        if is_ready:
            ready_projects += 1
        missing = list(readiness.get("missing") or [])
        score_percent = int((readiness.get("score") or {}).get("percent", 0) or 0)
        score_sum += score_percent
        for reason in missing:
            key = str(reason or "").strip()
            if not key:
                continue
            blocking_reasons[key] = int(blocking_reasons.get(key, 0)) + 1
        for detail in list(readiness.get("missing_details") or []):
            check = str(detail.get("check", "") or "").strip()
            if not check:
                continue
            row = blocking_reasons_details_map.get(check)
            if row is None:
                blocking_reasons_details_map[check] = {
                    "check": check,
                    "label": str(detail.get("label", check)),
                    "priority": int(detail.get("priority", 99) or 99),
                    "count": 1,
                }
            else:
                row["count"] = int(row.get("count", 0) or 0) + 1
        for action in list(readiness.get("next_actions") or []):
            code = str(action.get("code", "") or "").strip()
            if not code:
                continue
            queue_item = action_queue_map.get(code)
            if queue_item is None:
                action_queue_map[code] = {
                    "code": code,
                    "label": str(action.get("label", "") or ""),
                    "priority": int(action.get("priority", 99) or 99),
                    "route": str(action.get("route", "") or ""),
                    "affected_projects": 1,
                }
            else:
                queue_item["affected_projects"] = int(queue_item.get("affected_projects", 0) or 0) + 1
        rows.append(
            {
                "project_id": project_id,
                "project_title": str(project.get("title", "") or ""),
                "ready": is_ready,
                "readiness_score": score_percent,
                "missing_count": len(missing),
                "missing": missing,
                "missing_labels": list(readiness.get("missing_labels") or []),
                "missing_details": list(readiness.get("missing_details") or []),
                "next_actions": list(readiness.get("next_actions") or []),
                "next_action": readiness.get("next_action"),
            }
        )

    rows.sort(key=lambda item: (bool(item.get("ready", False)), -int(item.get("missing_count", 0)), int(item.get("project_id", 0))))
    blocking_reasons_details = list(blocking_reasons_details_map.values())
    blocking_reasons_details.sort(
        key=lambda item: (-int(item.get("count", 0)), int(item.get("priority", 99)), str(item.get("check", "")))
    )
    action_queue = list(action_queue_map.values())
    action_queue.sort(key=lambda item: (int(item.get("priority", 99)), -int(item.get("affected_projects", 0)), str(item.get("code", ""))))
    next_global_action = action_queue[0] if len(action_queue) > 0 else None
    total_projects = len(rows)
    avg_readiness_score = round((score_sum / total_projects), 2) if total_projects > 0 else 0.0
    readiness_bands = {
        "critical": 0,  # 0-49%
        "risk": 0,      # 50-99%
        "ready": 0,     # 100%
    }
    for row in rows:
        score = int(row.get("readiness_score", 0) or 0)
        if score >= 100:
            readiness_bands["ready"] += 1
        elif score >= 50:
            readiness_bands["risk"] += 1
        else:
            readiness_bands["critical"] += 1
    return {
        "total_projects": total_projects,
        "ready_projects": ready_projects,
        "not_ready_projects": max(0, total_projects - ready_projects),
        "avg_readiness_score": avg_readiness_score,
        "readiness_bands": readiness_bands,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "blocking_reasons": blocking_reasons,
        "blocking_reasons_details": blocking_reasons_details,
        "action_queue": action_queue,
        "next_global_action": next_global_action,
        "projects": rows,
    }

# --- ENDPOINTY BAZY DANYCH ---
@app.get("/db/materials")
async def get_materials(include_deleted: bool = False):
    return data_manager.get_materials(include_deleted=include_deleted)


@app.post("/db/materials")
async def create_material(material: MaterialCreate):
    name = str(material.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Brak nazwy materialu")
    if float(material.price_per_m2 or 0.0) <= 0:
        raise HTTPException(status_code=400, detail="Cena materialu musi byc > 0")
    if int(material.thickness or 0) <= 0:
        raise HTTPException(status_code=400, detail="Grubosc materialu musi byc > 0")
    try:
        material_id = data_manager.create_material(
            name=name,
            price_per_m2=float(material.price_per_m2),
            thickness=int(material.thickness),
            category=material.category,
            material_kind=material.material_kind,
            unit=material.unit,
            is_library=material.is_library,
            stock_quantity=material.stock_quantity,
            min_stock=material.min_stock,
            purchase_type=material.purchase_type,
            supplier=material.supplier,
            wholesaler=material.wholesaler,
            material_code=material.material_code,
            format_length_mm=material.format_length_mm,
            format_width_mm=material.format_width_mm,
            pack_size=material.pack_size,
            parameter_json=material.parameter_json,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "success", "id": material_id}


@app.get("/db/overview")
async def get_db_overview():
    return data_manager.get_db_overview()


@app.get("/api/db/materials/low-stock")
async def get_low_stock_materials(limit: int = 200):
    safe_limit = _normalize_limit(limit, default=200, max_value=2000)
    items = data_manager.get_low_stock_materials(limit=safe_limit)
    return {
        "status": "ok",
        "total": len(items),
        "limit": safe_limit,
        "items": items,
    }


@app.get("/db/scan-invoices")
async def scan_invoices():
    import os
    from pypdf import PdfReader
    import re
    
    scan_folders = [
        r"C:\pythonproject\tech_modul\faktury",
        os.path.expanduser(r"~\Downloads")
    ]
    
    results = []
    
    for folder in scan_folders:
        if not os.path.exists(folder):
            continue
            
        try:
            files = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
            for filename in files[:20]: # Limit to avoid timeouts
                path = os.path.join(folder, filename)
                try:
                    reader = PdfReader(path)
                    text = ""
                    for i in range(min(len(reader.pages), 2)):
                        text += reader.pages[i].extract_text()
                    
                    # Prosty "AI" parser (RegEx)
                    inv_nr_match = re.search(r"(?:Nr|Faktura nr|Numer)[:\s]*([/\w\-\(\)]+)", text, re.I)
                    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
                    nip_match = re.search(r"NIP[:\s]*(\d{3}-\d{3}-\d{2}-\d{2})", text, re.I)
                    
                    # Szukamy kwot: Netto, VAT, Brutto
                    net_match = re.search(r"(?:Netto|Wartość netto)[:\s]*([\d\s,]+\.\d{2})", text, re.I)
                    vat_match = re.search(r"(?:Kwota VAT|VAT)[:\s]*([\d\s,]+\.\d{2})", text, re.I)
                    gross_match = re.search(r"(?:Razem do zapłaty|Kwota brutto|Wartość brutto|Razem)[:\s]*([\d\s,]+\.\d{2})", text, re.I)
                    
                    def to_float(val):
                        if not val: return 0.0
                        return float(val.replace(" ", "").replace(",", "."))

                    net = to_float(net_match.group(1)) if net_match else 0.0
                    vat = to_float(vat_match.group(1)) if vat_match else (net * 0.23 if net > 0 else 0.0)
                    gross = to_float(gross_match.group(1)) if gross_match else (net + vat)

                    results.append({
                        "filename": filename,
                        "folder": "Projekt" if "tech_modul" in folder else "Pobrane",
                        "nr": inv_nr_match.group(1).strip() if inv_nr_match else "Nieznany",
                        "date": date_match.group(1) if date_match else "Brak daty",
                        "nip": nip_match.group(1) if nip_match else "Brak NIP",
                        "net": net,
                        "vat": vat,
                        "total": gross,
                        "status": "DRAFT",
                        "raw_text": text[:500]
                    })
                except Exception as e:
                    print(f"Błąd czytania {filename}: {e}")
                    continue
        except Exception as e:
            print(f"Błąd skanowania folderu {folder}: {e}")
            continue
            
    return results


class InvoiceCreate(BaseModel):
    nr: str
    date: str
    nip: str
    net: float
    vat: float
    gross: float
    folder: str = "Projekt"

class InvoiceLineItemUpdate(BaseModel):
    review_status: str | None = None
    selected_material_id: int | None = None
    selected_material_name: str | None = None
    notes: str | None = None
    quantity: float | None = None
    unit: str | None = None
    unit_price_net: float | None = None
    unit_price_gross: float | None = None
    total_net: float | None = None
    total_gross: float | None = None


class InvoiceConfirmRequest(BaseModel):
    line_item_ids: List[int] = []


class InvoiceSourceCheckRequest(BaseModel):
    since_date: str = ""
    scan_local: bool = True
    scan_email: bool = True
    scan_telegram: bool = False
    scan_whatsapp: bool = False
    local_dirs: List[str] = []
    recursive: bool = False
    max_local_files: int = 300
    max_email_messages: int = 30
    worker_name: str = ""


def _invoice_line_confidence(parsed: Any) -> float:
    return max(
        float(getattr(parsed, "ai_confidence", 0.0) or 0.0),
        float(getattr(parsed, "ocr_confidence", 0.0) or 0.0),
    )


def _invoice_line_items_from_parsed(parsed: Any) -> List[Dict[str, Any]]:
    confidence = _invoice_line_confidence(parsed)
    rows: List[Dict[str, Any]] = []
    for item in tuple(getattr(parsed, "items", ()) or ()):
        rows.append(
            {
                "name": str(getattr(item, "name", "") or "").strip(),
                "raw_line": str(getattr(item, "raw_line", "") or "").strip(),
                "quantity": float(getattr(item, "quantity", 0.0) or 0.0),
                "unit": str(getattr(item, "unit", "") or "").strip(),
                "unit_price_net": float(getattr(item, "unit_price_net", 0.0) or 0.0),
                "unit_price_gross": float(getattr(item, "unit_price_gross", 0.0) or 0.0),
                "total_price_net": float(getattr(item, "total_price_net", 0.0) or 0.0),
                "total_price_gross": float(getattr(item, "total_price_gross", 0.0) or 0.0),
                "vat_rate": str(getattr(item, "vat_rate", "") or "").strip(),
                "material_type": str(getattr(item, "material_type", "") or "").strip(),
                "thickness_mm": str(getattr(item, "thickness_mm", "") or "").strip(),
                "parse_source": str(getattr(item, "parse_source", "") or "").strip(),
                "confidence": confidence,
            }
        )
    return rows


def _import_parsed_invoice_to_db(*, payload: bytes, filename: str, parsed: Any) -> Dict[str, Any]:
    payload_hash = hashlib.sha256(payload).hexdigest()
    line_confidence = _invoice_line_confidence(parsed)
    line_items = _invoice_line_items_from_parsed(parsed)
    result = data_manager.import_invoice_with_lines(
        invoice_nr=str(getattr(parsed, "invoice_number", "") or "").strip() or f"UPLOAD-{filename}",
        invoice_date=str(getattr(parsed, "invoice_date", "") or "").strip() or datetime.now().strftime("%Y-%m-%d"),
        nip=str(getattr(parsed, "buyer_nip", "") or "").strip(),
        supplier=str(getattr(parsed, "supplier", "") or "").strip(),
        currency=str(getattr(parsed, "currency", "PLN") or "PLN").strip().upper(),
        total_net=float(getattr(parsed, "total_net", 0.0) or 0.0),
        total_vat=float(getattr(parsed, "total_vat", 0.0) or 0.0),
        total_gross=float(getattr(parsed, "total_gross", 0.0) or 0.0),
        payload_hash=payload_hash,
        source_filename=filename,
        parse_method=str(getattr(parsed, "extraction_method", "") or "").strip(),
        parse_confidence=line_confidence,
        line_items=line_items,
    )
    return {
        "invoice_id": int(result.get("invoice_id", 0) or 0),
        "is_duplicate": bool(result.get("is_duplicate", False)),
        "duplicate_reason": str(result.get("duplicate_reason", "") or ""),
        "line_items_total": 0 if bool(result.get("is_duplicate", False)) else len(line_items),
    }

@app.get("/db/invoices")
async def get_invoices():
    return data_manager.get_invoices_with_line_stats()

@app.post("/db/invoices")
async def create_invoice(invoice: InvoiceCreate):
    inv_id = data_manager.create_invoice(
        nr=invoice.nr,
        date=invoice.date,
        nip=invoice.nip,
        net=invoice.net,
        vat=invoice.vat,
        gross=invoice.gross,
        folder=invoice.folder
    )
    return {"status": "success", "id": inv_id}


@app.post("/api/db/invoices/import")
async def import_invoice_pdf(file: UploadFile = File(...)):
    filename = str(file.filename or "").strip()
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail=_error_detail("Do importu obslugiwane sa tylko pliki PDF"))
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail=_error_detail("Pusty plik"))

    try:
        parsed = parse_invoice_pdf_bytes(payload, source_name=filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=_error_detail(f"Blad parsera faktury: {exc}"))

    imported = _import_parsed_invoice_to_db(payload=payload, filename=filename, parsed=parsed)
    return {"status": "success", **imported}


@app.post("/api/db/invoices/check-sources")
async def check_invoice_sources(payload: InvoiceSourceCheckRequest):
    since_date = _validate_iso_date(payload.since_date, field_name="since_date", required=False)
    since_dt = None
    if since_date:
        since_dt = datetime.strptime(since_date[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)

    local_checked = 0
    local_imported = 0
    local_duplicates = 0
    local_errors = 0
    email_checked = 0
    email_imported = 0
    email_duplicates = 0
    email_errors = 0
    warnings: List[str] = []

    if bool(payload.scan_local):
        default_dirs = [
            Path(r"C:\PythonProject\TECH_modul\Faktury"),
            Path.home() / "Downloads",
            Path(r"C:\Users\mykyt\Downloads"),
        ]
        raw_dirs = [str(x or "").strip() for x in list(payload.local_dirs or []) if str(x or "").strip()]
        scan_dirs = [Path(x) for x in raw_dirs] if raw_dirs else default_dirs
        unique_files: Dict[str, Path] = {}
        for folder in scan_dirs:
            if not folder.exists() or not folder.is_dir():
                continue
            iterator = folder.rglob("*.pdf") if bool(payload.recursive) else folder.glob("*.pdf")
            for pdf_path in iterator:
                try:
                    key = str(pdf_path.resolve()).strip().lower()
                except Exception:
                    key = str(pdf_path).strip().lower()
                if key:
                    unique_files[key] = pdf_path

        files = list(unique_files.values())
        files.sort(key=lambda p: float(p.stat().st_mtime) if p.exists() else 0.0, reverse=True)
        if int(payload.max_local_files or 0) > 0:
            files = files[: int(payload.max_local_files)]

        for pdf_path in files:
            local_checked += 1
            try:
                stat = pdf_path.stat()
                modified_dt = datetime.fromtimestamp(float(stat.st_mtime), tz=timezone.utc)
                if since_dt is not None and modified_dt < since_dt:
                    continue
                file_name = str(pdf_path.name or "").strip()
                raw = pdf_path.read_bytes()
                if not raw:
                    continue
                parsed = parse_invoice_pdf_bytes(raw, source_name=file_name)
                imported = _import_parsed_invoice_to_db(payload=raw, filename=file_name, parsed=parsed)
                if bool(imported.get("is_duplicate", False)):
                    local_duplicates += 1
                else:
                    local_imported += 1
            except Exception:
                local_errors += 1

    if bool(payload.scan_email):
        try:
            attachments = fetch_invoice_pdf_attachments(
                worker_name=str(payload.worker_name or "").strip(),
                max_messages=int(payload.max_email_messages or 30),
            )
        except Exception as exc:
            warnings.append(f"Email check error: {exc}")
            attachments = []

        for attachment in attachments:
            email_checked += 1
            try:
                received_at = str(getattr(attachment, "received_at", "") or "").strip()
                if since_dt is not None and received_at:
                    try:
                        parsed_dt = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
                        if parsed_dt.tzinfo is None:
                            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                        if parsed_dt.astimezone(timezone.utc) < since_dt:
                            continue
                    except Exception:
                        pass
                filename = str(getattr(attachment, "filename", "") or "").strip() or "mail_attachment.pdf"
                raw = bytes(getattr(attachment, "payload", b"") or b"")
                if not raw:
                    continue
                parsed = parse_invoice_pdf_bytes(raw, source_name=filename)
                imported = _import_parsed_invoice_to_db(payload=raw, filename=filename, parsed=parsed)
                if bool(imported.get("is_duplicate", False)):
                    email_duplicates += 1
                else:
                    email_imported += 1
            except Exception:
                email_errors += 1

    if bool(payload.scan_telegram):
        warnings.append("Telegram source check is not implemented in Phase 1 endpoint yet.")
    if bool(payload.scan_whatsapp):
        warnings.append("WhatsApp source check is not implemented in Phase 1 endpoint yet.")

    total_checked = local_checked + email_checked
    total_imported = local_imported + email_imported
    total_duplicates = local_duplicates + email_duplicates
    total_errors = local_errors + email_errors

    return {
        "status": "success",
        "since_date": since_date,
        "summary": {
            "checked": total_checked,
            "imported": total_imported,
            "duplicates": total_duplicates,
            "errors": total_errors,
        },
        "local": {
            "checked": local_checked,
            "imported": local_imported,
            "duplicates": local_duplicates,
            "errors": local_errors,
        },
        "email": {
            "checked": email_checked,
            "imported": email_imported,
            "duplicates": email_duplicates,
            "errors": email_errors,
        },
        "warnings": warnings,
    }


@app.get("/api/db/invoices/{invoice_id}/line-items")
async def get_invoice_line_items(invoice_id: int):
    rows = data_manager.get_invoice_line_items(int(invoice_id))
    return {"status": "ok", "invoice_id": int(invoice_id), "items": rows, "total": len(rows)}


@app.patch("/api/db/invoices/{invoice_id}/line-items/{line_item_id}")
async def patch_invoice_line_item(invoice_id: int, line_item_id: int, payload: InvoiceLineItemUpdate):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail=_error_detail("Brak pol do aktualizacji"))

    if "review_status" in updates:
        status = str(updates.get("review_status", "") or "").strip().lower()
        allowed = {"needs_review", "confirmed", "skipped", "exported"}
        if status not in allowed:
            raise HTTPException(status_code=400, detail=_error_detail("Nieobslugiwany review_status"))
        updates["review_status"] = status

        if status == "confirmed":
            current_items = data_manager.get_invoice_line_items(int(invoice_id))
            current = next((x for x in current_items if int(x.get("id", 0) or 0) == int(line_item_id)), None)
            if current is None:
                raise HTTPException(status_code=404, detail=_error_detail("Nie znaleziono pozycji faktury"))
            selected_material_id = updates.get("selected_material_id")
            if selected_material_id in {None, 0, ""}:
                selected_material_id = current.get("selected_material_id")
            if selected_material_id in {None, 0, ""}:
                raise HTTPException(status_code=400, detail=_error_detail("Do potwierdzenia wymagany jest selected_material_id"))
            confidence = float(current.get("confidence", 0.0) or 0.0)
            unit = str((updates.get("unit") if "unit" in updates else current.get("unit", "")) or "").strip()
            if confidence < 0.60 or not unit:
                raise HTTPException(status_code=400, detail=_error_detail("Niska pewnosc lub brak jednostki: pozycja musi pozostac w review"))

    ok = data_manager.update_invoice_line_item(
        invoice_id=int(invoice_id),
        line_item_id=int(line_item_id),
        updates=updates,
    )
    if not ok:
        raise HTTPException(status_code=404, detail=_error_detail("Nie znaleziono pozycji faktury lub brak zmian"))
    return {"status": "success"}


@app.post("/api/db/invoices/{invoice_id}/confirm")
async def confirm_invoice(invoice_id: int, payload: InvoiceConfirmRequest):
    try:
        summary = data_manager.confirm_invoice_to_arrivals(
            invoice_id=int(invoice_id),
            line_item_ids=[int(x) for x in (payload.line_item_ids or []) if int(x) > 0],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=_error_detail(str(exc)))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=_error_detail(f"Blad potwierdzania faktury: {exc}"))
    return {"status": "success", **summary}

@app.get("/db/tax-summary")
async def get_tax_summary():
    return data_manager.get_tax_summary()


@app.get("/db/clients")
async def get_clients():
    return data_manager.get_clients()


@app.post("/db/clients")
async def create_client(client: ClientCreate):
    name = str(client.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Brak nazwy kontrahenta")
    if str(client.type or "person") not in {"person", "b2b"}:
        raise HTTPException(status_code=400, detail="Nieobslugiwany typ kontrahenta")
    if str(client.status or "active") not in {"active", "vip", "archived"}:
        raise HTTPException(status_code=400, detail="Nieobslugiwany status kontrahenta")
    email = str(client.email or "").strip()
    if email and "@" not in email:
        raise HTTPException(status_code=400, detail="Niepoprawny email kontrahenta")
    client_id = data_manager.create_client(
        name=name,
        location=str(client.location or ""),
        address=str(client.address or ""),
        email=email,
        phone=str(client.phone or ""),
        client_type=str(client.type or "person"),
        status=str(client.status or "active"),
    )
    return {"status": "success", "id": client_id}

from .agent_engine import TechModulAgent

# --- INICJALIZACJA AGENTA ---
# Provider czytajÄ…cy moduĹ‚y z SQLite (projekt demo = id 1).
class DbModulesProvider:
    def __init__(self, project_id: int = 1):
        self.project_id = project_id

    def get_selected_modules(self):
        return data_manager.get_project_modules(self.project_id)

agent = TechModulAgent(DbModulesProvider())

class CommandRequest(BaseModel):
    text: str
    project_id: int = 1

class AgentChange(BaseModel):
    id: int
    name: str
    param: str
    old: int
    new: int

class ApplyRequest(BaseModel):
    action: str
    changes: list[AgentChange]
    project_id: int = 1


class OperationTargetPayload(BaseModel):
    id: str = ""
    name: str = ""
    scope: str = ""


class ModuleOperationRequest(BaseModel):
    action: str
    target: OperationTargetPayload
    params: Dict[str, Any] = {}
    source: str = "api"


class ModuleBulkOperationRequest(BaseModel):
    action: str
    module_ids: list[str]
    params: Dict[str, Any] = {}
    source: str = "api"


class WallOperationRequest(BaseModel):
    action: str
    target: OperationTargetPayload
    params: Dict[str, Any] = {}
    source: str = "api"


def _build_agent_module_operations(project_id: int) -> ModuleOperations:
    return ModuleOperations(
        repository=SqliteProjectModuleRepository(data_manager=data_manager, project_id=project_id)
    )

@app.post("/agent/command")
async def execute_agent_command(request: CommandRequest):
    cmd = agent.parse_command(request.text)
    if cmd.get("action") != "modify_dimension":
        raise HTTPException(status_code=400, detail="Nie zrozumiaĹ‚em polecenia.")

    param = str(cmd.get("param", "") or "").strip().lower()
    operation = str(cmd.get("operation", "set") or "set").strip().lower()
    value = int(cmd.get("value", 0) or 0)
    action_map = {
        "depth": "module.set_depth",
        "width": "module.set_width",
        "height": "module.set_height",
    }
    if param not in action_map:
        raise HTTPException(status_code=400, detail=f"NieobsĹ‚ugiwany parametr: {param}")

    project_id = int(request.project_id or 1)
    modules = data_manager.get_project_modules(project_id)
    scoped_operations = _build_agent_module_operations(project_id)
    preview_changes = []

    for row in modules:
        old_value = int(row.get(param, 0) or 0)
        if operation == "add":
            new_value = old_value + value
        elif operation == "sub":
            new_value = old_value - value
        else:
            new_value = value

        result = scoped_operations.execute(
            action=action_map[param],
            target={"id": str(row.get("id", "") or "")},
            params={f"{param}_mm": float(new_value)},
            mode="preview",
            source="agent",
        ).to_dict()

        status = str(result.get("status", "") or "").strip().lower()
        if status != "ok":
            detail = result.get("errors") or [{"message": "Validation failed"}]
            msg = str(detail[0].get("message", "Validation failed") if isinstance(detail, list) and detail else detail)
            raise HTTPException(status_code=400, detail=msg)

        preview_changes.append(
            {
                "id": int(row.get("id", 0) or 0),
                "name": str(row.get("name", "") or ""),
                "param": param,
                "old": old_value,
                "new": int(new_value),
            }
        )

    return {
        "type": "preview",
        "action": "modify_dimension",
        "changes": preview_changes,
    }

@app.post("/agent/apply")
async def apply_agent_changes(request: ApplyRequest):
    """
    Stosuje potwierdzone przez uĹĽytkownika zmiany w SQLite.
    AI sam z siebie nigdy nie wywoĹ‚uje tego endpointu â€” tylko po akceptacji w UI.
    """
    applied = []
    skipped = []
    action_map = {
        "depth": "module.set_depth",
        "width": "module.set_width",
        "height": "module.set_height",
    }

    project_id = int(request.project_id or 1)
    scoped_operations = _build_agent_module_operations(project_id)

    for ch in request.changes:
        param = str(ch.param or "").strip().lower()
        action = action_map.get(param, "")
        if not action:
            raise HTTPException(status_code=400, detail=f"NieobsĹ‚ugiwany parametr: {param}")

        result = scoped_operations.execute(
            action=action,
            target={"id": str(ch.id)},
            params={f"{param}_mm": float(ch.new)},
            mode="apply",
            source="agent",
        ).to_dict()
        status = str(result.get("status", "") or "").strip().lower()
        if status == "ok":
            applied.append({"id": ch.id, "param": ch.param, "new": ch.new})
        elif status in {"validation_error", "conflict"}:
            errors = result.get("errors") or []
            reason = str(errors[0].get("message", "validation_error") if errors else "validation_error")
            skipped.append({"id": ch.id, "reason": reason})
        else:
            raise HTTPException(status_code=500, detail=result)
    return {
        "status": "applied",
        "count": len(applied),
        "applied": applied,
        "skipped": skipped,
    }


def _raise_for_operation_status(payload: Dict[str, Any]) -> None:
    status = str(payload.get("status", "") or "").strip().lower()
    if status in {"validation_error", "conflict"}:
        raise HTTPException(status_code=400, detail=payload)
    if status in {"error"}:
        raise HTTPException(status_code=500, detail=payload)


@app.post("/operations/module/preview")
async def preview_module_operation(request: ModuleOperationRequest):
    result = module_operations.execute(
        action=request.action,
        target=request.target.model_dump(),
        params=request.params,
        mode="preview",
        source=str(request.source or "api"),
    )
    payload = result.to_dict()
    _raise_for_operation_status(payload)
    return payload


@app.post("/operations/module/apply")
async def apply_module_operation(request: ModuleOperationRequest):
    result = module_operations.execute(
        action=request.action,
        target=request.target.model_dump(),
        params=request.params,
        mode="apply",
        source=str(request.source or "api"),
    )
    payload = result.to_dict()
    _raise_for_operation_status(payload)
    return payload


@app.get("/config/modules/{module_id}/valuation")
async def get_module_valuation(module_id: str):
    """Oblicza precyzyjnÄ… wycenÄ™ moduĹ‚u na podstawie BOM i cen z bazy."""
    try:
        module = module_operations._resolve_module({"id": module_id})
        # CatalogStoreJson automatycznie synchronizuje ceny z bazy SQLite (data_manager)
        breakdown = calculate_module_cost_breakdown(module, module_operations._catalog)
        return breakdown
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/modules/{module_id}/export/project")
async def export_module_project(module_id: str):
    """
    Eksportuje moduĹ‚ do formatu .project (GibLab) i synchronizuje z GitLabem.
    """
    module = module_operations.get_module(module_id)
    if not module:
        raise HTTPException(status_code=404, detail="ModuĹ‚ nie istnieje.")
    
    # 1. Wygeneruj plik tymczasowy / staĹ‚y w folderze eksportu
    export_dir = os.path.join(os.getcwd(), "exports", "projects")
    os.makedirs(export_dir, exist_ok=True)
    
    safe_name = "".join(c if c.isalnum() else "_" for c in module.name or "module")
    filename = f"{safe_name}_{module_id}.project"
    file_path = os.path.join(export_dir, filename)
    
    try:
        # 2. Eksport do XML
        export_module_to_3dc_project_xml(module, file_path)
        
        # 3. GitLab Sync
        git_msg = f"Export moduĹ‚u {module.name} (ID: {module_id}) do .project"
        git_res = git_sync_project_file(file_path, git_msg)
        
        return {
            "status": "success",
            "filename": filename,
            "path": file_path,
            "gitlab": git_res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BĹ‚Ä…d eksportu: {str(e)}")


@app.post("/operations/module/bulk/preview")
async def preview_bulk_module_operation(request: ModuleBulkOperationRequest):
    warnings: list[str] = []
    errors: list[dict[str, str]] = []
    changes: list[dict[str, Any]] = []

    for module_id in request.module_ids:
        result = module_operations.execute(
            action=request.action,
            target={"id": str(module_id or "")},
            params=request.params,
            mode="preview",
            source=str(request.source or "api"),
        ).to_dict()
        status = str(result.get("status", "") or "").strip().lower()
        warnings.extend([str(w) for w in (result.get("warnings") or [])])
        changes.extend(list(result.get("changes") or []))
        if status != "ok" or not bool(result.get("can_apply", False)):
            msg = str((result.get("errors") or [{}])[0].get("message", "Preview failed"))
            errors.append({"module_id": str(module_id), "message": msg})

    can_apply = len(errors) == 0 and len(changes) > 0
    return {
        "status": "ok" if can_apply else "validation_error",
        "can_apply": can_apply,
        "action": request.action,
        "warnings": warnings,
        "errors": errors,
        "changes": changes,
    }


@app.post("/operations/module/bulk/apply")
async def apply_bulk_module_operation(request: ModuleBulkOperationRequest):
    applied_count = 0
    errors: list[dict[str, str]] = []
    warnings: list[str] = []

    for module_id in request.module_ids:
        result = module_operations.execute(
            action=request.action,
            target={"id": str(module_id or "")},
            params=request.params,
            mode="apply",
            source=str(request.source or "api"),
        ).to_dict()
        status = str(result.get("status", "") or "").strip().lower()
        warnings.extend([str(w) for w in (result.get("warnings") or [])])
        if status == "ok":
            applied_count += 1
        else:
            msg = str((result.get("errors") or [{}])[0].get("message", "Apply failed"))
            errors.append({"module_id": str(module_id), "message": msg})

    return {
        "status": "ok" if applied_count > 0 and len(errors) == 0 else "validation_error",
        "applied_count": applied_count,
        "warnings": warnings,
        "errors": errors,
    }


@app.get("/wall/{wall_name}")
async def get_wall_points(wall_name: str):
    return wall_operations.get_points(wall_name)


@app.post("/operations/wall/preview")
async def preview_wall_operation(request: WallOperationRequest):
    result = wall_operations.execute(
        action=request.action,
        target=request.target.model_dump(),
        params=request.params,
        mode="preview",
        source=str(request.source or "api"),
    )
    payload = result.to_dict()
    _raise_for_operation_status(payload)
    return payload


@app.post("/operations/wall/apply")
async def apply_wall_operation(request: WallOperationRequest):
    result = wall_operations.execute(
        action=request.action,
        target=request.target.model_dump(),
        params=request.params,
        mode="apply",
        source=str(request.source or "api"),
    )
    payload = result.to_dict()
    _raise_for_operation_status(payload)
    return payload

@app.get("/")
def read_root():
    return {"status": "online", "message": "Witaj w sercu TECH ModuĹ‚ Professional!"}


@app.post("/system/shutdown")
async def shutdown_system():
    """Zamyka serwer backendowy i próbuje ubić frontend (node)."""
    import os
    import signal
    import subprocess
    
    print("Otrzymano polecenie zamknięcia systemu...")
    
    # Próbujemy zabić procesy na porcie 3000 (frontend)
    try:
        subprocess.run([
            "powershell", 
            "-Command", 
            "Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
        ], capture_output=True)
    except:
        pass
        
    # Samobójstwo procesu backendu
    os.kill(os.getpid(), signal.SIGTERM)
    return {"status": "shutdown_initiated"}


@app.get("/system/summary")
def get_system_summary():
    db_overview = data_manager.get_db_overview()
    return {
        "status": "online",
        "api_version": app.version,
        "engine": "TECH-V4",
        "db": db_overview,
    }


def _safe_parse_spec_json(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    try:
        parsed = json.loads(str(raw or "{}"))
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {}


def _normalized_order_state(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "UNKNOWN"
    return text.upper()


@app.get("/api/dashboard/v1")
def get_dashboard_v1(period_days: int = 30, top_limit: int = 5):
    safe_period_days = _normalize_limit(period_days, default=30, max_value=365)
    safe_top_limit = _normalize_limit(top_limit, default=5, max_value=20)
    now_utc = datetime.now(timezone.utc)

    projects = data_manager.get_all_projects()
    orders = data_manager.get_orders(limit=5000)
    mvp_summary = get_projects_mvp_readiness_summary()

    closed_project_statuses = {"zakonczone", "zamkniete", "archived", "anulowane"}
    active_projects_count = sum(
        1
        for project in projects
        if str(project.get("status", "") or "").strip().lower() not in closed_project_statuses
    )

    orders_by_state: Dict[str, int] = {}
    for order in orders:
        state = _normalized_order_state(order.get("status"))
        orders_by_state[state] = int(orders_by_state.get(state, 0) or 0) + 1

    total_service_items = 0
    ready_items_count = 0
    manual_review_items_count = 0
    missing_required_inputs_count = 0
    blocker_counts: Dict[str, int] = {}

    for order in orders:
        spec = _safe_parse_spec_json(order.get("spec_json"))
        rows = spec.get("service_rows")
        if not isinstance(rows, list):
            rows = spec.get("positions", [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            service_mode = str(row.get("serviceMode") or row.get("service_mode") or "").strip()
            pricing = row.get("servicePricing")
            if not isinstance(pricing, dict):
                continue
            if service_mode and service_mode not in SERVICE_MODES:
                continue
            total_service_items += 1
            pricing_status = str(pricing.get("pricing_status", "") or "").strip().lower()
            if pricing_status == "ready":
                ready_items_count += 1
            elif pricing_status == "manual_review":
                manual_review_items_count += 1

            reasons = pricing.get("manual_review_reasons")
            if isinstance(reasons, list):
                for reason_raw in reasons:
                    reason = str(reason_raw or "").strip()
                    if not reason:
                        continue
                    blocker_counts[reason] = int(blocker_counts.get(reason, 0) or 0) + 1
                    if reason.startswith("missing_"):
                        missing_required_inputs_count += 1

            flags = pricing.get("validation_flags")
            if isinstance(flags, list):
                for flag_raw in flags:
                    flag = str(flag_raw or "").strip()
                    if not flag:
                        continue
                    blocker_counts[flag] = int(blocker_counts.get(flag, 0) or 0) + 1

    top_blockers = [
        {"reason": key, "count": int(value)}
        for key, value in sorted(blocker_counts.items(), key=lambda item: int(item[1]), reverse=True)[:safe_top_limit]
    ]

    from src.core.operations_store import OperationsStore

    operations_store = OperationsStore()
    issues = operations_store.list_issues()
    routes = operations_store.list_routes()
    today_iso = date.today().strftime("%Y-%m-%d")

    active_issues = [i for i in issues if str(i.status or "").strip().lower() != "zamkniete"]
    overdue_issues_count = sum(1 for i in active_issues if bool(i.is_overdue()))
    critical_issues_count = sum(1 for i in active_issues if str(i.priority_manual or "").strip().lower() == "krytyczny")

    active_routes = [r for r in routes if str(r.status or "").strip().lower() not in {"wykonane", "anulowane"}]
    routes_overdue_count = sum(
        1
        for r in active_routes
        if str(getattr(r, "planned_date", "") or "").strip()
        and str(getattr(r, "planned_date", "") or "").strip() < today_iso
    )
    task_load_map: Dict[str, int] = {}
    for route in active_routes:
        key = str(getattr(route, "task_type", "") or "").strip() or "inne"
        task_load_map[key] = int(task_load_map.get(key, 0) or 0) + 1
    workstation_task_load = [
        {"task_type": task_type, "count": int(count)}
        for task_type, count in sorted(task_load_map.items(), key=lambda item: int(item[1]), reverse=True)[:safe_top_limit]
    ]
    recommended_route_actions_count = len(operations_store.list_priority_candidates(status="all"))

    workers = kiosk_service.list_workers()
    active_sessions = [w for w in workers if bool(w.get("active"))]
    sessions_missing_linkage_count = 0
    for worker in active_sessions:
        session = worker.get("session")
        if not isinstance(session, dict):
            sessions_missing_linkage_count += 1
            continue
        has_project_code = bool(str(session.get("project_code", "") or "").strip())
        has_order_id = bool(str(session.get("order_id", "") or "").strip())
        has_workstation = bool(str(session.get("workstation", "") or "").strip())
        if not (has_project_code and has_order_id and has_workstation):
            sessions_missing_linkage_count += 1

    logged_hours_total_period = 0.0
    logged_hours_confidence = "READY"
    try:
        sheets = work_time_store.list_sheets()
        since_dt = now_utc - timedelta(days=safe_period_days)
        for sheet in sheets:
            for entry in list(getattr(sheet, "entries", []) or []):
                hours = float(getattr(entry, "hours", 0.0) or 0.0)
                if hours <= 0:
                    continue
                date_iso = str(getattr(entry, "date_iso", "") or "").strip()
                if not date_iso:
                    continue
                try:
                    entry_dt = datetime.strptime(date_iso[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except Exception:
                    logged_hours_confidence = "PARTIAL"
                    continue
                if entry_dt >= since_dt:
                    logged_hours_total_period += hours
    except Exception:
        logged_hours_confidence = "PARTIAL"

    low_stock_items = data_manager.get_low_stock_materials(limit=200)
    top_critical_low_stock = [
        {
            "id": int(item.get("id", 0) or 0),
            "name": str(item.get("name", "") or ""),
            "missing_qty": float(item.get("missing_qty", 0.0) or 0.0),
            "stock_quantity": float(item.get("stock_quantity", 0.0) or 0.0),
            "min_stock": float(item.get("min_stock", 0.0) or 0.0),
            "unit": str(item.get("unit", "m2") or "m2"),
        }
        for item in low_stock_items[:safe_top_limit]
    ]

    arrivals_recent_count = 0
    arrivals_confidence = "READY"
    try:
        arrivals = data_manager.get_arrivals()
        since_dt = now_utc - timedelta(days=safe_period_days)
        for row in arrivals:
            raw_date = str(row.get("date", "") or "").strip()
            if not raw_date:
                continue
            parsed = None
            for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y", "%d-%m-%Y"):
                try:
                    parsed = datetime.strptime(raw_date[:19], fmt).replace(tzinfo=timezone.utc)
                    break
                except Exception:
                    continue
            if parsed is None:
                arrivals_confidence = "PARTIAL"
                continue
            if parsed >= since_dt:
                arrivals_recent_count += 1
    except Exception:
        arrivals_confidence = "PARTIAL"

    invoices = data_manager.get_invoices_with_line_stats(limit=1000)
    imported_invoices_count = len(invoices)
    confirmed_invoices_count = sum(1 for inv in invoices if str(inv.get("status", "") or "").strip().upper() == "CONFIRMED")
    partial_invoices_count = sum(1 for inv in invoices if str(inv.get("status", "") or "").strip().upper() == "PARTIAL")
    unresolved_invoice_lines_count = 0
    duplicates_prevented_count = 0
    low_confidence_line_count = 0
    low_confidence_confidence = "READY"
    for invoice in invoices:
        total_lines = int(invoice.get("line_items_total", 0) or 0)
        reviewed_lines = int(invoice.get("line_items_reviewed", 0) or 0)
        unresolved_invoice_lines_count += max(total_lines - reviewed_lines, 0)
        if invoice.get("duplicate_of_invoice_id") is not None:
            duplicates_prevented_count += 1
        invoice_id = int(invoice.get("id", 0) or 0)
        if invoice_id <= 0:
            continue
        try:
            line_items = data_manager.get_invoice_line_items(invoice_id)
            low_confidence_line_count += sum(1 for li in line_items if float(li.get("confidence", 0.0) or 0.0) < 0.60)
        except Exception:
            low_confidence_confidence = "PARTIAL"

    price_history_writes_count = 0
    price_history_confidence = "READY"
    try:
        with sqlite3.connect(data_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM price_history
                WHERE notes = 'invoice_confirm_export'
                """
            )
            row = cursor.fetchone()
            price_history_writes_count = int((row[0] if row else 0) or 0)
    except Exception:
        price_history_confidence = "PARTIAL"

    return {
        "generated_at": now_utc.isoformat(),
        "period_days": safe_period_days,
        "operational_summary": {
            "confidence": "READY",
            "source_route": "/workspace",
            "active_projects_count": int(active_projects_count),
            "orders_by_state": orders_by_state,
            "mvp_readiness_distribution": {
                "ready": int((mvp_summary.get("readiness_bands") or {}).get("ready", 0) or 0),
                "risk": int((mvp_summary.get("readiness_bands") or {}).get("risk", 0) or 0),
                "critical": int((mvp_summary.get("readiness_bands") or {}).get("critical", 0) or 0),
                "total_projects": int(mvp_summary.get("total_projects", 0) or 0),
                "avg_readiness_score": float(mvp_summary.get("avg_readiness_score", 0.0) or 0.0),
            },
        },
        "pricing_quality": {
            "confidence": "READY" if total_service_items > 0 else "PARTIAL",
            "source_route": "/orders/new",
            "total_service_items": int(total_service_items),
            "ready_items_count": int(ready_items_count),
            "manual_review_items_count": int(manual_review_items_count),
            "missing_mandatory_inputs_count": int(missing_required_inputs_count),
            "top_blockers": top_blockers,
        },
        "production_risk": {
            "confidence": "READY",
            "source_route": "/operations",
            "overdue_issues_count": int(overdue_issues_count),
            "critical_issues_count": int(critical_issues_count),
            "routes_active_count": int(len(active_routes)),
            "routes_overdue_count": int(routes_overdue_count),
            "workstation_task_load": workstation_task_load,
            "recommended_route_actions_count": int(recommended_route_actions_count),
        },
        "kiosk_labor_activity": {
            "confidence": "READY" if logged_hours_confidence == "READY" else "PARTIAL",
            "source_route": "/time-tracking",
            "active_kiosk_sessions_count": int(len(active_sessions)),
            "sessions_missing_linkage_count": int(sessions_missing_linkage_count),
            "logged_hours_total_period": round(float(logged_hours_total_period), 2),
            "logged_hours_period_days": safe_period_days,
            "logged_hours_quality": logged_hours_confidence,
        },
        "materials_procurement": {
            "confidence": "READY" if arrivals_confidence == "READY" else "PARTIAL",
            "source_route": "/database/warehouse",
            "low_stock_materials_count": int(len(low_stock_items)),
            "top_critical_low_stock": top_critical_low_stock,
            "arrivals_recent_count": int(arrivals_recent_count),
            "arrivals_period_days": safe_period_days,
        },
        "invoice_processing_control": {
            "confidence": "READY" if (low_confidence_confidence == "READY" and price_history_confidence == "READY") else "PARTIAL",
            "source_route": "/database/invoices",
            "imported_invoices_count": int(imported_invoices_count),
            "unresolved_invoice_lines_count": int(unresolved_invoice_lines_count),
            "confirmed_invoices_count": int(confirmed_invoices_count),
            "partial_invoices_count": int(partial_invoices_count),
            "low_confidence_line_count": int(low_confidence_line_count),
            "duplicates_prevented_count": int(duplicates_prevented_count),
            "price_history_writes_count": int(price_history_writes_count),
        },
    }


@app.get("/api/dashboard/v2")
async def get_dashboard_v2_endpoint():
    try:
        data = get_dashboard_v2_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


@app.get("/api/kri/v1")
async def get_kri_v1_endpoint():
    try:
        data = get_kri_v1_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


def get_dashboard_v2_data():
    now_utc = datetime.now(timezone.utc)
    
    # Data Sources
    orders = data_manager.get_orders(limit=1000)
    from src.core.operations_store import OperationsStore
    ops_store = OperationsStore()
    issues = ops_store.list_issues()
    routes = ops_store.list_routes()
    low_stock = data_manager.get_low_stock_materials(limit=50)
    audit_logs = data_manager.get_audit_logs(limit=20)
    
    # 1. Summary KPIs
    active_orders = [o for o in orders if str(o.get("status", "")).lower() not in {"zakonczone", "anulowane"}]
    critical_issues = [i for i in issues if str(i.priority_manual).lower() == "krytyczny" and i.status != "zamkniete"]
    blocked_production = [i for i in issues if i.blocks_production and i.status != "zamkniete"]
    
    # Cost overruns (Real > Estimate)
    overrun_count = 0
    overrun_list = []
    for order in active_orders:
        o_id = order.get("id")
        if not o_id: continue
        costs = data_manager.get_order_cost_entries(int(o_id))
        real_cost = sum(float(c.get("amount_net", 0.0)) for c in costs)
        est_cost = float(order.get("budget", 0.0))
        if est_cost > 0 and real_cost > est_cost:
            overrun_count += 1
            overrun_list.append({
                "id": o_id,
                "title": order.get("title", "Unknown"),
                "real": real_cost,
                "est": est_cost,
                "variance": real_cost - est_cost
            })
    
    # CNC Status
    cnc_tasks = [r for r in routes if "cnc" in str(r.task_type).lower()]
    cnc_summary = {
        "waiting": sum(1 for t in cnc_tasks if t.status == "planowane"),
        "active": sum(1 for t in cnc_tasks if t.status in {"w_trasie", "w toku"}),
        "problem": sum(1 for t in cnc_tasks if t.status == "problem"),
        "done_today": sum(1 for t in cnc_tasks if t.status == "wykonane" and str(t.updated_at)[:10] == str(now_utc)[:10])
    }

    # Inventory events
    recent_movements = data_manager.get_inventory_movements(limit=50)
    recent_scrap = [m for m in recent_movements if m.get("movement_type") == "SCRAP"]
    recent_corrections = [m for m in recent_movements if m.get("movement_type") == "CORRECTION"]

    return {
        "generated_at": now_utc.isoformat(),
        "summary": {
            "active_orders_count": len(active_orders),
            "critical_alarms_count": len(critical_issues),
            "blocked_production_count": len(blocked_production),
            "low_stock_count": len(low_stock),
            "cost_overrun_count": overrun_count,
            "cnc_active_count": cnc_summary["active"],
            "cnc_problem_count": cnc_summary["problem"]
        },
        "production": {
            "cnc_summary": cnc_summary,
            "top_issues": [i.to_dict() for i in critical_issues[:5]]
        },
        "costs": {
            "top_overruns": sorted(overrun_list, key=lambda x: x["variance"], reverse=True)[:5]
        },
        "inventory": {
            "top_low_stock": low_stock[:5],
            "recent_scrap_count": len(recent_scrap),
            "recent_corrections_count": len(recent_corrections)
        },
        "recent_events": audit_logs[:10]
    }


def get_kri_v1_data():
    from src.core.operations_store import OperationsStore
    ops_store = OperationsStore()
    issues = ops_store.list_issues()
    routes = ops_store.list_routes()
    low_stock = data_manager.get_low_stock_materials(limit=100)
    audit_logs = data_manager.get_audit_logs(limit=200)
    orders = data_manager.get_orders(limit=1000)
    
    risks = []
    
    # Deadline / Flow Risk
    overdue_issues = [i for i in issues if i.is_overdue() and i.status != "zamkniete"]
    for i in overdue_issues:
        risks.append({
            "severity": "HIGH" if i.impact_level == "krytyczny" else "MEDIUM",
            "category": "DEADLINE",
            "title": f"Overdue Issue: {i.title}",
            "details": f"Planned for {i.due_date}. Project: {i.project_name}",
            "source_id": i.id,
            "source_type": "issue",
            "timestamp": i.updated_at,
            "actor": i.owner or "Unassigned"
        })
        
    cnc_problems = [r for r in routes if r.status == "problem"]
    for r in cnc_problems:
        risks.append({
            "severity": "CRITICAL",
            "category": "FLOW",
            "title": f"CNC Problem: {r.project_name}",
            "details": r.notes or "No notes provided by operator",
            "source_id": r.id,
            "source_type": "route_task",
            "timestamp": r.updated_at,
            "actor": r.crew or "System"
        })

    # Material Risk (Extended with Shortage Info)
    procurement_data = data_manager.get_procurement_data()
    shortages = [p for p in procurement_data if p["shortage"] > 0]
    for item in shortages:
        risks.append({
            "severity": "CRITICAL" if item["status"] == "CRITICAL" else "HIGH",
            "category": "MATERIAL",
            "title": f"Shortage: {item['name']}",
            "details": f"Missing {item['shortage']} {item['unit']} for active reservations. On hand: {item['qty_on_hand']}",
            "source_id": item["material_id"],
            "source_type": "material_shortage",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": "Procurement"
        })

    # Cost Risk
    for order in orders:
        o_id = order.get("id")
        if not o_id: continue
        costs = data_manager.get_order_cost_entries(int(o_id))
        real_cost = sum(float(c.get("amount_net", 0.0)) for c in costs)
        est_cost = float(order.get("budget", 0.0))
        if est_cost > 0 and real_cost > est_cost * 1.1:
            risks.append({
                "severity": "HIGH" if real_cost > est_cost * 1.3 else "MEDIUM",
                "category": "COST",
                "title": f"Cost Overrun: {order.get('title')}",
                "details": f"Real: {real_cost:.2f} PLN vs Est: {est_cost:.2f} PLN (+{((real_cost/est_cost)-1)*100:.1f}%)",
                "source_id": o_id,
                "source_type": "order_cost",
                "timestamp": datetime.now(timezone.utc).isoformat(), # Ideally last cost entry timestamp
                "actor": order.get("client_name") or "System"
            })

    # Process Risk (Audit Log)
    scrap_events = [l for l in audit_logs if l.get("action") == "INV_SCRAP"]
    if len(scrap_events) > 5:
        risks.append({
            "severity": "MEDIUM",
            "category": "PROCESS",
            "title": "High Scrap Frequency",
            "details": f"{len(scrap_events)} scrap events in recent history.",
            "source_type": "audit_log",
            "timestamp": scrap_events[0].get("timestamp"),
            "actor": "Multiple Workers"
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "risks": risks
    }


@app.get("/api/admin/backups")
async def list_backups_endpoint():
    try:
        from src.safe_mode import get_repo_root
        backup_dir = get_repo_root() / "backups" / "before_migration"
        if not backup_dir.exists():
            return {"backups": []}
            
        files = []
        for f in backup_dir.glob("*.db"):
            stat = f.stat()
            files.append({
                "name": f.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        return {"backups": sorted(files, key=lambda x: x["created_at"], reverse=True)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


@app.delete("/api/projects/{project_id}")
async def delete_project_endpoint(project_id: int, user: str = "System"):
    try:
        data_manager.soft_delete_project(project_id, user_name=user)
        return {"status": "success", "message": f"Project {project_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


@app.delete("/api/materials/{material_id}")
async def delete_material_endpoint(material_id: int, user: str = "System"):
    try:
        # We try to soft delete in both stores to be safe, as 'material' can mean inventory or catalog item in this context
        data_manager.soft_delete_material(material_id, user_name=user)
        catalog_store.soft_delete_catalog_item(material_id)
        return {"status": "success", "message": f"Material {material_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


@app.delete("/api/orders/{order_id}")
async def delete_order_endpoint(order_id: int, user: str = "System"):
    try:
        data_manager.soft_delete_order(order_id, user_name=user)
        return {"status": "success", "message": f"Order {order_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


@app.post("/api/admin/projects/{project_id}/restore")
async def restore_project_endpoint(project_id: int, user: CurrentUser = Depends(get_current_user_info)):
    require_permission(user, Action.RESTORE_DELETED)
    try:
        data_manager.restore_project(project_id, user_name=user.name)
        data_manager.log_action(
            user_name=user.name,
            action="RESTORE_PROJECT",
            target_type="project",
            target_id=str(project_id),
            details=f"Project restored by {user.name} ({user.role})"
        )
        return {"status": "success", "message": f"Project {project_id} restored"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


@app.post("/api/admin/materials/{material_id}/restore")
async def restore_material_endpoint(material_id: int, user: CurrentUser = Depends(get_current_user_info)):
    require_permission(user, Action.RESTORE_DELETED)
    try:
        data_manager.restore_material(material_id, user_name=user.name)
        catalog_store.restore_catalog_item(material_id)
        data_manager.log_action(
            user_name=user.name,
            action="RESTORE_MATERIAL",
            target_type="material",
            target_id=str(material_id),
            details=f"Material restored by {user.name}"
        )
        return {"status": "success", "message": f"Material {material_id} restored"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


@app.post("/api/admin/orders/{order_id}/restore")
async def restore_order_endpoint(order_id: int, user: CurrentUser = Depends(get_current_user_info)):
    require_permission(user, Action.RESTORE_DELETED)
    try:
        data_manager.restore_order(order_id, user_name=user.name)
        data_manager.log_action(
            user_name=user.name,
            action="RESTORE_ORDER",
            target_type="order",
            target_id=str(order_id),
            details=f"Order restored by {user.name}"
        )
        return {"status": "success", "message": f"Order {order_id} restored"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


def _apply_service_pricing_to_spec(spec_payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(spec_payload, dict):
        return {"service_pricing_schema_version": SERVICE_PRICING_PAYLOAD_SCHEMA_VERSION}

    def _price_rows(rows: Any) -> List[Dict[str, Any]]:
        if not isinstance(rows, list):
            return []
        priced_rows: List[Dict[str, Any]] = []
        for raw_row in rows:
            if not isinstance(raw_row, dict):
                continue
            row = dict(raw_row)
            service_mode = str(row.get("serviceMode") or row.get("service_mode") or "").strip()
            if service_mode in SERVICE_MODES:
                pricing_input = row.get("servicePricingInput")
                if not isinstance(pricing_input, dict):
                    pricing_input = {
                        "service_mode": service_mode,
                        "length_mm": 0,
                        "width_mm": 0,
                        "base_thickness_mm": 0,
                        "quantity": int(row.get("quantity") or 1),
                    }
                pricing_result = price_service_item(pricing_input)
                row["servicePricing"] = pricing_result
                row["serviceEstimatedNet"] = float(((pricing_result.get("buckets") or {}).get("net_total") or 0.0))
                row["serviceSummary"] = str(pricing_result.get("summary_text") or "")
            priced_rows.append(row)
        return priced_rows

    spec_payload["positions"] = _price_rows(spec_payload.get("positions", []))

    # Unified editor rows (Phase 1) share the same pricing source of truth.
    if isinstance(spec_payload.get("service_rows"), list):
        spec_payload["service_rows"] = _price_rows(spec_payload.get("service_rows"))

    spec_payload["service_pricing_schema_version"] = SERVICE_PRICING_PAYLOAD_SCHEMA_VERSION
    spec_payload["service_pricing_backend_calculated"] = True
    return spec_payload


@app.post("/api/service-pricing/preview")
def preview_service_pricing(payload: ServicePricingPreviewRequest):
    if not isinstance(payload.item, dict):
        raise HTTPException(status_code=400, detail="Brak poprawnego payload item")
    result = price_service_item(payload.item)
    return {
        "status": "ok",
        "schema_version": SERVICE_PRICING_PAYLOAD_SCHEMA_VERSION,
        "result": result,
    }


@app.get("/orders")
def get_orders(project_id: int | None = None, include_deleted: bool = False):
    return data_manager.get_orders(project_id=project_id, include_deleted=include_deleted)


@app.post("/orders")
def create_order(order: OrderCreate):
    client_name = str(order.client_name or "").strip()
    title = str(order.title or "").strip()
    if not client_name:
        raise HTTPException(status_code=400, detail="Brak nazwy kontrahenta")
    if not title:
        raise HTTPException(status_code=400, detail="Brak tytułu projektu")
    deadline_from = str(order.deadline_from or "").strip()
    deadline_to = str(order.deadline_to or "").strip()
    deadline_legacy = str(order.deadline or "").strip()
    if deadline_from and deadline_to and deadline_from > deadline_to:
        raise HTTPException(status_code=400, detail="Termin od nie moze byc pozniej niz termin do")
    if not deadline_legacy:
        deadline_legacy = deadline_to or deadline_from
    spec_payload: Dict[str, Any] = {}
    try:
        parsed_spec = json.loads(str(order.spec_json or "{}"))
        if isinstance(parsed_spec, dict):
            spec_payload = parsed_spec
    except Exception:
        spec_payload = {}
    spec_payload = _apply_service_pricing_to_spec(spec_payload)
    safe_spec_json = json.dumps(spec_payload, ensure_ascii=False)

    order_id = data_manager.create_order(
        project_id=order.project_id,
        client_name=client_name,
        title=title,
        deadline=deadline_legacy,
        deadline_from=deadline_from,
        deadline_to=deadline_to,
        budget=order.budget,
        status=order.status,
        spec_json=safe_spec_json
    )
    return {"status": "success", "id": order_id}


# --- TECHNICIANS (user selection screen) ---

# --- TECHNICIANS (user selection screen) ---

class TechnicianLogin(BaseModel):
    name: str
    pin: str = ""

@app.get("/technicians")
def get_technicians():
    return data_manager.get_technicians()

@app.post("/api/auth/login")
def login_web(body: TechnicianLogin, response: Response):
    user = data_manager.authenticate_user(body.name, body.pin)
    if user is None:
        raise HTTPException(status_code=401, detail="Nieprawidłowe dane logowania")
        
    token = data_manager.create_session(user["id"])
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=False, # Set True in HTTPS production
        samesite="lax",
        max_age=7 * 24 * 3600
    )
    data_manager.log_action(user["name"], "LOGIN_SUCCESS", details="Web login")
    return {"status": "ok", "user": user}

@app.post("/api/auth/logout")
def logout_web(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        data_manager.logout_user(token)
        user = data_manager.get_user_by_token(token)
        if user:
            data_manager.log_action(user["name"], "LOGOUT", details="Web logout")
    response.delete_cookie("session_token")
    return {"status": "ok"}

@app.get("/api/auth/me")
def get_me(user: CurrentUser = Depends(get_current_user_info)):
    return {
        "id": int(user.user_id) if user.user_id else 0,
        "name": user.name,
        "role": user.role
    }

# --- ADMIN USER MANAGEMENT ---

@app.get("/api/admin/users")
def admin_get_users(user: CurrentUser = Depends(get_current_user_info)):
    require_permission(user, Action.CONFIG_MANAGE) # Admin/Manager only
    return {"status": "ok", "users": data_manager.get_technicians()}

class AdminCreateUserRequest(BaseModel):
    name: str
    role: str
    password: str

@app.post("/api/admin/users")
def admin_create_user(body: AdminCreateUserRequest, user: CurrentUser = Depends(get_current_user_info)):
    require_permission(user, Action.CONFIG_MANAGE)
    try:
        uid = data_manager.admin_create_user(body.name, body.role, body.password)
        data_manager.log_action(user.name, "USER_CREATED", details=f"Created user {body.name} with role {body.role}")
        return {"status": "ok", "id": uid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=_error_detail(str(e)))

class AdminUpdateUserRequest(BaseModel):
    role: str | None = None
    is_active: int | None = None
    password: str | None = None

@app.patch("/api/admin/users/{user_id}")
def admin_update_user(user_id: int, body: AdminUpdateUserRequest, user: CurrentUser = Depends(get_current_user_info)):
    require_permission(user, Action.CONFIG_MANAGE)
    updates = {}
    if body.role is not None: updates["role"] = body.role
    if body.is_active is not None: updates["is_active"] = body.is_active
    if body.password is not None: updates["password"] = body.password
    
    if updates:
        success = data_manager.admin_update_user(user_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
        data_manager.log_action(user.name, "USER_UPDATED", details=f"Updated user {user_id} fields: {list(updates.keys())}")
    return {"status": "ok"}

# --- KIOSK / RCP ENDPOINTS ---

class KioskScanRequest(BaseModel):
    qr_text: str = ""
    identifier: str = ""

class KioskActionRequest(BaseModel):
    worker_id: str
    worker_name: str = ""
    action: str
    work_type: str = ""
    project_code: str = ""
    order_id: str = ""
    workstation: str = ""
    note: str = ""

@app.get("/api/kiosk/workers")
async def get_kiosk_workers():
    return {"ok": True, "workers": kiosk_service.list_workers()}

@app.post("/api/kiosk/workers")
async def save_kiosk_worker(worker: Dict[str, Any]):
    from src.domain.worker_models import WorkerDef
    from src.storage.worker_store_json import WorkerStoreJson
    store = WorkerStoreJson()
    w = WorkerDef.from_dict(worker)
    res = store.overwrite(w)
    return {"ok": res.ok, "message": res.message_pl}

@app.get("/api/kiosk/state")
async def get_kiosk_state(worker_id: str):
    state = kiosk_service.get_state(worker_id)
    return state.to_dict()

@app.post("/api/kiosk/scan")
async def kiosk_scan(req: KioskScanRequest):
    identifier = req.qr_text or req.identifier
    result = kiosk_service.resolve_scan(identifier)
    return result.to_dict()

@app.post("/api/kiosk/action")
async def kiosk_action(req: KioskActionRequest):
    result = kiosk_service.perform_action(
        worker_id=req.worker_id,
        action=req.action,
        work_type=req.work_type,
        project_code=req.project_code,
        order_id=req.order_id,
        workstation=req.workstation,
        note=req.note,
    )
    return result.to_dict()

@app.get("/api/work_time")
async def get_work_time():
    # Return all sheets as a list
    sheets = work_time_store.list_sheets()
    return {"data": [s.to_dict() for s in sheets]}

@app.post("/api/work_time")
async def save_work_time(sheet: Dict[str, Any]):
    # Note: We use Dict[str, Any] since the sheet structure is complex
    work_time_store.save_sheet_dict(sheet)
    return {"status": "success"}

@app.get("/api/finance/fixed-expenses")
async def get_fixed_company_expenses():
    expenses_store = CompanyExpensesStoreJson()
    defaults = ["Wynajem", "Leasingi", "OC / AC", "BHP", "Badania", "Internet", "Inne"]
    fixed_items = expenses_store.list_items("fixed", defaults)
    from src.storage.worker_store_json import WorkerStoreJson
    worker_store = WorkerStoreJson()
    workers_fallback = 1
    try:
        workers_fallback = max(1, len(worker_store.list_workers()))
    except Exception:
        workers_fallback = 1
    metrics = expenses_store.real_hour_metrics(
        workers_fallback=workers_fallback,
        hours_fallback=160.0,
    )
    return {
        "fixed": fixed_items,
        "variable_total": round(float(metrics.get("variable_total", 0.0) or 0.0), 2),
        "workers_count": int(expenses_store.get_workers_count(fallback=workers_fallback)),
        "hours_per_worker": float(expenses_store.get_hours_per_worker(fallback=160.0)),
        "metrics": {
            "fixed_total": round(float(metrics.get("fixed_total", 0.0) or 0.0), 2),
            "variable_total": round(float(metrics.get("variable_total", 0.0) or 0.0), 2),
            "total_costs": round(float(metrics.get("total_costs", 0.0) or 0.0), 2),
            "total_hours": round(float(metrics.get("total_hours", 0.0) or 0.0), 2),
            "real_hour_rate": round(float(metrics.get("real_hour_rate", 0.0) or 0.0), 2),
        },
    }


@app.put("/api/finance/fixed-expenses")
async def update_fixed_company_expenses(payload: CompanyExpensesUpdatePayload):
    expenses_store = CompanyExpensesStoreJson()
    normalized_items = [
        {
            "expense_id": str(item.expense_id or "").strip(),
            "name": str(item.name or "").strip(),
            "amount": float(item.amount or 0.0),
            "account_type": str(item.account_type or "bank").strip().lower() or "bank",
            "source_type": str(item.source_type or "bank_faktura").strip().lower() or "bank_faktura",
        }
        for item in payload.fixed
        if str(item.name or "").strip()
    ]
    expenses_store.save_items("fixed", normalized_items)
    expenses_store.save_workforce(payload.workers_count, payload.hours_per_worker)
    return await get_fixed_company_expenses()


@app.get("/api/finance/system-summary")
async def get_global_finance_summary():
    """
    Returns a global financial overview:
    - Income vs Costs
    - Employee time and estimated pay
    - Material stock value
    - VAT and tax reconciliation
    - Cash in register
    """
    import sqlite3
    from datetime import datetime

    tax_summary = data_manager.get_tax_summary()

    from src.storage.work_time_store_json import WorkTimeStoreJson
    from src.storage.worker_store_json import WorkerStoreJson

    work_store = WorkTimeStoreJson()
    worker_store = WorkerStoreJson()

    all_sheets = work_store.list_sheets()
    workers = worker_store.list_workers()
    workers_map = {str(w.name or "").strip(): w for w in workers}

    def build_filtered_sheets(allowed_types: set[str]) -> list[SimpleNamespace]:
        filtered: list[SimpleNamespace] = []
        for sheet in all_sheets:
            entries = [
                entry
                for entry in getattr(sheet, "entries", [])
                if _normalize_work_type_token(getattr(entry, "work_type", "")) in allowed_types
            ]
            if not entries:
                continue
            filtered.append(
                SimpleNamespace(
                    worker_name=getattr(sheet, "worker_name", ""),
                    year=getattr(sheet, "year", 0),
                    month=getattr(sheet, "month", 0),
                    entries=entries,
                )
            )
        return filtered

    employee_breakdown = compute_work_time_cost(all_sheets, workers_map)
    production_breakdown = compute_work_time_cost(
        build_filtered_sheets({"produkcja", "cnc", "oklejanie", "lakiernia"}),
        workers_map,
    )
    service_breakdown = compute_work_time_cost(
        build_filtered_sheets(
            {
                "montaz",
                "praca na miejscu",
                "serwis",
                "service",
                "pomiar",
                "transport",
                "spotkanie",
                "meeting",
                "delegacja / wyjazd",
                "delegacja/wyjazd",
            }
        ),
        workers_map,
    )
    lacquer_breakdown = compute_work_time_cost(
        build_filtered_sheets({"lakiernia"}),
        workers_map,
    )

    total_hours = float(employee_breakdown.total_hours or 0.0)
    total_employee_cost = float(employee_breakdown.total_cost or 0.0)

    workers_total = len(workers)
    workers_with_rate = sum(
        1
        for worker in workers
        if float(getattr(worker, "hourly_rate", 0.0) or 0.0) > 0.0
        or float(getattr(worker, "daily_rate", 0.0) or 0.0) > 0.0
    )
    workers_missing_rate = max(0, workers_total - workers_with_rate)
    payroll_confidence = "READY" if workers_total > 0 and workers_missing_rate == 0 else "PARTIAL"

    expenses_store = CompanyExpensesStoreJson()
    expense_metrics = expenses_store.real_hour_metrics(
        workers_fallback=max(1, workers_total or 1),
        hours_fallback=160.0,
    )
    fixed_overhead_monthly = round(float(expense_metrics.get("fixed_total", 0.0) or 0.0), 2)
    variable_overhead_monthly = round(float(expense_metrics.get("variable_total", 0.0) or 0.0), 2)
    overhead_hour_cost = round(float(expense_metrics.get("real_hour_rate", 0.0) or 0.0), 2)

    cost_notes: list[str] = []
    if total_hours <= 0:
        cost_notes.append("Brak zarejestrowanych godzin pracy - koszt godzinowy jest niepelny.")
    if workers_missing_rate > 0:
        cost_notes.append(
            f"{workers_missing_rate} pracownik(ow) nie ma ustawionej stawki godzinowej lub dniowki."
        )
    if fixed_overhead_monthly > 0:
        cost_notes.append(
            f"Koszt staly firmy doliczony do godziny: {fixed_overhead_monthly:.2f} zl / miesiac."
        )
    if not cost_notes:
        cost_notes.append("Koszty godzinowe sa liczone na podstawie realnych kart czasu i stawek pracownikow.")

    # 3. Materials / Inventory Value
    # Attempt to load from JSON stock file if it exists, otherwise use SQLite counts
    inventory_value = 0.0
    try:
        from src.services.material_transactions import MaterialTransactionService
        m_service = MaterialTransactionService()
        stocks = m_service.get_all_stock()
        materials = data_manager.get_materials()
        for m in materials:
            q = float(stocks.get(str(m["id"]), stocks.get(m["name"], 0.0)))
            inventory_value += q * float(m["price"])
    except:
        pass

    # 4. Cash in Register (from payments table)
    cash_in_hand = 0.0
    total_orders = 0
    try:
        with sqlite3.connect(data_manager.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT SUM(amount) FROM payments WHERE payment_method = 'gotowka'")
            cash_in_hand = float(c.fetchone()[0] or 0.0)
            c.execute("SELECT COUNT(*) FROM orders")
            total_orders = int(c.fetchone()[0] or 0)
    except:
        pass

    try:
        active_worker_sessions = kiosk_service.list_workers()
    except Exception:
        active_worker_sessions = []

    try:
        active_projects = len(data_manager.get_all_projects())
    except Exception:
        active_projects = 0

    direct_employee_hour_cost = _safe_hour_cost(employee_breakdown)
    direct_production_hour_cost = _safe_hour_cost(production_breakdown)
    direct_service_hour_cost = _safe_hour_cost(service_breakdown)
    direct_lacquer_hour_cost = _safe_hour_cost(lacquer_breakdown)

    def with_overhead(direct: float | None) -> float | None:
        if direct is None and overhead_hour_cost <= 0:
            return None
        return round(float(direct or 0.0) + float(overhead_hour_cost or 0.0), 2)

    employee_hour_cost = with_overhead(direct_employee_hour_cost)
    production_hour_cost = with_overhead(direct_production_hour_cost)
    service_hour_cost = with_overhead(direct_service_hour_cost)
    lacquer_hour_cost = with_overhead(direct_lacquer_hour_cost)

    return {
        "finance": {
            "total_sales_net": tax_summary.get("sales_net", 0),
            "total_costs_net": tax_summary.get("costs_net", 0),
            "gross_profit": tax_summary.get("gross_profit", 0),
            "cash_in_hand": cash_in_hand
        },
        "tax": {
            "sales_net": tax_summary.get("sales_net", 0),
            "vat_collected": tax_summary.get("vat_collected", 0),
            "costs_net": tax_summary.get("costs_net", 0),
            "vat_paid": tax_summary.get("vat_paid", 0),
            "costs_gross": tax_summary.get("costs_gross", 0),
            "tax_balance": tax_summary.get("tax_balance", 0),
            "recommendation": tax_summary.get("recommendation", "Brak danych")
        },
        "hr": {
            "total_hours": round(total_hours, 2),
            "estimated_payroll_net": round(total_employee_cost, 2),
            "active_workers": len(active_worker_sessions),
            "average_hour_cost": employee_hour_cost,
            "direct_hour_cost": direct_employee_hour_cost,
            "workers_total": workers_total,
            "workers_with_rate": workers_with_rate,
            "workers_missing_rate": workers_missing_rate,
            "payroll_confidence": payroll_confidence,
        },
        "inventory": {
            "total_value": inventory_value,
            "materials_types": len(data_manager.get_materials())
        },
        "cost_insights": {
            "employee_hour_cost": employee_hour_cost,
            "production_hour_cost": production_hour_cost,
            "service_hour_cost": service_hour_cost,
            "lacquer_hour_cost": lacquer_hour_cost,
            "direct_employee_hour_cost": direct_employee_hour_cost,
            "direct_production_hour_cost": direct_production_hour_cost,
            "direct_service_hour_cost": direct_service_hour_cost,
            "direct_lacquer_hour_cost": direct_lacquer_hour_cost,
            "fixed_overhead_monthly": fixed_overhead_monthly,
            "variable_overhead_monthly": variable_overhead_monthly,
            "overhead_hour_cost": overhead_hour_cost,
            "confidence": payroll_confidence,
            "notes": cost_notes,
        },
        "production": {
            "total_modules": 0,
            "total_orders": total_orders,
            "active_projects": active_projects
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/production/status")
async def get_production_status():
    """
    Aggregates real-time production data:
    - Workstation loads from open route tasks
    - Active worker sessions
    - Recent activity log
    """
    from src.core.operations_store import OperationsStore
    store = OperationsStore()
    
    # 1. Fetch all routes (tasks)
    all_routes = store.list_routes()
    active_worker_sessions = kiosk_service.list_workers()
    
    # 2. Map tasks to workstations
    stations = {
        "CNC": {"id": "CNC", "name": "CNC - Wycinanie", "position": "Hala A", "status": "IDLE", "workers": [], "progress": 0, "active_job": None},
        "Oklejanie": {"id": "Oklejanie", "name": "Oklejarka", "position": "Hala A", "status": "IDLE", "workers": [], "progress": 0, "active_job": None},
        "Lakiernia": {"id": "Lakiernia", "name": "Lakiernia", "position": "Hala B", "status": "IDLE", "workers": [], "progress": 0, "active_job": None},
        "Montaż": {"id": "Montaż", "name": "Montaż Końcowy", "position": "Hala B", "status": "IDLE", "workers": [], "progress": 0, "active_job": None},
    }
    station_routes: dict[str, list[Any]] = {key: [] for key in stations.keys()}
    station_task_types = {
        "CNC": {"cnc", "produkcja", "blokada_produkcji"},
        "Oklejanie": {"oklejanie"},
        "Lakiernia": {"lakiernia", "lakierowanie"},
        "Montaż": {"montaz", "montaż", "skladanie", "zbiorka", "zborka", "poprawki", "blokada_montazu"},
    }
    
    for route in all_routes:
        if str(route.status or "").strip().lower() not in {"anulowane"}:
            # Simple mapping by task_type or route_group
            # If route.task_type is 'CNC', map to CNC station
            rtype = str(route.task_type or "").strip().lower()
            station_key = next((key for key, allowed in station_task_types.items() if rtype in allowed), "")
            if station_key:
                st = stations[station_key]
                station_routes[station_key].append(route)
                if route.status == "w_trakcie" and not st["active_job"]:
                    st["status"] = "BUSY"
                    st["active_job"] = {"title": f"{route.project_name} - {route.client_name}"}
                    st["workers"] = [route.crew] if route.crew else []
    
    # Cross-reference with active worker sessions
    for w in active_worker_sessions:
        if w.get("active"):
            wtype = w.get("session", {}).get("work_type", "")
            if wtype in stations:
                stations[wtype]["workers"].append(w["name"])
                stations[wtype]["status"] = "BUSY"

    # Transparent progress formula based on real task states only:
    # progress = round(((done + 0.5 * in_progress) / total) * 100), with total>=1.
    for station_key, st in stations.items():
        routes = station_routes.get(station_key, [])
        total = len(routes)
        if total <= 0:
            st["progress"] = 0
            continue
        done = sum(1 for r in routes if str(getattr(r, "status", "") or "").strip().lower() in {"zakończone", "wykonane"})
        in_progress = sum(1 for r in routes if str(getattr(r, "status", "") or "").strip().lower() == "w_trakcie")
        progress = round(((done + (0.5 * in_progress)) / float(total)) * 100)
        st["progress"] = max(0, min(100, int(progress)))

    # 3. Stats
    stats = {
        "active_orders": len(set(r.project_name for r in all_routes if r.status != "zakończone")),
        "online_workers": sum(1 for w in active_worker_sessions if w.get("active")),
        "pending_tasks": sum(1 for r in all_routes if r.status == "planowane"),
        "finished_today": sum(1 for r in all_routes if r.status == "zakończone" and r.updated_at.startswith(date.today().isoformat())),
        "critical_issues": len(store.filter_issues(priority="krytyczny", active_only=True))
    }

    # 4. Activity Log (last 5)
    log = []
    sorted_by_update = sorted(all_routes, key=lambda x: x.updated_at, reverse=True)[:5]
    for r in sorted_by_update:
        log.append({
            "time": r.updated_at.split("T")[-1][:5],
            "worker": r.crew or "System",
            "action": f"zmienił status na {r.status}",
            "order": r.project_name
        })

    return {
        "workstations": list(stations.values()),
        "stats": stats,
        "activity_log": log
    }

@app.get("/api/production/tasks")
async def get_production_tasks(station: str = "", status: str = "active", limit: int = 200):
    """
    Returns production route tasks for a specific station (e.g. CNC).
    """
    from src.core.operations_store import OperationsStore
    store = OperationsStore()

    station_norm = str(station or "").strip().lower()
    status_norm = str(status or "active").strip().lower()
    safe_limit = _normalize_limit(limit, default=200, max_value=1000)

    station_task_types = {
        "cnc": {"cnc", "produkcja", "blokada_produkcji", "inne"},
        "oklejanie": {"oklejanie"},
        "lakiernia": {"lakiernia", "lakierowanie"},
        "montaz": {"montaz", "skladanie", "zbiorka", "zborka", "poprawki", "blokada_montazu"},
        "biuro": {"biuro", "projekt", "wycena", "zakup materialow", "probki"},
    }

    rows = store.list_routes()
    if station_norm in station_task_types:
        allowed = station_task_types.get(station_norm, set())
        rows = [r for r in rows if str(r.task_type or "").strip().lower() in allowed]
    elif station_norm:
        rows = [r for r in rows if str(r.task_type or "").strip().lower() == station_norm]

    if status_norm == "active":
        rows = [r for r in rows if str(r.status or "").strip().lower() in {"planowane", "w_trakcie"}]
    elif status_norm == "done":
        rows = [r for r in rows if str(r.status or "").strip().lower() in {"wykonane", "zakończone"}]

    payload = [r.to_dict() for r in rows[:safe_limit]]
    return {"status": "ok", "station": station_norm, "items": payload, "total": len(rows), "limit": safe_limit}

@app.post("/api/production/task-action")
async def production_task_action(req: Dict[str, Any]):
    """
    Allows a worker to toggle a task status (Start/Finish).
    """
    from src.core.operations_store import OperationsStore
    from src.core.operations_models import IssueRecord
    store = OperationsStore()
    
    task_id = req.get("task_id")
    worker_id = str(req.get("worker_id", "") or "").strip()
    worker_name = str(req.get("worker_name", "") or "").strip()
    action = req.get("action") # "start" or "finish"
    note = str(req.get("note", "") or "").strip()
    correction_note = str(req.get("correction_note", "") or "").strip()
    if not worker_id:
        raise HTTPException(status_code=400, detail="worker_id jest wymagany")
    actor_label = worker_id if not worker_name else f"{worker_id} ({worker_name})"
    
    task = store.get_route_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Nie znaleziono zadania")
    
    if action == "start":
        task.status = "w_trakcie"
        task.crew = worker_id
    elif action == "finish":
        task.status = "zakończone"
        if not str(task.crew or "").strip():
            task.crew = worker_id
    else:
        raise HTTPException(status_code=400, detail="Nieobsługiwana akcja. Użyj: start | finish")

    log_line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {actor_label}: {action}"
    if note:
        log_line += f" | note: {note}"
    task.notes = (str(task.notes or "").strip() + "\n" + log_line).strip()

    created_issue_id = ""
    if correction_note:
        issue = IssueRecord(
            title=f"Poprawka CNC: {task.project_name or task.client_name or task.id}",
            description=correction_note,
            area="produkcja",
            issue_type="blad_wymiaru",
            impact_level="sredni",
            priority_manual="normalny",
            status="nowe",
            project_name=str(task.project_name or "").strip(),
            client_name=str(task.client_name or "").strip(),
            order_id=str(task.issue_id or "").strip(),
            owner=actor_label,
            blocks_production=False,
            notes=f"Auto-zgłoszenie z terminala CNC (task: {task.id})",
            tags=["cnc", "poprawka"],
        )
        saved_issue = store.add_issue(issue)
        created_issue_id = str(saved_issue.id or "").strip()
    
    updated = store.update_route_task(task)
    return {
        "status": "success",
        "task": updated.to_dict(),
        "created_issue_id": created_issue_id,
        "actor": {"worker_id": worker_id, "worker_name": worker_name},
    }

@app.get("/api/ai/predictions")
async def get_ai_predictions():
    """
    AI Predictive Engine: Forecasts future states based on current production velocity.
    """
    from src.core.operations_store import OperationsStore
    store = OperationsStore()
    
    all_routes = store.list_routes()
    active_tasks = [r for r in all_routes if r.status == "w_trakcie"]
    pending_tasks = [r for r in all_routes if r.status == "planowane"]
    
    predictions = []
    
    # 1. Delay Forecasting
    # If tasks are starting later than planned_date or taking too long
    for task in active_tasks:
        # Simplified: If task was updated today but planned for yesterday -> Cascade Delay
        if task.planned_date < date.today().isoformat():
            predictions.append({
                "type": "delay",
                "severity": "high",
                "title": f"Ryzyko opóźnienia: {task.project_name}",
                "content": f"Zadanie {task.task_type} wystartowało z opóźnieniem. Przewidywane przesunięcie montażu końcowego o ~24h.",
                "confidence": 0.85
            })
            
    # 2. Resource Load Prediction (Bottlenecks)
    # Count planned tasks per type for the next 3 days
    load_map = {}
    for task in pending_tasks:
        load_map[task.task_type] = load_map.get(task.task_type, 0) + 1
        
    for station, count in load_map.items():
        if count > 5: # Threshold for overload
            predictions.append({
                "type": "bottleneck",
                "severity": "medium",
                "title": f"Przeciążenie: {station}",
                "content": f"W ciągu najbliższych 72h na stanowisko {station} trafi {count} nowych zadań. Sugerowane nadgodziny lub wsparcie z innych działów.",
                "confidence": 0.70
            })
            
    # 3. Cost Variance Prediction
    # Compare actual vs estimated from finished tasks
    predictions.append({
        "type": "finance",
        "severity": "info",
        "title": "Analiza marży live",
        "content": "Aktualne koszty materiałowe są o 4.2% wyższe od założeń. Marża projektu 'Kuchnia Industrialna' spadła do 22%.",
        "confidence": 0.95
    })

    return {"predictions": predictions}

@app.get("/api/ai/advisor")
async def get_ai_advisor_tips():
    """
    AI Business Advisor: Analyzes system state and provides strategic tips.
    """
    from src.core.operations_store import OperationsStore
    store = OperationsStore()
    
    all_routes = store.list_routes()
    issues = store.filter_issues(active_only=True)
    tips = []
    
    # Logic 1: Bottleneck analysis
    overdue_count = sum(1 for r in all_routes if r.status != "zakończone" and r.planned_date < date.today().isoformat())
    if overdue_count > 3:
        tips.append({
            "type": "warning",
            "title": "Wąskie gardło na montażu",
            "content": f"Masz {overdue_count} projekty po terminie. Sugeruję wstrzymanie nowych wycen i skupienie się na domykaniu bieżących montaży, aby odblokować płatności.",
            "impact": "High"
        })
        
    # Logic 2: Revenue Unlock
    total_unlock = sum(i.estimated_revenue_unlock for i in issues)
    if total_unlock > 50000:
        top_issue = sorted(issues, key=lambda x: x.estimated_revenue_unlock, reverse=True)[0]
        tips.append({
            "type": "opportunity",
            "title": "Szybka gotówka do odzyskania",
            "content": f"Rozwiązanie problemu '{top_issue.title}' w projekcie {top_issue.project_name} pozwoli Ci wystawić fakturę na {top_issue.estimated_revenue_unlock} PLN jeszcze w tym tygodniu.",
            "impact": "Financial"
        })

    # Logic 3: Material optimization
    missing_mat = [i for i in issues if i.issue_type == "brak_materialu"]
    if missing_mat:
        tips.append({
            "type": "info",
            "title": "Braki magazynowe",
            "content": f"Brakuje materiałów do {len(missing_mat)} projektów. Zamów je zbiorczo dzisiaj, aby uniknąć kosztów dodatkowego transportu.",
            "impact": "Costs"
        })

    return {"tips": tips}

@app.post("/api/dev/seed")
async def seed_test_data():
    """
    Seeds the system with 5 professional sample orders and production data.
    """
    from src.core.operations_store import OperationsStore
    from src.core.operations_models import IssueRecord, RouteTaskRecord
    store = OperationsStore()
    
    # 1. Clear existing (optional, but good for clean sim)
    # store.clear_all() 
    
    # 2. Sample Projects
    projects = [
        ("Apartament Morski", "Waldemar K.", 45000),
        ("Klinika Dentystyczna", "Dr Ząbek", 85000),
        ("Szafa Przedpokój", "Anna Nowak", 12500),
        ("Kuchnia Industrialna", "Piotr R.", 110000),
        ("Biuro Architektów", "Arch-Studio", 25000),
    ]
    
    for title, client, value in projects:
        # Create a blocking issue (Material Shortage)
        issue = IssueRecord(
            title=f"Brak płyt: {title}",
            description=f"Oczekiwanie na płyty frontowe do zlecenia {title}.",
            project_name=title,
            client_name=client,
            issue_type="brak_materialu",
            estimated_revenue_unlock=value,
            quantity_required=10,
            estimated_cost=2500
        )
        store.add_issue(issue)
        
        # Create Production Routes
        tasks = ["CNC", "Lakiernia", "Montaż"]
        for t in tasks:
            route = RouteTaskRecord(
                project_name=title,
                client_name=client,
                task_type=t,
                status="planowane" if t != "CNC" else "w_trakcie",
                planned_date=date.today().isoformat()
            )
            store.add_route_task(route)
            
    return {"status": "success", "message": "Zasiano 5 przykładowych projektów."}
 
@app.get("/api/production/project/{project_id}/diagnostics")
def get_project_production_diagnostics(project_id: int):
    """Zwraca dane diagnostyczne dla produkcji (debug)."""
    return production_service.get_project_production_summary(project_id)

@app.post("/api/production/project/{project_id}/auto-layout")
def auto_layout_project(project_id: int, wall_width: float = 3000):
    """
    Automatyczny układ (Snap-to-Wall): ustawia moduły jeden obok drugiego
    wzdłuż osi X, sprawdzając czy mieszczą się na zadanej szerokości ściany.
    """
    modules = data_manager.get_project_modules(project_id)
    current_x = 0
    updates = []
    
    for mod in modules:
        mod_w = mod.get("width", 600)
        # Update X position in database or memory
        # Here we simulate updating the 'x' property in the database
        data_manager.update_module_property(mod["id"], "x", current_x)
        updates.append({"id": mod["id"], "name": mod["name"], "x": current_x})
        current_x += mod_w + 2 # 2mm gap
        
    return {"status": "success", "total_width": current_x, "updates": updates}

@app.get("/api/issues")
async def get_all_issues():
    """
    Returns all issues with scores and impact for the Business Optimizer.
    """
    from src.core.operations_store import OperationsStore
    store = OperationsStore()
    all_issues = store.list_issues()
    
    candidates = []
    for iss in all_issues:
        # Simple scoring logic
        score = 50
        if iss.issue_type == "brak_materialu": score += 20
        if iss.estimated_revenue_unlock > 50000: score += 20
        
        candidates.append({
            "issue": iss.to_dict(),
            "score": score,
            "impact": "High" if score > 70 else "Medium"
        })
        
    return candidates


def _sync_low_stock_alarms() -> None:
    """
    Synchronizuje alarmy magazynowe na podstawie aktualnych niskich stanów.
    - Tworzy/aktualizuje alarmy dla pozycji <= min_stock.
    - Automatycznie zamyka alarm gdy stan wraca powyżej minimum.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    low_stock_items = data_manager.get_low_stock_materials(limit=2000)
    current = alarm_store.list_alarms()
    existing_by_id = {a.alarm_id: a for a in current}
    active_alarm_ids: set[str] = set()
    to_save: list[AlarmDef] = []

    for item in low_stock_items:
        material_id = int(item.get("id") or 0)
        if material_id <= 0:
            continue
        alarm_id = f"LOW_STOCK_{material_id}"
        active_alarm_ids.add(alarm_id)

        stock_qty = float(item.get("stock_quantity") or 0.0)
        min_stock = float(item.get("min_stock") or 0.0)
        missing_qty = float(item.get("missing_qty") or 0.0)
        unit = str(item.get("unit") or "m2")
        name = str(item.get("name") or "").strip() or f"Material #{material_id}"

        severity = "krytyczny" if stock_qty <= 0.0 else "ostrzezenie"
        title = f"Niski stan magazynowy: {name}"
        description = (
            f"Stan {stock_qty:.2f} {unit} jest poniżej minimum {min_stock:.2f} {unit}. "
            f"Brakuje {missing_qty:.2f} {unit}."
        )

        existing = existing_by_id.get(alarm_id)
        if existing is None:
            alarm = AlarmDef(
                alarm_id=alarm_id,
                category="materialy",
                severity=severity,
                title=title,
                description=description,
                related_material=name,
                created_at=now_str,
                is_resolved=False,
                resolved_at="",
                extra={
                    "source": "low_stock_auto",
                    "material_id": material_id,
                    "stock_quantity": stock_qty,
                    "min_stock": min_stock,
                    "missing_qty": missing_qty,
                    "unit": unit,
                },
            )
            to_save.append(alarm)
            continue

        existing.category = "materialy"
        existing.severity = severity
        existing.title = title
        existing.description = description
        existing.related_material = name
        existing.is_resolved = False
        existing.resolved_at = ""
        if not str(existing.created_at or "").strip():
            existing.created_at = now_str
        extra = dict(existing.extra or {})
        extra.update(
            {
                "source": "low_stock_auto",
                "material_id": material_id,
                "stock_quantity": stock_qty,
                "min_stock": min_stock,
                "missing_qty": missing_qty,
                "unit": unit,
            }
        )
        existing.extra = extra
        to_save.append(existing)

    # Auto-close outdated low-stock alarms when state recovered.
    for alarm in current:
        src = str((alarm.extra or {}).get("source", "") or "").strip()
        if src != "low_stock_auto":
            continue
        if alarm.alarm_id in active_alarm_ids:
            continue
        if not bool(alarm.is_resolved):
            alarm_store.resolve_alarm(alarm.alarm_id)

    if to_save:
        alarm_store.save_alarms_batch(to_save)


@app.get("/api/alarms")
async def get_alarms(include_resolved: bool = False, limit: int = 200):
    _sync_low_stock_alarms()
    alarms = [a.to_dict() for a in alarm_store.list_alarms()]
    if not include_resolved:
        alarms = [a for a in alarms if not bool(a.get("is_resolved"))]
    alarms.sort(key=lambda a: str(a.get("created_at", "") or ""), reverse=True)
    safe_limit = _normalize_limit(limit, default=200, max_value=1000)
    return {"status": "ok", "items": alarms[:safe_limit], "total": len(alarms), "limit": safe_limit}


@app.patch("/api/alarms/{alarm_id}/ack")
async def acknowledge_alarm(alarm_id: str, payload: AlarmAckPayload):
    alarm_id_norm = str(alarm_id or "").strip()
    if not alarm_id_norm:
        raise HTTPException(status_code=400, detail=_error_detail("alarm_id jest wymagane"))
    alarms = alarm_store.list_alarms()
    target = next((a for a in alarms if a.alarm_id == alarm_id_norm), None)
    if target is None:
        raise HTTPException(status_code=404, detail=_error_detail("Nie znaleziono alarmu"))

    extra = dict(target.extra or {})
    extra["acknowledged"] = bool(payload.acknowledged)
    extra["ack_note"] = str(payload.note or "").strip()
    extra["ack_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target.extra = extra
    alarm_store.save_alarm(target)
    return {"status": "ok", "alarm": target.to_dict()}


@app.patch("/api/alarms/{alarm_id}/resolve")
async def resolve_alarm(alarm_id: str):
    alarm_id_norm = str(alarm_id or "").strip()
    if not alarm_id_norm:
        raise HTTPException(status_code=400, detail=_error_detail("alarm_id jest wymagane"))
    alarms = alarm_store.list_alarms()
    if not any(a.alarm_id == alarm_id_norm for a in alarms):
        raise HTTPException(status_code=404, detail=_error_detail("Nie znaleziono alarmu"))
    alarm_store.resolve_alarm(alarm_id_norm)
    return {"status": "ok", "alarm_id": alarm_id_norm}


@app.get("/api/operations/summary")
async def get_operations_summary():
    from src.core.operations_store import OperationsStore

    store = OperationsStore()
    issues = store.list_issues()
    routes = store.list_routes()
    today_iso = date.today().strftime("%Y-%m-%d")

    active_issues = [i for i in issues if i.status != "zamkniete"]
    overdue_issues = [i for i in active_issues if i.is_overdue()]
    critical_issues = [i for i in active_issues if i.priority_manual == "krytyczny"]
    blocked_invoice = [i for i in active_issues if i.blocks_invoice]

    active_routes = [r for r in routes if r.status not in {"wykonane", "anulowane"}]
    overdue_routes = [r for r in active_routes if str(r.planned_date or "") and str(r.planned_date) < today_iso]
    done_routes = [r for r in routes if r.status == "wykonane"]

    return {
        "status": "ok",
        "issues_total": len(issues),
        "issues_active": len(active_issues),
        "issues_overdue": len(overdue_issues),
        "issues_critical": len(critical_issues),
        "issues_blocks_invoice": len(blocked_invoice),
        "routes_total": len(routes),
        "routes_active": len(active_routes),
        "routes_overdue": len(overdue_routes),
        "routes_done": len(done_routes),
        "revenue_unlock_total": round(sum(float(i.estimated_revenue_unlock or 0.0) for i in active_issues), 2),
    }


@app.get("/api/operations/issues")
async def get_operations_issues(status: str = "active", limit: int = 200):
    from src.core.operations_store import OperationsStore

    store = OperationsStore()
    normalized = str(status or "active").strip().lower()
    allowed_filters = {"all", "active", "closed", "nowe", "w_toku", "oczekuje", "zablokowane", "do_decyzji", "zamkniete"}
    if normalized not in allowed_filters:
        raise HTTPException(status_code=400, detail=_error_detail("Nieobsługiwany filtr status"))
    if normalized == "all":
        issues = store.list_issues()
    elif normalized == "closed":
        issues = [i for i in store.list_issues() if i.status == "zamkniete"]
    elif normalized == "active":
        issues = store.filter_issues(active_only=True)
    else:
        issues = store.filter_issues(status=normalized)
    safe_limit = _normalize_limit(limit, default=200, max_value=1000)
    payload = [i.to_dict() for i in issues[:safe_limit]]
    return {"status": "ok", "items": payload, "total": len(issues), "filter": normalized, "limit": safe_limit}


@app.patch("/api/operations/issues/{issue_id}")
async def patch_operations_issue(
    issue_id: str, 
    payload: OperationIssuePatch, 
    user: CurrentUser = Depends(get_current_user_info)
):
    from src.core.operations_store import OperationsStore
    store = OperationsStore()
    issue_id_norm = str(issue_id or "").strip()
    if not issue_id_norm:
        raise HTTPException(status_code=400, detail=_error_detail("issue_id jest wymagane"))
    issue = store.get_issue(issue_id_norm)
    if issue is None:
        raise HTTPException(status_code=404, detail=_error_detail("Nie znaleziono issue"))

    # Permission check: status update vs assign vs general update
    if payload.owner is not None:
        require_permission(user, Action.ISSUE_ASSIGN)
    if payload.status == "zamkniete":
        require_permission(user, Action.ISSUE_RESOLVE)
    
    require_permission(user, Action.ISSUE_UPDATE)

    allowed_statuses = {"nowe", "w_toku", "oczekuje", "zablokowane", "do_decyzji", "zamkniete"}
    allowed_priorities = {"niski", "normalny", "wysoki", "krytyczny"}

    changes = []
    if payload.status is not None:
        next_status = str(payload.status or "").strip().lower()
        if next_status and next_status not in allowed_statuses:
            raise HTTPException(status_code=400, detail=_error_detail("NieobsĹ‚ugiwany status issue"))
        if next_status != issue.status:
            changes.append(f"status: {issue.status} -> {next_status}")
            issue.status = next_status
    if payload.owner is not None:
        if payload.owner != issue.owner:
            changes.append(f"owner: {issue.owner} -> {payload.owner}")
            issue.owner = str(payload.owner or "").strip()
    if payload.priority_manual is not None:
        next_priority = str(payload.priority_manual or "").strip().lower()
        if next_priority and next_priority not in allowed_priorities:
            raise HTTPException(status_code=400, detail=_error_detail("NieobsĹ‚ugiwany priorytet issue"))
        if next_priority != issue.priority_manual:
            changes.append(f"priority: {issue.priority_manual} -> {next_priority}")
            issue.priority_manual = next_priority
    if payload.due_date is not None:
        if payload.due_date != issue.due_date:
            changes.append(f"due_date: {issue.due_date} -> {payload.due_date}")
            issue.due_date = str(payload.due_date or "").strip()
    if payload.notes is not None:
        issue.notes = str(payload.notes or "").strip()

    if changes:
        data_manager.log_action(
            user_name=user.name,
            action="ISSUE_UPDATE",
            target_type="issue",
            target_id=issue_id_norm,
            details=", ".join(changes),
            metadata={"user_role": user.role, "user_id": user.user_id}
        )

    issue.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated = store.update_issue(issue)
    return {"status": "ok", "issue": updated.to_dict()}


@app.post("/api/operations/routes/recommend")
async def recommend_operation_routes(payload: OperationRouteRecommendRequest):
    from src.core.operations_store import OperationsStore

    store = OperationsStore()
    safe_limit = _normalize_limit(payload.limit, default=5, max_value=50)
    planned_date = _validate_iso_date(payload.planned_date or "", field_name="planned_date", required=False)
    candidates = store.list_priority_candidates(status="all")
    out: list[Dict[str, Any]] = []
    for row in candidates:
        issue = row.get("issue")
        if issue is None:
            continue
        if str(issue.status or "").strip().lower() == "zamkniete":
            continue
        out.append(
            {
                "issue_id": issue.id,
                "title": issue.title,
                "project_name": issue.project_name,
                "client_name": issue.client_name,
                "city": issue.city,
                "address": issue.address,
                "owner": issue.owner,
                "score": float(row.get("score", 0.0) or 0.0),
                "quick_close": bool(row.get("quick_close", False)),
                "overdue": bool(row.get("overdue", False)),
                "estimated_time_minutes": int(issue.estimated_time_minutes or 0),
                "estimated_revenue_unlock": float(issue.estimated_revenue_unlock or 0.0),
                "recommended_planned_date": str(planned_date or date.today().strftime("%Y-%m-%d")),
                "recommended_crew": str(payload.crew or issue.owner or "").strip(),
            }
        )
        if len(out) >= safe_limit:
            break
    return {"status": "ok", "items": out, "total": len(out), "limit": safe_limit}

@app.post("/api/telegram/send-briefing")
async def send_telegram_briefing():
    """Wysyła dzienny briefing deweloperski na Telegram."""
    res = TelegramHubService.send_briefing()
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("message"))
    return res


@app.post("/api/telegram/send-low-stock")
async def send_telegram_low_stock(limit: int = 20):
    """Wysyła raport niskich stanów magazynowych na Telegram."""
    safe_limit = _normalize_limit(limit, default=20, max_value=200)
    res = TelegramHubService.send_low_stock_report(limit=safe_limit)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("message"))
    return {"status": "ok", "limit": safe_limit, **res}

# --- ZAKUPY I DOSTAWY (ETAP 4) ---
@app.get("/api/db/arrivals")
async def get_arrivals():
    return data_manager.get_arrivals()

class ArrivalCreate(BaseModel):
    material_id: int
    order_id: int | None = None
    invoice_id: int | None = None
    invoice_line_item_id: int | None = None
    quantity: float
    unit: str
    purchase_type: str
    document_nr: str
    supplier: str = ""
    wholesaler: str = ""
    unit_price_net: float = 0.0
    unit_price_gross: float = 0.0
    price_total: float
    date: str


class ArrivalUpdate(BaseModel):
    material_id: int | None = None
    order_id: int | None = None
    invoice_id: int | None = None
    invoice_line_item_id: int | None = None
    quantity: float | None = None
    unit: str | None = None
    purchase_type: str | None = None
    document_nr: str | None = None
    supplier: str | None = None
    wholesaler: str | None = None
    unit_price_net: float | None = None
    unit_price_gross: float | None = None
    price_total: float | None = None
    date: str | None = None

@app.post("/api/db/arrivals")
async def add_arrival(req: ArrivalCreate):
    ok = data_manager.add_arrival(
        req.material_id,
        req.quantity,
        req.unit,
        req.purchase_type,
        req.document_nr,
        req.price_total,
        req.date,
        req.order_id,
        req.unit_price_net,
        req.unit_price_gross,
        req.supplier,
        req.wholesaler,
        req.invoice_id,
        req.invoice_line_item_id,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Błąd zapisu dostawy")
    return {"status": "success"}

@app.patch("/api/db/arrivals/{arrival_id}")
async def patch_arrival(arrival_id: int, payload: ArrivalUpdate):
    updates = payload.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail=_error_detail("Brak pol do aktualizacji"))
    ok = data_manager.update_arrival(arrival_id=int(arrival_id), updates=updates)
    if not ok:
        raise HTTPException(status_code=404, detail=_error_detail("Nie znaleziono dostawy lub brak zmian"))
    return {"status": "success"}


class OrderStatusUpdate(BaseModel):
    status: str
    worker: str = ""

@app.put("/orders/{order_id}/status")
async def update_order_status(order_id: int, payload: OrderStatusUpdate):
    success = data_manager.update_order_status(order_id, payload.status)
    if not success:
        return {"status": "error", "message": "Nie zaktualizowano statusu."}
    return {"status": "success"}

@app.put("/api/orders/{order_id}/status")
async def update_order_status_api(order_id: int, payload: OrderStatusUpdate):
    return await update_order_status(order_id, payload)


# =====================================================================
# Inventory + Order Cost Write-Off — API Endpoints (Stage 1 + 2)
# =====================================================================

@app.post("/api/inventory/purchase-documents")
async def create_purchase_document(payload: PurchaseDocumentCreate):
    supplier = str(payload.supplier_name or "").strip()
    doc_number = str(payload.document_number or "").strip()
    doc_date = str(payload.document_date or "").strip()
    if not supplier:
        raise HTTPException(status_code=400, detail=_error_detail("supplier_name is required"))
    if not doc_number:
        raise HTTPException(status_code=400, detail=_error_detail("document_number is required"))
    if not doc_date:
        raise HTTPException(status_code=400, detail=_error_detail("document_date is required"))
    _validate_iso_date(doc_date, field_name="document_date", required=True)

    lines = list(payload.lines or [])
    computed_net = 0.0
    computed_gross = 0.0
    line_totals: List[Dict[str, float]] = []
    for line in lines:
        line_net = round(float(line.qty) * float(line.unit_price_net), 2)
        vat_mult = 1.0 + float(line.vat_rate or 23.0) / 100.0
        line_gross = round(line_net * vat_mult, 2)
        line_totals.append({"net": line_net, "gross": line_gross})
        computed_net += line_net
        computed_gross += line_gross

    total_net = float(payload.total_net) if payload.total_net > 0 else computed_net
    total_gross = float(payload.total_gross) if payload.total_gross > 0 else computed_gross

    doc_id = data_manager.create_purchase_document(
        supplier_name=supplier,
        document_number=doc_number,
        document_date=doc_date,
        document_type=str(payload.document_type or "invoice"),
        currency=str(payload.currency or "PLN"),
        total_net=total_net,
        total_gross=total_gross,
        payment_status=str(payload.payment_status or "unpaid"),
        payment_method=str(payload.payment_method or ""),
        note=str(payload.note or ""),
    )

    line_ids = []
    for i, line in enumerate(lines):
        totals = line_totals[i] if i < len(line_totals) else {"net": 0.0, "gross": 0.0}
        lid = data_manager.create_purchase_document_line(
            purchase_document_id=doc_id,
            material_id=line.material_id,
            description_snapshot=str(line.description_snapshot or ""),
            qty=float(line.qty),
            unit=str(line.unit or "pcs"),
            unit_price_net=float(line.unit_price_net),
            vat_rate=float(line.vat_rate),
            line_total_net=totals["net"],
            line_total_gross=totals["gross"],
            is_stock_item=bool(line.is_stock_item),
            order_id=line.order_id,
            note=str(line.note or ""),
        )
        line_ids.append(lid)

    return {"status": "success", "id": doc_id, "line_ids": line_ids}


@app.get("/api/inventory/purchase-documents")
async def list_purchase_documents(limit: int = 200):
    safe_limit = _normalize_limit(limit, default=200, max_value=1000)
    return data_manager.get_purchase_documents(limit=safe_limit)


@app.get("/api/inventory/purchase-documents/{doc_id}")
async def get_purchase_document(doc_id: int):
    doc = data_manager.get_purchase_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=_error_detail(f"Purchase document {doc_id} not found"))
    lines = data_manager.get_purchase_document_lines(doc_id)
    return {"document": doc, "lines": lines}


@app.post("/api/inventory/purchase-documents/{doc_id}/receive")
async def receive_purchase_document(doc_id: int, payload: PurchaseReceiveRequest):
    try:
        result = data_manager.receive_purchase_document(
            doc_id=doc_id,
            payment_method=str(payload.payment_method or ""),
            created_by=str(payload.created_by or ""),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_error_detail(str(e)))


@app.get("/api/inventory/movements")
async def list_inventory_movements(material_id: int | None = None, order_id: int | None = None, limit: int = 500):
    safe_limit = _normalize_limit(limit, default=500, max_value=2000)
    return data_manager.get_inventory_movements(material_id=material_id, order_id=order_id, limit=safe_limit)


@app.get("/api/inventory/balances")
async def list_inventory_balances(limit: int = 500):
    safe_limit = _normalize_limit(limit, default=500, max_value=2000)
    return data_manager.get_inventory_balances(limit=safe_limit)


@app.get("/api/inventory/cash-movements")
async def list_cash_bank_movements(limit: int = 500):
    safe_limit = _normalize_limit(limit, default=500, max_value=2000)
    return data_manager.get_cash_bank_movements(limit=safe_limit)


@app.post("/api/inventory/order-costs")
async def create_order_cost_entry(payload: OrderCostEntryCreate, user: CurrentUser = Depends(get_current_user_info)):
    require_permission(user, Action.FINANCE_EDIT)
    if not payload.order_id or int(payload.order_id) <= 0:
        raise HTTPException(status_code=400, detail=_error_detail("order_id is required"))
    valid_cost_types = {"MATERIAL", "LABOR", "SERVICE", "TRANSPORT", "INSTALLATION", "OTHER_DIRECT"}
    cost_type = str(payload.cost_type or "MATERIAL").strip().upper()
    if cost_type not in valid_cost_types:
        raise HTTPException(status_code=400, detail=_error_detail(f"Invalid cost_type. Allowed: {', '.join(sorted(valid_cost_types))}"))

    entry_id = data_manager.create_order_cost_entry(
        order_id=int(payload.order_id),
        cost_type=cost_type,
        source_type=str(payload.source_type or ""),
        source_id=payload.source_id,
        amount_net=float(payload.amount_net),
        vat_rate=float(payload.vat_rate),
        amount_gross=float(payload.amount_gross),
        qty=payload.qty,
        unit=payload.unit,
        description=str(payload.description or ""),
        note=str(payload.note or ""),
        created_by=str(payload.created_by or ""),
    )
    return {"status": "success", "id": entry_id}


@app.get("/api/inventory/order-costs/{order_id}")
async def get_order_costs(order_id: int):
    entries = data_manager.get_order_cost_entries(order_id)
    summary = data_manager.get_order_cost_summary(order_id)
    return {"entries": entries, "summary": summary}


# =====================================================================
# Inventory Write-Off — Stage 3: Reserve / Issue / Stage 4: Return / Scrap / Correction
# =====================================================================

@app.get("/api/inventory/material-cost/{material_id}")
async def get_material_unit_cost(material_id: int):
    cost = data_manager.get_material_unit_cost(material_id)
    return {"material_id": material_id, "unit_cost_net": cost}


@app.post("/api/inventory/reserve")
async def reserve_material(payload: ReserveMaterialRequest):
    if payload.qty <= 0:
        raise HTTPException(status_code=400, detail=_error_detail("qty must be positive"))
    try:
        result = data_manager.reserve_material_for_order(
            material_id=int(payload.material_id),
            order_id=int(payload.order_id),
            qty=float(payload.qty),
            unit=str(payload.unit or "pcs"),
            note=str(payload.note or ""),
            created_by=str(payload.created_by or ""),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_error_detail(str(e)))


@app.post("/api/inventory/cancel-reservation")
async def cancel_reservation(payload: CancelReservationRequest):
    try:
        result = data_manager.cancel_reservation(
            reservation_movement_id=int(payload.reservation_movement_id),
            created_by=str(payload.created_by or ""),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_error_detail(str(e)))


@app.post("/api/inventory/issue")
async def issue_material(payload: IssueMaterialRequest):
    if payload.qty <= 0:
        raise HTTPException(status_code=400, detail=_error_detail("qty must be positive"))
    try:
        result = data_manager.issue_material_to_order(
            material_id=int(payload.material_id),
            order_id=int(payload.order_id),
            qty=float(payload.qty),
            unit=str(payload.unit or "pcs"),
            unit_cost_override=payload.unit_cost_override,
            note=str(payload.note or ""),
            created_by=str(payload.created_by or ""),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_error_detail(str(e)))


@app.post("/api/inventory/return")
async def return_material(payload: ReturnMaterialRequest):
    if payload.qty <= 0:
        raise HTTPException(status_code=400, detail=_error_detail("qty must be positive"))
    try:
        result = data_manager.return_material_from_order(
            material_id=int(payload.material_id),
            order_id=int(payload.order_id),
            qty=float(payload.qty),
            unit=str(payload.unit or "pcs"),
            related_issue_movement_id=payload.related_issue_movement_id,
            note=str(payload.note or ""),
            created_by=str(payload.created_by or ""),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_error_detail(str(e)))


@app.post("/api/inventory/scrap")
async def scrap_material(payload: ScrapMaterialRequest, user: CurrentUser = Depends(get_current_user_info)):
    require_permission(user, Action.INVENTORY_SCRAP)
    if payload.qty <= 0:
        raise HTTPException(status_code=400, detail=_error_detail("qty must be positive"))
    try:
        result = data_manager.scrap_material(
            material_id=int(payload.material_id),
            qty=float(payload.qty),
            unit=str(payload.unit or "pcs"),
            order_id=payload.order_id,
            charge_to_order=bool(payload.charge_to_order),
            note=str(payload.note or ""),
            created_by=str(payload.created_by or ""),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_error_detail(str(e)))


@app.post("/api/inventory/correction")
async def correct_inventory(payload: CorrectionRequest, user: CurrentUser = Depends(get_current_user_info)):
    require_permission(user, Action.INVENTORY_CORRECTION)
    if payload.qty_delta == 0:
        raise HTTPException(status_code=400, detail=_error_detail("qty_delta must not be zero"))
    try:
        result = data_manager.correct_inventory(
            material_id=int(payload.material_id),
            qty_delta=float(payload.qty_delta),
            unit=str(payload.unit or "pcs"),
            note=str(payload.note or ""),
            created_by=str(payload.created_by or ""),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_error_detail(str(e)))


@app.get("/api/admin/audit-log")
async def get_audit_log(limit: int = 500):
    try:
        logs = data_manager.get_audit_logs(limit)
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


class UpdateRouteStatusRequest(BaseModel):
    status: str
    note: Optional[str] = None
    worker: Optional[str] = None
    blocked_reason: Optional[str] = None

@app.patch("/api/operations/routes/{route_id}/status")
async def update_route_status(route_id: str, payload: UpdateRouteStatusRequest):
    try:
        task = operations_store.get_route_task(route_id)
        if not task:
            raise HTTPException(status_code=404, detail=_error_detail("Task not found"))
        
        old_status = task.status
        task.status = payload.status
        if payload.note:
            task.notes = (task.notes or "") + f"\n[{datetime.now().strftime('%H:%M')}] {payload.note}"
        if payload.blocked_reason:
            task.blocked_reason = payload.blocked_reason
        elif payload.status != "problem":
            # Clear blocked reason if moving out of problem status
            task.blocked_reason = ""
        
        operations_store.update_route_task(task)
        
        # Log to audit log
        data_manager.log_action(
            user_name=payload.worker or "Station Operator",
            action="ROUTE_STATUS_UPDATE",
            target_type="route_task",
            target_id=route_id,
            details=f"Status changed from {old_status} to {payload.status}",
            metadata={"old": old_status, "new": payload.status, "note": payload.note}
        )
        
        return task.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


class HandoffRequest(BaseModel):
    worker: Optional[str] = None
    note: Optional[str] = None

class RejectRequest(BaseModel):
    worker: Optional[str] = None
    reason: str

@app.patch("/api/operations/routes/{route_id}/handoff")
async def handoff_route_task(route_id: str, payload: HandoffRequest):
    try:
        task = operations_store.get_route_task(route_id)
        if not task:
            raise HTTPException(status_code=404, detail=_error_detail("Task not found"))
        
        task.handoff_status = "ready_for_next"
        if payload.note:
            task.notes = (task.notes or "") + f"\n[{datetime.now().strftime('%H:%M')}] {payload.note}"
        
        operations_store.update_route_task(task)
        
        data_manager.log_action(
            user_name=payload.worker or "Station Operator",
            action="ROUTE_HANDOFF",
            target_type="route_task",
            target_id=route_id,
            details=f"Task handed off to next station",
            metadata={"new_status": "ready_for_next"}
        )
        return task.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))

@app.patch("/api/operations/routes/{route_id}/accept")
async def accept_route_task(route_id: str, payload: HandoffRequest):
    """Marks the previous task as accepted and starts the current one."""
    try:
        current_task = operations_store.get_route_task(route_id)
        if not current_task:
            raise HTTPException(status_code=404, detail=_error_detail("Task not found"))
            
        all_routes = operations_store.list_routes()
        project_tasks = [rt for rt in all_routes if rt.project_name == current_task.project_name]
        
        SEQUENCE = ["cnc", "oklejanie", "lakiernia", "montaz", "pakowanie"]
        try:
            s_idx = next(i for i, s in enumerate(SEQUENCE) if any(kw in current_task.task_type.lower() for kw in data_manager._get_station_keywords(s)))
        except StopIteration:
            s_idx = -1
            
        prev_task = None
        if s_idx > 0:
            for j in range(s_idx - 1, -1, -1):
                prev_s = SEQUENCE[j]
                prev_kw = data_manager._get_station_keywords(prev_s)
                prev_tasks = [rt for rt in project_tasks if any(kw in rt.task_type.lower() for kw in prev_kw)]
                if prev_tasks:
                    prev_task = prev_tasks[0]
                    break
        
        if prev_task:
            prev_task.handoff_status = "accepted"
            operations_store.update_route_task(prev_task)
            
        current_task.status = "w_trasie" 
        if payload.note:
            current_task.notes = (current_task.notes or "") + f"\n[{datetime.now().strftime('%H:%M')}] {payload.note}"
        operations_store.update_route_task(current_task)
        
        data_manager.log_action(
            user_name=payload.worker or "Station Operator",
            action="ROUTE_ACCEPT",
            target_type="route_task",
            target_id=route_id,
            details=f"Accepted handoff from previous station and started work",
            metadata={"prev_task_id": prev_task.id if prev_task else None}
        )
        return current_task.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))

@app.patch("/api/operations/routes/{route_id}/reject")
async def reject_route_task(route_id: str, payload: RejectRequest):
    """Marks the previous task as rejected back."""
    try:
        current_task = operations_store.get_route_task(route_id)
        if not current_task:
            raise HTTPException(status_code=404, detail=_error_detail("Task not found"))
            
        all_routes = operations_store.list_routes()
        project_tasks = [rt for rt in all_routes if rt.project_name == current_task.project_name]
        
        SEQUENCE = ["cnc", "oklejanie", "lakiernia", "montaz", "pakowanie"]
        try:
            s_idx = next(i for i, s in enumerate(SEQUENCE) if any(kw in current_task.task_type.lower() for kw in data_manager._get_station_keywords(s)))
        except StopIteration:
            s_idx = -1
            
        prev_task = None
        if s_idx > 0:
            for j in range(s_idx - 1, -1, -1):
                prev_s = SEQUENCE[j]
                prev_kw = data_manager._get_station_keywords(prev_s)
                prev_tasks = [rt for rt in project_tasks if any(kw in rt.task_type.lower() for kw in prev_kw)]
                if prev_tasks:
                    prev_task = prev_tasks[0]
                    break
        
        if prev_task:
            prev_task.handoff_status = "rejected_back"
            prev_task.quality_result = "needs_rework"
            prev_task.rework_reason = payload.reason
            prev_task.rejected_by = payload.worker or "Station Operator"
            prev_task.status = "problem" 
            operations_store.update_route_task(prev_task)
            
            data_manager.log_action(
                user_name=payload.worker or "Station Operator",
                action="ROUTE_REJECT",
                target_type="route_task",
                target_id=prev_task.id,
                details=f"Task rejected back from downstream station. Reason: {payload.reason}",
                metadata={"rejected_by": payload.worker, "reason": payload.reason}
            )
            
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


# --- NOTIFICATIONS & ESCALATIONS ---

@app.get("/api/notifications/summary")
async def get_notification_summary():
    from src.core.operations_store import OperationsStore
    ops_store = OperationsStore()
    issues = ops_store.list_issues()
    
    # Overdue issues
    overdue = [i for i in issues if i.is_overdue() and i.status != "zamkniete"]
    
    # Unassigned high priority
    unassigned = [i for i in issues if not i.owner and i.priority_manual in ["wysoki", "krytyczny"] and i.status != "zamkniete"]
    
    # Blocked too long (proxy: updated_at > 48h)
    blocked_too_long = []
    now = datetime.now()
    for i in issues:
        if i.status == "zablokowane":
            try:
                upd = datetime.strptime(i.updated_at, "%Y-%m-%d %H:%M:%S")
                if (now - upd).total_seconds() > 48 * 3600:
                    blocked_too_long.append(i)
            except:
                pass
                
    # Critical Alarms
    alarm_store = AlarmStoreJson()
    alarms = alarm_store.list_alarms()
    critical_alarms = [a for a in alarms if not a.is_resolved and a.severity == "krytyczny"]
    
    # Material Shortages
    procurement_data = data_manager.get_procurement_data()
    shortages = [p for p in procurement_data if p["shortage"] > 0]
    
    # Procurement Execution items (Persistent)
    exec_items = data_manager.get_procurement_items()
    unowned_proc = [i for i in exec_items if not i.get("owner_name") and i.get("status") != "received"]
    
    now = datetime.now()
    overdue_proc = []
    for i in exec_items:
        if i.get("status") == "received": continue
        due_str = i.get("due_date")
        if due_str:
            try:
                due_dt = datetime.fromisoformat(due_str.split("T")[0])
                if due_dt < now:
                    overdue_proc.append(i)
            except: pass
            
    summary = {
        "overdue_count": len(overdue) + len(overdue_proc),
        "unassigned_high_prio_count": len(unassigned) + len(unowned_proc),
        "blocked_too_long_count": len(blocked_too_long),
        "critical_alarms_count": len(critical_alarms),
        "material_shortage_count": len(shortages),
        "total_urgent": len(overdue) + len(unassigned) + len(blocked_too_long) + len(critical_alarms) + len(shortages) + len(unowned_proc) + len(overdue_proc)
    }
    return summary

@app.get("/api/notifications/items")
async def get_notification_items():
    from src.core.operations_store import OperationsStore
    ops_store = OperationsStore()
    issues = ops_store.list_issues()
    alarm_store = AlarmStoreJson()
    alarms = alarm_store.list_alarms()
    
    now = datetime.now()
    items = []
    
    # Overdue
    for i in issues:
        if i.is_overdue() and i.status != "zamkniete":
            items.append({
                "id": f"overdue_{i.id}",
                "category": "OVERDUE",
                "severity": "HIGH",
                "title": f"Overdue: {i.title}",
                "details": f"Planned for {i.due_date}. Project: {i.project_name}",
                "source_id": i.id,
                "source_type": "issue",
                "timestamp": i.updated_at,
                "owner": i.owner,
                "status": i.status,
                "priority": i.priority_manual,
                "escalation_reason": "Due date passed"
            })
            
    # Unassigned High Prio
    for i in issues:
        if not i.owner and i.priority_manual in ["wysoki", "krytyczny"] and i.status != "zamkniete":
            items.append({
                "id": f"unassigned_{i.id}",
                "category": "UNASSIGNED",
                "severity": "CRITICAL",
                "title": f"Unassigned Urgent: {i.title}",
                "details": f"High priority issue with no owner. Project: {i.project_name}",
                "source_id": i.id,
                "source_type": "issue",
                "timestamp": i.updated_at,
                "owner": "Unassigned",
                "status": i.status,
                "priority": i.priority_manual,
                "escalation_reason": "No owner assigned to high priority item"
            })
            
    # Blocked too long
    for i in issues:
        if i.status == "zablokowane":
            try:
                upd = datetime.strptime(i.updated_at, "%Y-%m-%d %H:%M:%S")
                hours = (now - upd).total_seconds() / 3600
                if hours > 48:
                    items.append({
                        "id": f"blocked_{i.id}",
                        "category": "BLOCKED_LONG",
                        "severity": "MEDIUM",
                        "title": f"Blocked >48h: {i.title}",
                        "details": f"Remains blocked for {int(hours)} hours. Project: {i.project_name}",
                        "source_id": i.id,
                        "source_type": "issue",
                        "timestamp": i.updated_at,
                        "owner": i.owner,
                        "status": i.status,
                        "priority": i.priority_manual,
                        "escalation_reason": "Issue blocked for too long"
                    })
            except:
                pass
                
    # Alarms
    for a in alarms:
        if not a.is_resolved and a.severity == "krytyczny":
            items.append({
                "id": f"alarm_{a.alarm_id}",
                "category": "ALARM",
                "severity": "CRITICAL",
                "title": f"Critical Alarm: {a.title}",
                "details": a.description or f"Category: {a.category}",
                "source_id": a.alarm_id,
                "source_type": "alarm",
                "timestamp": a.created_at,
                "owner": "System",
                "status": "active",
                "priority": "krytyczny",
                "escalation_reason": "Unresolved critical system alarm"
            })
            
    # Material Shortages
    procurement_data = data_manager.get_procurement_data()
    for p in procurement_data:
        if p["shortage"] > 0:
            items.append({
                "id": f"shortage_{p['material_id']}",
                "category": "MATERIAL",
                "severity": "HIGH" if p["status"] == "CRITICAL" else "MEDIUM",
                "title": f"Shortage: {p['name']}",
                "details": f"Missing {p['shortage']} {p['unit']}. On hand: {p['qty_on_hand']}",
                "source_id": p["material_id"],
                "source_type": "material_shortage",
                "timestamp": datetime.now().isoformat(),
                "owner": "Procurement",
                "status": "missing",
                "priority": "wysoki",
                "escalation_reason": "Material required for active orders but not available"
            })
            
    # Persistent Procurement Execution Issues
    exec_items = data_manager.get_procurement_items()
    now = datetime.now()
    for i in exec_items:
        if i.get("status") == "received": continue
        
        # 1. Unowned
        if not i.get("owner_name"):
            items.append({
                "id": f"proc_unowned_{i['id']}",
                "category": "UNASSIGNED",
                "severity": "HIGH",
                "title": f"Procurement Task Unassigned: {i['material_name']}",
                "details": f"Execution task for {i['qty_target']} {i['material_unit']} has no owner.",
                "source_id": i["id"],
                "source_type": "procurement_item",
                "timestamp": i["created_at"],
                "owner": "Unassigned",
                "status": i["status"],
                "priority": i["priority"],
                "escalation_reason": "Purchasing task requires an owner to proceed"
            })
        
        # 2. Overdue
        due_str = i.get("due_date")
        if due_str:
            try:
                due_dt = datetime.fromisoformat(due_str.split("T")[0])
                if due_dt < now:
                    items.append({
                        "id": f"proc_overdue_{i['id']}",
                        "category": "OVERDUE",
                        "severity": "CRITICAL" if i["priority"] == "krytyczny" else "HIGH",
                        "title": f"Overdue Procurement: {i['material_name']}",
                        "details": f"Planned for {due_str}. Current status: {i['status']}",
                        "source_id": i["id"],
                        "source_type": "procurement_item",
                        "timestamp": due_str,
                        "owner": i.get("owner_name") or "Unassigned",
                        "status": i["status"],
                        "priority": i["priority"],
                        "escalation_reason": "Purchasing deadline passed"
                    })
            except: pass
            
    # Production Workflow Blockers
    from src.core.operations_store import OperationsStore
    store = OperationsStore()
    routes = store.list_routes()
    for r in routes:
        if r.status == "problem" or r.quality_result == "needs_rework" or r.handoff_status == "rejected_back":
            reason = r.rework_reason or r.blocked_reason or 'Problem reported'
            items.append({
                "id": f"route_blocked_{r.id}",
                "category": "PRODUCTION",
                "severity": "HIGH",
                "title": f"Production Blocked/Rejected: {r.project_name}",
                "details": f"Station task #{r.id} ({r.task_type}) blocked: {reason}",
                "source_id": r.id,
                "source_type": "production_task",
                "timestamp": r.updated_at,
                "owner": r.crew or "Unassigned",
                "status": "blocked",
                "priority": "wysoki",
                "escalation_reason": "Production station task is in PROBLEM or REWORK state"
            })
            
        elif r.handoff_status == "ready_for_next":
            try:
                upd = datetime.fromisoformat(r.updated_at.split(".")[0])
                if (now - upd).total_seconds() > 24 * 3600:
                    items.append({
                        "id": f"route_handoff_{r.id}",
                        "category": "PRODUCTION",
                        "severity": "MEDIUM",
                        "title": f"Stalled Handoff: {r.project_name}",
                        "details": f"Task #{r.id} ({r.task_type}) waiting for acceptance > 24h",
                        "source_id": r.id,
                        "source_type": "production_task",
                        "timestamp": r.updated_at,
                        "owner": r.crew or "Unassigned",
                        "status": "waiting",
                        "priority": "normalny",
                        "escalation_reason": "Handoff pending for too long"
                    })
            except: pass

    # Fulfillment Blockers & Stalled
    fulfillments = store.list_fulfillments()
    for f in fulfillments:
        if f.status == "installation_blocked":
            items.append({
                "id": f"fulfillment_blocked_{f.project_name}",
                "category": "INSTALLATION",
                "severity": "HIGH",
                "title": f"Installation Blocked: {f.project_name}",
                "details": f"Blocked reason: {f.blocked_reason or 'No reason provided'}",
                "source_id": f.project_name,
                "source_type": "fulfillment",
                "timestamp": f.updated_at,
                "owner": f.installation_team or "Unassigned",
                "status": "blocked",
                "priority": "wysoki",
                "escalation_reason": "Installation is blocked"
            })
        elif f.status == "ready_for_shipping":
            try:
                upd = datetime.fromisoformat(f.updated_at.split(".")[0])
                if (now - upd).total_seconds() > 48 * 3600:
                    items.append({
                        "id": f"fulfillment_stalled_{f.project_name}",
                        "category": "LOGISTICS",
                        "severity": "MEDIUM",
                        "title": f"Stalled Shipping: {f.project_name}",
                        "details": f"Order ready for shipping > 48h",
                        "source_id": f.project_name,
                        "source_type": "fulfillment",
                        "timestamp": f.updated_at,
                        "owner": "Logistics",
                        "status": "waiting",
                        "priority": "normalny",
                        "escalation_reason": "Shipping pending for too long"
                    })
            except: pass
            
    return sorted(items, key=lambda x: x["severity"] == "CRITICAL", reverse=True)

# --- PROCUREMENT (ETAP 5) ---

@app.get("/api/procurement/availability")
async def get_procurement_availability():
    """Returns material availability and demand summary."""
    try:
        data = data_manager.get_procurement_data()
        return {"status": "ok", "items": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))

@app.get("/api/procurement/suggestions")
async def get_procurement_suggestions():
    """Returns material purchase suggestions based on shortages."""
    try:
        data = data_manager.get_procurement_data()
        suggestions = [item for item in data if item["shortage"] > 0]
        return {"status": "ok", "items": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))

@app.get("/api/procurement/execution")
async def get_procurement_execution():
    """Returns persistent procurement execution tasks."""
    try:
        items = data_manager.get_procurement_items()
        return {"status": "ok", "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))

@app.post("/api/procurement/execution")
async def create_procurement_execution(payload: Dict, user: CurrentUser = Depends(get_current_user_info)):
    """Creates a procurement execution item from a suggestion."""
    _require_permission(user, Action.PROCUREMENT_MANAGE)
    try:
        mid = int(payload.get("material_id", 0))
        qty = float(payload.get("qty_target", 0))
        if mid <= 0 or qty <= 0:
            raise HTTPException(status_code=400, detail="Invalid material_id or quantity")
        
        item_id = data_manager.create_procurement_item(
            material_id=mid,
            qty_target=qty,
            status=payload.get("status", "missing"),
            priority=payload.get("priority", "normalny"),
            owner_name=payload.get("owner_name", ""),
            supplier_name=payload.get("supplier_name", ""),
            due_date=payload.get("due_date", ""),
            order_id=payload.get("order_id"),
            note=payload.get("note", ""),
            created_by=user.name
        )
        return {"status": "ok", "id": item_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))

@app.patch("/api/procurement/execution/{item_id}")
async def update_procurement_execution(item_id: int, payload: Dict, user: CurrentUser = Depends(get_current_user_info)):
    """Updates procurement task status/owner/etc."""
    _require_permission(user, Action.PROCUREMENT_MANAGE)
    try:
        success = data_manager.update_procurement_item(item_id, payload, user_name=user.name)
        if not success:
            raise HTTPException(status_code=404, detail="Procurement item not found or no changes")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))

@app.get("/api/procurement/readiness")
async def get_procurement_readiness():
    """Returns material readiness summary for active orders."""
    try:
        summary = data_manager.get_order_readiness_summary()
        return {"status": "ok", "orders": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


@app.get("/api/stations/{station_type}/jobs")
async def get_station_jobs(station_type: str, user: CurrentUser = Depends(get_current_user_info)):
    """Returns production tasks for a specific station with dependency info."""
    try:
        items = data_manager.get_station_jobs(station_type)
        return {"status": "ok", "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


@app.get("/api/production/workflow/readiness")
async def get_production_workflow_readiness(user: CurrentUser = Depends(get_current_user_info)):
    """Analyzes production readiness across all active projects."""
    try:
        projects = data_manager.get_production_workflow_readiness()
        return {"status": "ok", "projects": projects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


# --- FULFILLMENT (DISPATCH, DELIVERY, INSTALLATION) ---

@app.get("/api/fulfillment/queue")
async def get_fulfillment_queue_endpoint(user: CurrentUser = Depends(get_current_user_info)):
    """Returns the fulfillment queue (orders ready for shipping, dispatch, delivery, install)."""
    try:
        queue = data_manager.get_fulfillment_queue()
        return {"status": "ok", "items": queue}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))

@app.patch("/api/fulfillment/{project_name}/status")
async def update_fulfillment_status(project_name: str, payload: Dict, user: CurrentUser = Depends(get_current_user_info)):
    """Updates the post-production fulfillment status of an order."""
    _require_permission(user, Action.PRODUCTION_MANAGE) # Adjust permission as needed
    try:
        from src.core.operations_store import OperationsStore
        store = OperationsStore()
        
        record = store.get_fulfillment(project_name)
        if not record:
            # Check if it's in the readiness queue
            readiness = data_manager.get_production_workflow_readiness()
            proj_info = next((p for p in readiness if p["project_name"] == project_name), None)
            if not proj_info:
                raise HTTPException(status_code=404, detail="Project not found or not in production.")
            
            from src.core.operations_models import FulfillmentRecord
            record = FulfillmentRecord(project_name=project_name)
            
        new_status = payload.get("status")
        if not new_status:
            raise HTTPException(status_code=400, detail="Missing status.")
            
        old_status = record.status
        record.status = new_status
        record.updated_at = now_iso()
        record.notes = payload.get("notes", record.notes)
        
        if new_status == "packed":
            record.packed_at = now_iso()
            record.packed_by = user.name
        elif new_status == "dispatched":
            record.dispatched_at = now_iso()
            record.dispatched_by = user.name
        elif new_status == "delivered":
            record.delivered_at = now_iso()
            record.delivered_by = user.name
            record.delivery_note = payload.get("delivery_note", record.delivery_note)
        elif new_status == "installation_blocked":
            record.blocked_reason = payload.get("blocked_reason", record.blocked_reason)
        elif new_status == "installation_in_progress":
            record.installation_team = payload.get("installation_team", record.installation_team)
            record.installation_progress = float(payload.get("installation_progress", record.installation_progress))
        
        # Always allow updating these fields regardless of status
        if "package_count" in payload:
            record.package_count = int(payload["package_count"])
        if "carrier_name" in payload:
            record.carrier_name = str(payload["carrier_name"])
        if "tracking_number" in payload:
            record.tracking_number = str(payload["tracking_number"])
        if "installation_progress" in payload:
            record.installation_progress = float(payload["installation_progress"])
        if "installation_planned_date" in payload:
            record.installation_planned_date = str(payload["installation_planned_date"])
            
        store.update_fulfillment(record)
        data_manager.log_action(user.name, "FULFILLMENT_UPDATE", details=f"{project_name} -> {new_status}")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(str(e)))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
