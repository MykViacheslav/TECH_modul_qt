from src.core.visit_history_store import VisitHistoryRecord, VisitHistoryStore


def test_visit_history_store_create_and_crud(tmp_path):
    store = VisitHistoryStore(data_dir=tmp_path)
    assert (tmp_path / "visit_history.json").exists()
    assert store.list_records() == []

    rec = VisitHistoryRecord(point_id="route::1", visit_date="2026-04-11", crew="Ekipa A", work_done="Montaż")
    saved = store.add_record(rec)
    assert saved.id
    assert store.get_record(saved.id) is not None

    saved.work_remaining = "Regulacja"
    store.update_record(saved)
    row = store.get_record(saved.id)
    assert row is not None
    assert row.work_remaining == "Regulacja"

    store.delete_record(saved.id)
    assert store.get_record(saved.id) is None


def test_visit_history_list_for_point_sorted_desc(tmp_path):
    store = VisitHistoryStore(data_dir=tmp_path)
    store.add_record(VisitHistoryRecord(point_id="route::A", visit_date="2026-04-10", crew="E1"))
    store.add_record(VisitHistoryRecord(point_id="route::A", visit_date="2026-04-12", crew="E1"))
    rows = store.list_for_point("route::A")
    assert len(rows) == 2
    assert rows[0].visit_date >= rows[1].visit_date


def test_visit_history_append_finance_result(tmp_path):
    store = VisitHistoryStore(data_dir=tmp_path)
    rec = store.add_record(VisitHistoryRecord(point_id="route::F1", visit_date="2026-04-11"))
    out = store.append_finance_result(
        point_id="route::F1",
        finance_result="gotowe_do_fakturowania",
        payment_unlocked_amount=1234.5,
        ready_to_invoice=True,
        requires_settlement=False,
        requires_confirmation=False,
        notes="OK do faktury",
    )
    assert out.finance_result == "gotowe_do_fakturowania"
    assert out.ready_to_invoice is True
    assert abs(out.payment_unlocked_amount - 1234.5) < 0.001
