from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.core.maps_urls import build_google_maps_directions_url
from src.core.operations_models import RouteTaskRecord
from src.core.operations_store import OperationsStore
from src.core.visit_history_store import VisitHistoryStore
from src.storage.client_store_json import ClientStoreJson
from src.storage.data_paths import data_dir
from src.storage.order_store_json import OrderStoreJson


VISIT_TYPE_VALUES = {"montaz", "pomiar", "poprawka", "odbior", "serwis", "transport", "inne"}
VISIT_STATUS_VALUES = {"planowane", "potwierdzone", "w trasie", "wykonane", "anulowane", "do ustalenia"}


@dataclass
class MapOrderPoint:
    id: str = ""
    order_id: str = ""
    project_id: str = ""
    project_name: str = ""
    client_id: str = ""
    client_name: str = ""
    contact_name: str = ""
    contact_phone: str = ""
    contact_phone_alt: str = ""
    full_address: str = ""
    city: str = ""
    postal_code: str = ""
    country: str = ""
    visit_type: str = "inne"
    visit_status: str = "do ustalenia"
    last_visit_at: str = ""
    next_visit_at: str = ""
    work_scope: str = ""
    items_to_take: str = ""
    crew_notes: str = ""
    crew: str = ""
    is_active: bool = True
    lat: float | None = None
    lng: float | None = None
    place_id: str = ""
    source_kind: str = ""
    trip_order: int = 0
    route_group: str = ""
    has_history: bool = False
    last_history_note: str = ""
    last_visit_result: str = ""
    blocks_payment: bool = False
    estimated_payment_unlock: float = 0.0
    finance_followup_status: str = "brak"
    finance_followup_note: str = ""
    ready_to_invoice: bool = False
    requires_settlement: bool = False
    requires_confirmation: bool = False
    last_finance_result: str = ""


def _clean_visit_type(value: str) -> str:
    norm = str(value or "").strip().lower()
    return norm if norm in VISIT_TYPE_VALUES else "inne"


def _clean_visit_status(value: str) -> str:
    norm = str(value or "").strip().lower().replace("_", " ")
    return norm if norm in VISIT_STATUS_VALUES else "do ustalenia"


class OrdersMapService:
    def __init__(self, app_context=None, operations_store=None, data_dir: str | Path | None = None) -> None:
        base_dir = Path(data_dir) if data_dir is not None else data_dir_fn()
        self._ctx = app_context or {}
        self._operations = operations_store if operations_store is not None else OperationsStore()
        self._order_store = self._ctx.get("order_store") or OrderStoreJson(path=base_dir / "orders.json")
        self._client_store = self._ctx.get("client_store") or ClientStoreJson(path=base_dir / "clients.json")
        self._history_store = self._ctx.get("visit_history_store") or VisitHistoryStore(data_dir=base_dir)

    def _latest_history_by_point(self) -> dict[str, object]:
        latest: dict[str, object] = {}
        for rec in self._history_store.list_records():
            if rec.point_id and rec.point_id not in latest:
                latest[rec.point_id] = rec
        return latest

    def list_map_points(self) -> list[MapOrderPoint]:
        out: list[MapOrderPoint] = []
        client_by_name = {c.name: c for c in self._client_store.list_clients()}
        latest_hist = self._latest_history_by_point()

        for order in self._order_store.list_orders():
            address = str(order.site_address or "").strip()
            if not address:
                parts = [
                    str(order.site_street or "").strip(),
                    str(order.site_house_number or "").strip(),
                    str(order.site_apartment_number or "").strip(),
                    str(order.site_postal_code or "").strip(),
                    str(order.site_city or "").strip(),
                ]
                address = " ".join([x for x in parts if x]).strip()
            client = client_by_name.get(order.client_name)
            hist = latest_hist.get(f"order::{order.code}")
            point = MapOrderPoint(
                id=f"order::{order.code}",
                order_id=order.code,
                project_id=order.order_id or order.code,
                project_name=order.order_name or order.code,
                client_id=str(getattr(client, "client_id", "") or ""),
                client_name=order.client_name,
                contact_name=order.client_name,
                contact_phone=str(getattr(client, "phone", "") or "").strip(),
                full_address=address,
                city=order.site_city,
                postal_code=order.site_postal_code,
                country="PL",
                visit_type="inne",
                visit_status="do ustalenia",
                last_visit_at=str(getattr(hist, "visit_date", "") or ""),
                next_visit_at="",
                work_scope=order.notes or "",
                items_to_take="",
                crew_notes="",
                crew=order.worker_name,
                is_active=str(order.status or "").lower() not in {"anulowane", "zamkniete"},
                source_kind="order",
                trip_order=0,
                route_group="",
                has_history=hist is not None,
                last_history_note=str(getattr(hist, "notes", "") or ""),
                last_visit_result=str(getattr(hist, "status_after", "") or ""),
                blocks_payment=bool(getattr(hist, "payment_unlocked_amount", 0.0) > 0.0),
                estimated_payment_unlock=float(getattr(hist, "payment_unlocked_amount", 0.0) or 0.0),
                finance_followup_status=str(getattr(hist, "finance_result", "brak") or "brak"),
                finance_followup_note=str(getattr(hist, "notes", "") or ""),
                ready_to_invoice=bool(getattr(hist, "ready_to_invoice", False)),
                requires_settlement=bool(getattr(hist, "requires_settlement", False)),
                requires_confirmation=bool(getattr(hist, "requires_confirmation", False)),
                last_finance_result=str(getattr(hist, "finance_result", "brak") or "brak"),
            )
            out.append(point)

        for route in self._operations.list_routes():
            issue = self._operations.get_issue(route.issue_id) if route.issue_id else None
            contact_phone = ""
            if issue:
                client = client_by_name.get(issue.client_name)
                contact_phone = str(getattr(client, "phone", "") or "").strip()
            point_id = f"route::{route.id}"
            hist = latest_hist.get(point_id)
            point = MapOrderPoint(
                id=point_id,
                order_id=issue.order_id if issue else "",
                project_id=issue.project_id if issue else "",
                project_name=route.project_name or (issue.project_name if issue else ""),
                client_id=issue.client_id if issue else "",
                client_name=route.client_name or (issue.client_name if issue else ""),
                contact_name=route.client_name or (issue.client_name if issue else ""),
                contact_phone=contact_phone,
                full_address=route.address or (issue.address if issue else ""),
                city=route.city or (issue.city if issue else ""),
                postal_code="",
                country="PL",
                visit_type=_clean_visit_type(route.task_type),
                visit_status=_clean_visit_status(route.status),
                last_visit_at=str(getattr(hist, "visit_date", "") or ""),
                next_visit_at=route.planned_date,
                work_scope=issue.description if issue else "",
                items_to_take="",
                crew_notes=route.notes,
                crew=route.crew,
                is_active=route.status not in {"wykonane", "anulowane"},
                source_kind="route",
                trip_order=int(route.trip_order or 0),
                route_group=route.route_group,
                has_history=hist is not None,
                last_history_note=str(getattr(hist, "notes", "") or ""),
                last_visit_result=str(getattr(hist, "status_after", "") or ""),
                blocks_payment=bool(route.blocks_payment),
                estimated_payment_unlock=float(route.estimated_payment_unlock or 0.0),
                finance_followup_status=str(route.finance_followup_status or "brak"),
                finance_followup_note=str(route.finance_followup_note or ""),
                ready_to_invoice=bool(route.ready_to_invoice),
                requires_settlement=bool(route.requires_settlement),
                requires_confirmation=bool(route.requires_confirmation),
                last_finance_result=str(getattr(hist, "finance_result", route.finance_followup_status or "brak") or "brak"),
            )
            out.append(point)
        return out

    def filter_map_points(
        self,
        *,
        text: str = "",
        city: str = "",
        crew: str = "",
        visit_type: str = "",
        visit_status: str = "",
        active_only: bool = False,
        only_today: bool = False,
        with_phone_only: bool = False,
        only_blocks_payment: bool = False,
        only_ready_to_invoice: bool = False,
        only_requires_settlement: bool = False,
        only_requires_confirmation: bool = False,
    ) -> list[MapOrderPoint]:
        q_text = str(text or "").strip().lower()
        q_city = str(city or "").strip().lower()
        q_crew = str(crew or "").strip().lower()
        q_type = str(visit_type or "").strip().lower()
        q_status = str(visit_status or "").strip().lower()
        today = date.today().strftime("%Y-%m-%d")
        out: list[MapOrderPoint] = []
        for p in self.list_map_points():
            if active_only and not p.is_active:
                continue
            if only_today and str(p.next_visit_at or "")[:10] != today:
                continue
            if with_phone_only and not str(p.contact_phone or "").strip():
                continue
            if only_blocks_payment and not p.blocks_payment:
                continue
            if only_ready_to_invoice and not p.ready_to_invoice:
                continue
            if only_requires_settlement and not p.requires_settlement:
                continue
            if only_requires_confirmation and not p.requires_confirmation:
                continue
            if q_city and q_city not in str(p.city or "").lower():
                continue
            if q_crew and q_crew not in str(p.crew or "").lower():
                continue
            if q_type and q_type != "all" and q_type != str(p.visit_type or "").lower():
                continue
            if q_status and q_status != "all" and q_status != str(p.visit_status or "").lower():
                continue
            if q_text:
                hay = " ".join(
                    [
                        p.project_name,
                        p.client_name,
                        p.full_address,
                        p.city,
                        p.contact_phone,
                        p.work_scope,
                        p.crew_notes,
                        p.last_history_note,
                    ]
                ).lower()
                if q_text not in hay:
                    continue
            out.append(p)
        return out

    def group_points_by_city(self) -> dict[str, list[MapOrderPoint]]:
        grouped: dict[str, list[MapOrderPoint]] = {}
        for p in self.list_map_points():
            key = str(p.city or "").strip() or "(brak miasta)"
            grouped.setdefault(key, []).append(p)
        return grouped

    def build_route_points_for_day(self, planned_date: str, crew: str = "") -> list[MapOrderPoint]:
        day = str(planned_date or "").strip()
        crew_q = str(crew or "").strip().lower()
        points = []
        for p in self.list_map_points():
            if p.source_kind != "route":
                continue
            if day and str(p.next_visit_at or "")[:10] != day:
                continue
            if crew_q and crew_q not in str(p.crew or "").lower():
                continue
            points.append(p)
        points.sort(key=lambda x: (int(x.trip_order or 0) <= 0, int(x.trip_order or 0), x.client_name))
        return points

    def build_google_maps_route_for_day(self, planned_date: str, crew: str = "", origin: str = "") -> str:
        points = [p for p in self.build_route_points_for_day(planned_date, crew) if p.is_active]
        addresses = [str(p.full_address or "").strip() for p in points if str(p.full_address or "").strip()]
        if not addresses:
            return ""
        start = str(origin or "").strip() or addresses[0]
        if len(addresses) == 1:
            return build_google_maps_directions_url(start, addresses[0], [])
        destination = addresses[-1]
        waypoints = addresses[1:-1]
        return build_google_maps_directions_url(start, destination, waypoints=waypoints)

    def reorder_route_points(self, route_group: str, ordered_point_ids: list[str]) -> None:
        group = str(route_group or "").strip()
        if not group:
            return
        ids = []
        for pid in ordered_point_ids or []:
            text = str(pid or "").strip()
            if text.startswith("route::"):
                text = text.split("::", 1)[1]
            if text:
                ids.append(text)
        order_map = {rid: idx + 1 for idx, rid in enumerate(ids)}
        for route in self._operations.list_routes():
            if str(route.route_group or "").strip() != group:
                continue
            if route.id in order_map:
                route.trip_order = order_map[route.id]
                self._operations.update_route_task(route)

    def append_point_to_route(self, point_id: str, planned_date: str, crew: str, route_group: str = "") -> None:
        pid = str(point_id or "").strip()
        day = str(planned_date or "").strip()
        crew_text = str(crew or "").strip()
        group = str(route_group or "").strip() or f"{day}-{crew_text or 'ekipa'}"

        # Existing route point
        if pid.startswith("route::"):
            rid = pid.split("::", 1)[1]
            route = self._operations.get_route_task(rid)
            if route is None:
                return
            route.planned_date = day or route.planned_date
            route.crew = crew_text or route.crew
            route.route_group = group
            max_order = max([int(r.trip_order or 0) for r in self._operations.list_routes() if r.route_group == group], default=0)
            route.trip_order = max_order + 1
            self._operations.update_route_task(route)
            return

        # Order point
        if pid.startswith("order::"):
            code = pid.split("::", 1)[1]
            order = self._order_store.get(code)
            if order is None:
                return
            address = str(order.site_address or "").strip()
            if not address:
                bits = [
                    str(order.site_street or "").strip(),
                    str(order.site_house_number or "").strip(),
                    str(order.site_apartment_number or "").strip(),
                    str(order.site_postal_code or "").strip(),
                    str(order.site_city or "").strip(),
                ]
                address = " ".join([x for x in bits if x]).strip()
            max_order = max([int(r.trip_order or 0) for r in self._operations.list_routes() if r.route_group == group], default=0)
            rec = RouteTaskRecord(
                issue_id="",
                task_type="transport",
                project_name=order.order_name or order.code,
                client_name=order.client_name,
                city=order.site_city,
                address=address,
                planned_date=day,
                crew=crew_text or order.worker_name,
                status="planowane",
                estimated_time_minutes=0,
                route_group=group,
                trip_order=max_order + 1,
                route_score=0.0,
                notes=order.notes or "",
            )
            self._operations.add_route_task(rec)

    def mark_point_done(self, point_id: str, planned_date: str, crew: str = "") -> None:
        pid = str(point_id or "").strip()
        day = str(planned_date or "").strip()
        crew_text = str(crew or "").strip().lower()
        if pid.startswith("route::"):
            rid = pid.split("::", 1)[1]
            route = self._operations.get_route_task(rid)
            if route is None:
                return
            if day and route.planned_date != day:
                return
            if crew_text and crew_text not in str(route.crew or "").lower():
                return
            route.status = "wykonane"
            self._operations.update_route_task(route)

    def get_points_ready_to_invoice(self) -> list[MapOrderPoint]:
        return [x for x in self.list_map_points() if x.ready_to_invoice]

    def get_points_requiring_settlement(self) -> list[MapOrderPoint]:
        return [x for x in self.list_map_points() if x.requires_settlement]

    def get_points_requiring_confirmation(self) -> list[MapOrderPoint]:
        return [x for x in self.list_map_points() if x.requires_confirmation]

    def get_points_blocking_payment(self) -> list[MapOrderPoint]:
        return [x for x in self.list_map_points() if x.blocks_payment or float(x.estimated_payment_unlock or 0.0) > 0.0]

    def mark_point_finance_result(
        self,
        *,
        point_id: str,
        finance_followup_status: str,
        estimated_payment_unlock: float,
        ready_to_invoice: bool,
        requires_settlement: bool,
        requires_confirmation: bool,
        finance_followup_note: str = "",
    ) -> None:
        pid = str(point_id or "").strip()
        if not pid.startswith("route::"):
            return
        route_id = pid.split("::", 1)[1]
        route = self._operations.get_route_task(route_id)
        if route is None:
            return
        route.blocks_payment = float(estimated_payment_unlock or 0.0) > 0.0
        route.estimated_payment_unlock = float(estimated_payment_unlock or 0.0)
        route.finance_followup_status = str(finance_followup_status or "brak").strip().lower()
        route.ready_to_invoice = bool(ready_to_invoice)
        route.requires_settlement = bool(requires_settlement)
        route.requires_confirmation = bool(requires_confirmation)
        route.finance_followup_note = str(finance_followup_note or "").strip()
        self._operations.update_route_task(route)
        self._history_store.append_finance_result(
            point_id=pid,
            finance_result=route.finance_followup_status,
            payment_unlocked_amount=route.estimated_payment_unlock,
            ready_to_invoice=route.ready_to_invoice,
            requires_settlement=route.requires_settlement,
            requires_confirmation=route.requires_confirmation,
            notes=route.finance_followup_note,
        )


def data_dir_fn() -> Path:
    return data_dir()
