from src.core.finance_operations_followup_history_store import FinanceOperationsFollowupHistoryStore


def test_history_store_creates_missing_file(tmp_path):
    path = tmp_path / "finance_operations_followup_history.json"
    store = FinanceOperationsFollowupHistoryStore(path=path)
    assert path.exists()
    assert store.list_records() == []


def test_history_store_append_and_list_for_point(tmp_path):
    store = FinanceOperationsFollowupHistoryStore(path=tmp_path / "finance_operations_followup_history.json")
    rec = store.append_record(
        point_id="pt-h-1",
        action_type="mark_paid",
        created_by="biuro",
        old_office_status="zafakturowane",
        new_office_status="oplacone",
        paid_amount=500.0,
        payment_date="2026-04-12",
        payment_method="przelew",
        note="zaplacone",
    )
    assert rec.get("point_id") == "pt-h-1"
    assert rec.get("action_type") == "mark_paid"
    rows = store.list_for_point("pt-h-1")
    assert len(rows) == 1
    assert rows[0].get("created_by") == "biuro"


def test_history_store_sort_desc_by_created_at(tmp_path):
    store = FinanceOperationsFollowupHistoryStore(path=tmp_path / "finance_operations_followup_history.json")
    store.append_record(point_id="pt-h-2", action_type="save_office_note", note="a")
    store.append_record(point_id="pt-h-2", action_type="save_office_note", note="b")
    rows = store.list_for_point("pt-h-2")
    assert len(rows) == 2
    assert str(rows[0].get("created_at", "")) >= str(rows[1].get("created_at", ""))
