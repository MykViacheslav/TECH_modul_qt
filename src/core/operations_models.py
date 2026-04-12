from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
import uuid


AREA_VALUES: dict[str, str] = {
    "finanse": "Finanse",
    "produkcja": "Produkcja",
    "biuro": "Biuro",
    "magazyn": "Magazyn",
    "montaz": "Montaz",
    "klient": "Klient",
    "jakosc": "Jakosc",
    "logistyka": "Logistyka",
}

ISSUE_TYPE_VALUES: dict[str, str] = {
    "brak_elementu": "Brak elementu",
    "brak_materialu": "Brak materialu",
    "blad_wymiaru": "Blad wymiaru",
    "blad_projektu": "Blad projektu",
    "reklamacja": "Reklamacja",
    "opoznienie": "Opoznienie",
    "brak_informacji": "Brak informacji",
    "blokada_faktury": "Blokada faktury",
    "blokada_montazu": "Blokada montazu",
    "blokada_produkcji": "Blokada produkcji",
    "rozrachunek": "Rozrachunek",
    "inne": "Inne",
}

IMPACT_LEVEL_VALUES: dict[str, str] = {
    "niski": "Niski",
    "sredni": "Sredni",
    "wysoki": "Wysoki",
    "krytyczny": "Krytyczny",
}

PRIORITY_VALUES: dict[str, str] = {
    "niski": "Niski",
    "normalny": "Normalny",
    "wysoki": "Wysoki",
    "krytyczny": "Krytyczny",
}

STATUS_VALUES: dict[str, str] = {
    "nowe": "Nowe",
    "w_toku": "W toku",
    "oczekuje": "Oczekuje",
    "zablokowane": "Zablokowane",
    "do_decyzji": "Do decyzji",
    "zamkniete": "Zamkniete",
}

ROUTE_STATUS_VALUES: dict[str, str] = {
    "planowane": "Planowane",
    "w_trasie": "W trasie",
    "wykonane": "Wykonane",
    "anulowane": "Anulowane",
}


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "tak", "yes", "y"}


def to_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x or "").strip() for x in value if str(x or "").strip()]
    raw = str(value or "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def new_issue_id() -> str:
    return f"ISS-{uuid.uuid4().hex[:10].upper()}"


def new_route_task_id() -> str:
    return f"ROUTE-{uuid.uuid4().hex[:10].upper()}"


@dataclass
class IssueRecord:
    id: str = ""
    created_at: str = ""
    updated_at: str = ""
    title: str = ""
    description: str = ""
    area: str = "biuro"
    issue_type: str = "inne"
    impact_level: str = "sredni"
    priority_manual: str = "normalny"
    status: str = "nowe"
    project_id: str = ""
    project_name: str = ""
    client_id: str = ""
    client_name: str = ""
    order_id: str = ""
    owner: str = ""
    due_date: str = ""
    blocks_invoice: bool = False
    blocks_production: bool = False
    blocks_installation: bool = False
    estimated_cost: float = 0.0
    estimated_revenue_unlock: float = 0.0
    estimated_time_minutes: int = 0
    city: str = ""
    address: str = ""
    notes: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "IssueRecord":
        row = row if isinstance(row, dict) else {}
        return cls(
            id=str(row.get("id", "") or "").strip() or new_issue_id(),
            created_at=str(row.get("created_at", "") or "").strip() or now_iso(),
            updated_at=str(row.get("updated_at", "") or "").strip() or now_iso(),
            title=str(row.get("title", "") or "").strip(),
            description=str(row.get("description", "") or "").strip(),
            area=str(row.get("area", "biuro") or "biuro").strip().lower(),
            issue_type=str(row.get("issue_type", "inne") or "inne").strip().lower(),
            impact_level=str(row.get("impact_level", "sredni") or "sredni").strip().lower(),
            priority_manual=str(row.get("priority_manual", "normalny") or "normalny").strip().lower(),
            status=str(row.get("status", "nowe") or "nowe").strip().lower(),
            project_id=str(row.get("project_id", "") or "").strip(),
            project_name=str(row.get("project_name", "") or "").strip(),
            client_id=str(row.get("client_id", "") or "").strip(),
            client_name=str(row.get("client_name", "") or "").strip(),
            order_id=str(row.get("order_id", "") or "").strip(),
            owner=str(row.get("owner", "") or "").strip(),
            due_date=str(row.get("due_date", "") or "").strip(),
            blocks_invoice=to_bool(row.get("blocks_invoice", False)),
            blocks_production=to_bool(row.get("blocks_production", False)),
            blocks_installation=to_bool(row.get("blocks_installation", False)),
            estimated_cost=float(row.get("estimated_cost", 0.0) or 0.0),
            estimated_revenue_unlock=float(row.get("estimated_revenue_unlock", 0.0) or 0.0),
            estimated_time_minutes=int(row.get("estimated_time_minutes", 0) or 0),
            city=str(row.get("city", "") or "").strip(),
            address=str(row.get("address", "") or "").strip(),
            notes=str(row.get("notes", "") or "").strip(),
            tags=to_str_list(row.get("tags", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id or new_issue_id(),
            "created_at": self.created_at or now_iso(),
            "updated_at": self.updated_at or now_iso(),
            "title": str(self.title or "").strip(),
            "description": str(self.description or "").strip(),
            "area": str(self.area or "biuro").strip().lower(),
            "issue_type": str(self.issue_type or "inne").strip().lower(),
            "impact_level": str(self.impact_level or "sredni").strip().lower(),
            "priority_manual": str(self.priority_manual or "normalny").strip().lower(),
            "status": str(self.status or "nowe").strip().lower(),
            "project_id": str(self.project_id or "").strip(),
            "project_name": str(self.project_name or "").strip(),
            "client_id": str(self.client_id or "").strip(),
            "client_name": str(self.client_name or "").strip(),
            "order_id": str(self.order_id or "").strip(),
            "owner": str(self.owner or "").strip(),
            "due_date": str(self.due_date or "").strip(),
            "blocks_invoice": bool(self.blocks_invoice),
            "blocks_production": bool(self.blocks_production),
            "blocks_installation": bool(self.blocks_installation),
            "estimated_cost": float(self.estimated_cost or 0.0),
            "estimated_revenue_unlock": float(self.estimated_revenue_unlock or 0.0),
            "estimated_time_minutes": int(self.estimated_time_minutes or 0),
            "city": str(self.city or "").strip(),
            "address": str(self.address or "").strip(),
            "notes": str(self.notes or "").strip(),
            "tags": [str(x or "").strip() for x in self.tags if str(x or "").strip()],
        }

    def is_overdue(self, today: date | None = None) -> bool:
        if self.status == "zamkniete":
            return False
        text = str(self.due_date or "").strip()[:10]
        if not text:
            return False
        try:
            due = datetime.strptime(text, "%Y-%m-%d").date()
        except Exception:
            return False
        ref = today or date.today()
        return due < ref

    def is_active(self) -> bool:
        return self.status != "zamkniete"

    def is_quick_close_candidate(self) -> bool:
        if not self.is_active():
            return False
        if 0 < int(self.estimated_time_minutes or 0) <= 60:
            return True
        tagset = {x.lower() for x in self.tags}
        return "szybkie_domkniecie" in tagset or "quick_close" in tagset


@dataclass
class RouteTaskRecord:
    id: str = ""
    issue_id: str = ""
    task_type: str = "inne"
    project_name: str = ""
    client_name: str = ""
    city: str = ""
    address: str = ""
    planned_date: str = ""
    crew: str = ""
    status: str = "planowane"
    estimated_time_minutes: int = 0
    route_group: str = ""
    trip_order: int = 0
    route_score: float = 0.0
    blocks_payment: bool = False
    estimated_payment_unlock: float = 0.0
    finance_followup_status: str = "brak"
    ready_to_invoice: bool = False
    requires_settlement: bool = False
    requires_confirmation: bool = False
    finance_followup_note: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "RouteTaskRecord":
        row = row if isinstance(row, dict) else {}
        return cls(
            id=str(row.get("id", "") or "").strip() or new_route_task_id(),
            issue_id=str(row.get("issue_id", "") or "").strip(),
            task_type=str(row.get("task_type", "inne") or "inne").strip().lower(),
            project_name=str(row.get("project_name", "") or "").strip(),
            client_name=str(row.get("client_name", "") or "").strip(),
            city=str(row.get("city", "") or "").strip(),
            address=str(row.get("address", "") or "").strip(),
            planned_date=str(row.get("planned_date", "") or "").strip(),
            crew=str(row.get("crew", "") or "").strip(),
            status=str(row.get("status", "planowane") or "planowane").strip().lower(),
            estimated_time_minutes=int(row.get("estimated_time_minutes", 0) or 0),
            route_group=str(row.get("route_group", "") or "").strip(),
            trip_order=int(row.get("trip_order", 0) or 0),
            route_score=float(row.get("route_score", 0.0) or 0.0),
            blocks_payment=to_bool(row.get("blocks_payment", False)),
            estimated_payment_unlock=float(row.get("estimated_payment_unlock", 0.0) or 0.0),
            finance_followup_status=str(row.get("finance_followup_status", "brak") or "brak").strip().lower(),
            ready_to_invoice=to_bool(row.get("ready_to_invoice", False)),
            requires_settlement=to_bool(row.get("requires_settlement", False)),
            requires_confirmation=to_bool(row.get("requires_confirmation", False)),
            finance_followup_note=str(row.get("finance_followup_note", "") or "").strip(),
            notes=str(row.get("notes", "") or "").strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id or new_route_task_id(),
            "issue_id": str(self.issue_id or "").strip(),
            "task_type": str(self.task_type or "inne").strip().lower(),
            "project_name": str(self.project_name or "").strip(),
            "client_name": str(self.client_name or "").strip(),
            "city": str(self.city or "").strip(),
            "address": str(self.address or "").strip(),
            "planned_date": str(self.planned_date or "").strip(),
            "crew": str(self.crew or "").strip(),
            "status": str(self.status or "planowane").strip().lower(),
            "estimated_time_minutes": int(self.estimated_time_minutes or 0),
            "route_group": str(self.route_group or "").strip(),
            "trip_order": int(self.trip_order or 0),
            "route_score": float(self.route_score or 0.0),
            "blocks_payment": bool(self.blocks_payment),
            "estimated_payment_unlock": float(self.estimated_payment_unlock or 0.0),
            "finance_followup_status": str(self.finance_followup_status or "brak").strip().lower(),
            "ready_to_invoice": bool(self.ready_to_invoice),
            "requires_settlement": bool(self.requires_settlement),
            "requires_confirmation": bool(self.requires_confirmation),
            "finance_followup_note": str(self.finance_followup_note or "").strip(),
            "notes": str(self.notes or "").strip(),
        }


def issue_visible_for_role(issue: IssueRecord, role: str, worker_name: str = "") -> bool:
    role_norm = str(role or "").strip().lower()
    worker_norm = str(worker_name or "").strip().lower()
    if role_norm in {"wlasciciel", "biuro", ""}:
        return True
    if role_norm == "produkcja":
        return issue.area in {"produkcja", "montaz", "logistyka"} or issue.blocks_production or issue.blocks_installation
    if role_norm == "magazyn":
        return issue.area in {"magazyn", "logistyka"} or issue.issue_type == "brak_materialu"
    if role_norm == "montaz":
        owner = str(issue.owner or "").strip().lower()
        return bool(worker_norm and owner and worker_norm in owner)
    return False


def route_visible_for_role(route: RouteTaskRecord, role: str, worker_name: str = "") -> bool:
    role_norm = str(role or "").strip().lower()
    worker_norm = str(worker_name or "").strip().lower()
    if role_norm in {"wlasciciel", "biuro", ""}:
        return True
    if role_norm == "produkcja":
        return route.task_type in {"blokada_produkcji", "blokada_montazu", "opoznienie", "inne"}
    if role_norm == "magazyn":
        return route.task_type in {"brak_materialu", "logistyka", "brak_elementu", "inne"}
    if role_norm == "montaz":
        crew = str(route.crew or "").strip().lower()
        return bool(worker_norm and crew and worker_norm in crew)
    return False
