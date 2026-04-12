from datetime import date, timedelta

from src.core.operations_models import IssueRecord
from src.core.operations_store import OperationsStore


def _mk_issue(**kwargs):
    base = IssueRecord(
        title="Brak elementu",
        description="Brakuje prowadnicy",
        area="produkcja",
        issue_type="brak_elementu",
        impact_level="wysoki",
        priority_manual="normalny",
        status="nowe",
        project_name="P-01",
        client_name="Klient A",
        due_date=(date.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
        blocks_invoice=True,
        estimated_cost=120.0,
        estimated_revenue_unlock=900.0,
        estimated_time_minutes=45,
        tags=["po_drodze", "klient_dlugo_czeka"],
    )
    for k, v in kwargs.items():
        setattr(base, k, v)
    return base


def test_store_creates_missing_json(tmp_path):
    store = OperationsStore(
        issues_path=tmp_path / "operations_issues.json",
        routes_path=tmp_path / "operations_routes.json",
    )
    assert (tmp_path / "operations_issues.json").exists()
    assert (tmp_path / "operations_routes.json").exists()
    assert store.list_issues() == []
    assert store.list_routes() == []


def test_add_update_close_issue_and_filters(tmp_path):
    store = OperationsStore(
        issues_path=tmp_path / "operations_issues.json",
        routes_path=tmp_path / "operations_routes.json",
    )
    rec = store.add_issue(_mk_issue())
    assert rec.id
    assert store.get_issue(rec.id) is not None

    rec.owner = "Jan"
    rec.priority_manual = "krytyczny"
    updated = store.update_issue(rec)
    assert updated.owner == "Jan"
    assert updated.priority_manual == "krytyczny"

    filtered = store.filter_issues(owner="Jan", priority="krytyczny", active_only=True)
    assert len(filtered) == 1
    assert filtered[0].id == rec.id

    assert store.close_issue(rec.id) is True
    closed = store.get_issue(rec.id)
    assert closed is not None
    assert closed.status == "zamkniete"


def test_scoring_and_priority_sort_desc(tmp_path):
    store = OperationsStore(
        issues_path=tmp_path / "operations_issues.json",
        routes_path=tmp_path / "operations_routes.json",
    )
    high = store.add_issue(_mk_issue(title="Wysoki"))
    low = store.add_issue(
        _mk_issue(
            title="Niski",
            blocks_invoice=False,
            estimated_revenue_unlock=0,
            estimated_time_minutes=180,
            tags=["daleki_wyjazd"],
            issue_type="inne",
            due_date=(date.today() + timedelta(days=5)).strftime("%Y-%m-%d"),
        )
    )
    score_high = store.compute_priority_score(high)
    score_low = store.compute_priority_score(low)
    assert score_high > score_low

    rows = store.list_priority_candidates()
    assert len(rows) == 2
    assert float(rows[0]["score"]) >= float(rows[1]["score"])


def test_create_route_task_from_issue(tmp_path):
    store = OperationsStore(
        issues_path=tmp_path / "operations_issues.json",
        routes_path=tmp_path / "operations_routes.json",
    )
    rec = store.add_issue(_mk_issue(project_name="Projekt R1", city="Krakow", address="ul. Test 1"))
    route = store.create_route_task_from_issue(rec.id, date.today().strftime("%Y-%m-%d"), "Ekipa A", "KRK-1")
    assert route is not None
    assert route.issue_id == rec.id
    assert route.route_group == "KRK-1"
    assert len(store.list_routes()) == 1
