from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
import json
import os
from pathlib import Path
from typing import Any

from src.core.operations_models import (
    IssueRecord,
    RouteTaskRecord,
    issue_visible_for_role,
    now_iso,
    route_visible_for_role,
)
from src.storage.data_paths import data_dir


def _load_json_utf8(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return dict(default)
    except Exception:
        return dict(default)
    if not raw.strip():
        return dict(default)
    try:
        payload = json.loads(raw)
    except Exception:
        return dict(default)
    return payload if isinstance(payload, dict) else dict(default)


def _save_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
        fh.write("\n")
    os.replace(tmp, path)

from src.core.operations_models import IssueRecord, RouteTaskRecord, FulfillmentRecord

class OperationsStore:
    def __init__(
        self,
        issues_path: Path | None = None,
        routes_path: Path | None = None,
    ) -> None:
        base = data_dir()
        self._issues_path = issues_path if issues_path is not None else base / "operations_issues.json"
        self._routes_path = routes_path if routes_path is not None else base / "operations_routes.json"
        self._fulfillment_path = base / "operations_fulfillment.json"
        self._ensure_files()

    def _ensure_files(self) -> None:
        self._issues_path.parent.mkdir(parents=True, exist_ok=True)
        self._routes_path.parent.mkdir(parents=True, exist_ok=True)
        self._fulfillment_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._issues_path.exists():
            _save_json_atomic(self._issues_path, {"issues": []})
        if not self._routes_path.exists():
            _save_json_atomic(self._routes_path, {"routes": []})
        if not self._fulfillment_path.exists():
            _save_json_atomic(self._fulfillment_path, {"fulfillments": []})

    def _read_issues_payload(self) -> dict[str, Any]:
        payload = _load_json_utf8(self._issues_path, {"issues": []})
        rows = payload.get("issues", [])
        if not isinstance(rows, list):
            payload["issues"] = []
        return payload

    def _read_routes_payload(self) -> dict[str, Any]:
        payload = _load_json_utf8(self._routes_path, {"routes": []})
        rows = payload.get("routes", [])
        if not isinstance(rows, list):
            payload["routes"] = []
        return payload

    def _read_fulfillment_payload(self) -> dict[str, Any]:
        payload = _load_json_utf8(self._fulfillment_path, {"fulfillments": []})
        rows = payload.get("fulfillments", [])
        if not isinstance(rows, list):
            payload["fulfillments"] = []
        return payload

    def list_issues(self) -> list[IssueRecord]:
        payload = self._read_issues_payload()
        out: list[IssueRecord] = []
        for row in payload.get("issues", []):
            if isinstance(row, dict):
                out.append(IssueRecord.from_dict(row))
        out.sort(key=lambda x: (x.status == "zamkniete", x.is_overdue(), x.updated_at), reverse=True)
        return out

    def get_issue(self, issue_id: str) -> IssueRecord | None:
        issue_id_norm = str(issue_id or "").strip()
        if not issue_id_norm:
            return None
        for issue in self.list_issues():
            if issue.id == issue_id_norm:
                return issue
        return None

    def add_issue(self, record: IssueRecord) -> IssueRecord:
        payload = self._read_issues_payload()
        rows = payload.get("issues", [])
        if not isinstance(rows, list):
            rows = []
        item = record.to_dict()
        item["created_at"] = item.get("created_at") or now_iso()
        item["updated_at"] = now_iso()
        rows.append(item)
        payload["issues"] = rows
        payload["updated_at"] = now_iso()
        _save_json_atomic(self._issues_path, payload)
        return IssueRecord.from_dict(item)

    def update_issue(self, record: IssueRecord) -> IssueRecord:
        payload = self._read_issues_payload()
        rows = payload.get("issues", [])
        if not isinstance(rows, list):
            rows = []
        item = record.to_dict()
        issue_id = str(item.get("id", "") or "").strip()
        if not issue_id:
            return self.add_issue(record)
        replaced = False
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            if str(row.get("id", "") or "").strip() == issue_id:
                created_at = str(row.get("created_at", "") or "").strip()
                item["created_at"] = created_at or item.get("created_at") or now_iso()
                item["updated_at"] = now_iso()
                rows[i] = item
                replaced = True
                break
        if not replaced:
            return self.add_issue(record)
        payload["issues"] = rows
        payload["updated_at"] = now_iso()
        _save_json_atomic(self._issues_path, payload)
        return IssueRecord.from_dict(item)

    def close_issue(self, issue_id: str) -> bool:
        issue = self.get_issue(issue_id)
        if issue is None:
            return False
        issue.status = "zamkniete"
        issue.updated_at = now_iso()
        self.update_issue(issue)
        return True

    def assign_issue(self, issue_id: str, owner: str) -> bool:
        issue = self.get_issue(issue_id)
        if issue is None:
            return False
        issue.owner = str(owner or "").strip()
        issue.updated_at = now_iso()
        self.update_issue(issue)
        return True

    def filter_issues(
        self,
        *,
        text: str = "",
        status: str = "",
        priority: str = "",
        area: str = "",
        issue_type: str = "",
        project: str = "",
        client: str = "",
        owner: str = "",
        overdue_only: bool = False,
        blocks_invoice: bool = False,
        blocks_production: bool = False,
        blocks_installation: bool = False,
        active_only: bool = False,
        role: str = "",
        worker_name: str = "",
    ) -> list[IssueRecord]:
        q_text = str(text or "").strip().lower()
        q_status = str(status or "").strip().lower()
        q_priority = str(priority or "").strip().lower()
        q_area = str(area or "").strip().lower()
        q_type = str(issue_type or "").strip().lower()
        q_project = str(project or "").strip().lower()
        q_client = str(client or "").strip().lower()
        q_owner = str(owner or "").strip().lower()

        out: list[IssueRecord] = []
        for issue in self.list_issues():
            if role and not issue_visible_for_role(issue, role, worker_name):
                continue
            if active_only and not issue.is_active():
                continue
            if overdue_only and not issue.is_overdue():
                continue
            if blocks_invoice and not issue.blocks_invoice:
                continue
            if blocks_production and not issue.blocks_production:
                continue
            if blocks_installation and not issue.blocks_installation:
                continue
            if q_status and q_status != "all" and issue.status != q_status:
                continue
            if q_priority and q_priority != "all" and issue.priority_manual != q_priority:
                continue
            if q_area and q_area != "all" and issue.area != q_area:
                continue
            if q_type and q_type != "all" and issue.issue_type != q_type:
                continue
            if q_project and q_project not in issue.project_name.lower():
                continue
            if q_client and q_client not in issue.client_name.lower():
                continue
            if q_owner and q_owner not in issue.owner.lower():
                continue
            if q_text:
                hay = " ".join(
                    [
                        issue.id,
                        issue.title,
                        issue.description,
                        issue.project_name,
                        issue.client_name,
                        issue.owner,
                        issue.notes,
                        " ".join(issue.tags),
                    ]
                ).lower()
                if q_text not in hay:
                    continue
            out.append(issue)
        return out

    def get_issue_kpis(self, role: str = "", worker_name: str = "") -> dict[str, int]:
        issues = self.filter_issues(role=role, worker_name=worker_name)
        return {
            "otwarte": sum(1 for x in issues if x.is_active()),
            "krytyczne": sum(1 for x in issues if x.priority_manual == "krytyczny" and x.is_active()),
            "po_terminie": sum(1 for x in issues if x.is_overdue()),
            "blokuje_fakture": sum(1 for x in issues if x.blocks_invoice and x.is_active()),
            "blokuje_produkcje": sum(1 for x in issues if x.blocks_production and x.is_active()),
            "blokuje_montaz": sum(1 for x in issues if x.blocks_installation and x.is_active()),
            "reklamacje": sum(1 for x in issues if x.issue_type == "reklamacja" and x.is_active()),
            "do_decyzji": sum(1 for x in issues if x.status == "do_decyzji"),
        }

    def compute_priority_score(self, issue: IssueRecord) -> float:
        score = 0.0
        tags = {x.lower() for x in issue.tags}
        if issue.blocks_invoice or issue.estimated_revenue_unlock > 0:
            score += 50.0
        if issue.is_overdue():
            score += 40.0
        if issue.blocks_invoice and issue.blocks_production and issue.blocks_installation:
            score += 35.0
        if issue.issue_type == "reklamacja" or "reklamacja" in tags:
            score += 25.0
        if 0 < int(issue.estimated_time_minutes or 0) < 60:
            score += 20.0
        if "po_drodze" in tags:
            score += 20.0
        if float(issue.estimated_cost or 0.0) <= 200.0:
            score += 15.0
        if "klient_dlugo_czeka" in tags:
            score += 15.0
        if issue.issue_type == "brak_materialu" or "brak_materialu" in tags:
            score -= 20.0
        if "daleki_wyjazd" in tags:
            score -= 15.0
        if not issue.blocks_invoice and not issue.blocks_production and not issue.blocks_installation and issue.estimated_revenue_unlock <= 0:
            score -= 10.0
        return score

    def list_priority_candidates(
        self,
        *,
        role: str = "",
        worker_name: str = "",
        text: str = "",
        status: str = "",
        area: str = "",
    ) -> list[dict[str, Any]]:
        issues = self.filter_issues(
            text=text,
            status=status,
            area=area,
            active_only=True,
            role=role,
            worker_name=worker_name,
        )
        out: list[dict[str, Any]] = []
        for issue in issues:
            score = self.compute_priority_score(issue)
            out.append(
                {
                    "issue": issue,
                    "score": score,
                    "quick_close": issue.is_quick_close_candidate(),
                    "overdue": issue.is_overdue(),
                }
            )
        out.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
        return out

    def list_routes(self) -> list[RouteTaskRecord]:
        payload = self._read_routes_payload()
        out: list[RouteTaskRecord] = []
        for row in payload.get("routes", []):
            if isinstance(row, dict):
                out.append(RouteTaskRecord.from_dict(row))
        out.sort(key=lambda x: (x.planned_date, x.route_group, -x.route_score))
        return out

    def get_route_task(self, route_id: str) -> RouteTaskRecord | None:
        route_id_norm = str(route_id or "").strip()
        if not route_id_norm:
            return None
        for row in self.list_routes():
            if row.id == route_id_norm:
                return row
        return None

    def add_route_task(self, record: RouteTaskRecord) -> RouteTaskRecord:
        payload = self._read_routes_payload()
        rows = payload.get("routes", [])
        if not isinstance(rows, list):
            rows = []
        item = record.to_dict()
        item["created_at"] = item.get("created_at") or now_iso()
        item["updated_at"] = now_iso()
        rows.append(item)
        payload["routes"] = rows
        payload["updated_at"] = now_iso()
        _save_json_atomic(self._routes_path, payload)
        return RouteTaskRecord.from_dict(item)

    def update_route_task(self, record: RouteTaskRecord) -> RouteTaskRecord:
        payload = self._read_routes_payload()
        rows = payload.get("routes", [])
        if not isinstance(rows, list):
            rows = []
        item = record.to_dict()
        route_id = str(item.get("id", "") or "").strip()
        if not route_id:
            return self.add_route_task(record)
        replaced = False
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            if str(row.get("id", "") or "").strip() == route_id:
                created_at = str(row.get("created_at", "") or "").strip()
                item["created_at"] = created_at or item.get("created_at") or now_iso()
                item["updated_at"] = now_iso()
                rows[i] = item
                replaced = True
                break
        if not replaced:
            return self.add_route_task(record)
        payload["routes"] = rows
        payload["updated_at"] = now_iso()
        _save_json_atomic(self._routes_path, payload)
        return RouteTaskRecord.from_dict(item)

    def filter_routes(
        self,
        *,
        planned_date: str = "",
        crew: str = "",
        route_group: str = "",
        city: str = "",
        status: str = "",
        text: str = "",
        role: str = "",
        worker_name: str = "",
    ) -> list[RouteTaskRecord]:
        q_date = str(planned_date or "").strip()
        q_crew = str(crew or "").strip().lower()
        q_group = str(route_group or "").strip().lower()
        q_city = str(city or "").strip().lower()
        q_status = str(status or "").strip().lower()
        q_text = str(text or "").strip().lower()

        out: list[RouteTaskRecord] = []
        for row in self.list_routes():
            if role and not route_visible_for_role(row, role, worker_name):
                continue
            if q_date and row.planned_date != q_date:
                continue
            if q_crew and q_crew not in row.crew.lower():
                continue
            if q_group and q_group not in row.route_group.lower():
                continue
            if q_city and q_city not in row.city.lower():
                continue
            if q_status and q_status != "all" and row.status != q_status:
                continue
            if q_text:
                hay = " ".join(
                    [
                        row.id,
                        row.project_name,
                        row.client_name,
                        row.city,
                        row.address,
                        row.task_type,
                        row.notes,
                    ]
                ).lower()
                if q_text not in hay:
                    continue
            out.append(row)
        out.sort(key=lambda x: (x.planned_date, x.route_group, -x.route_score))
        return out

    def group_routes_by_group(
        self,
        *,
        planned_date: str = "",
        crew: str = "",
        city: str = "",
        role: str = "",
        worker_name: str = "",
    ) -> dict[str, list[RouteTaskRecord]]:
        rows = self.filter_routes(
            planned_date=planned_date,
            crew=crew,
            city=city,
            role=role,
            worker_name=worker_name,
        )
        grouped: dict[str, list[RouteTaskRecord]] = defaultdict(list)
        for row in rows:
            key = row.route_group or f"{row.planned_date}|{row.city}|{row.crew}"
            grouped[key].append(row)
        return dict(grouped)

    def create_route_task_from_issue(
        self,
        issue_id: str,
        planned_date: str,
        crew: str,
        route_group: str = "",
    ) -> RouteTaskRecord | None:
        issue = self.get_issue(issue_id)
        if issue is None:
            return None
        task = RouteTaskRecord(
            issue_id=issue.id,
            task_type=issue.issue_type,
            project_name=issue.project_name,
            client_name=issue.client_name,
            city=issue.city,
            address=issue.address,
            planned_date=str(planned_date or date.today().strftime("%Y-%m-%d")).strip(),
            crew=str(crew or issue.owner).strip(),
            status="planowane",
            estimated_time_minutes=int(issue.estimated_time_minutes or 0),
            route_group=str(route_group or "").strip(),
            route_score=self.compute_priority_score(issue),
            notes=(issue.title or issue.description)[:250],
        )
        return self.add_route_task(task)

    def list_fulfillments(self) -> list[FulfillmentRecord]:
        payload = self._read_fulfillment_payload()
        return [FulfillmentRecord.from_dict(row) for row in payload["fulfillments"] if isinstance(row, dict)]

    def get_fulfillment(self, project_name: str) -> FulfillmentRecord | None:
        return next((f for f in self.list_fulfillments() if f.project_name == project_name), None)

    def update_fulfillment(self, record: FulfillmentRecord) -> None:
        payload = self._read_fulfillment_payload()
        rows = payload["fulfillments"]
        idx = next((i for i, row in enumerate(rows) if isinstance(row, dict) and row.get("project_name") == record.project_name), -1)
        if idx >= 0:
            rows[idx] = record.to_dict()
        else:
            rows.append(record.to_dict())
        _save_json_atomic(self._fulfillment_path, payload)
