from datetime import date

from src.core.finance_operations_followup_history_store import FinanceOperationsFollowupHistoryStore
from src.core.finance_operations_followup_store import FinanceOperationsFollowupStore


def test_followup_store_creates_missing_file(tmp_path):
    path = tmp_path / "finance_operations_followup.json"
    store = FinanceOperationsFollowupStore(path=path)
    assert path.exists()
    assert store.list_records() == []


def test_followup_store_upsert_and_markers(tmp_path):
    store = FinanceOperationsFollowupStore(path=tmp_path / "finance_operations_followup.json")
    rec = store.upsert_record("pt-1", "nowe", "start", "biuro")
    assert rec.get("point_id") == "pt-1"
    assert store.get_record("pt-1") is not None

    sent = store.mark_sent_to_invoicing("pt-1", note="faktura", updated_by="biuro")
    assert sent.get("office_status") == "przekazane_do_fakturowania"
    assert bool(sent.get("sent_to_invoicing")) is True
    assert sent.get("invoice_status") == "przekazane_do_fakturowania"

    invoiced = store.mark_invoiced(
        "pt-1",
        invoice_number="FV/1/04/2026",
        invoice_date="2026-04-11",
        linked_invoice_id="inv-123",
        linked_invoice_source="manual",
        note="wystawiona",
        updated_by="biuro",
    )
    assert invoiced.get("office_status") == "zafakturowane"
    assert invoiced.get("invoice_status") == "zafakturowane"
    assert invoiced.get("invoice_number") == "FV/1/04/2026"
    assert invoiced.get("invoice_date") == "2026-04-11"

    settled = store.mark_settled("pt-1", note="rozliczone", updated_by="biuro")
    assert settled.get("office_status") == "rozliczone"
    assert bool(settled.get("settled")) is True

    closed = store.mark_office_closed("pt-1", note="koniec", updated_by="biuro")
    assert closed.get("office_status") == "zamkniete_biurowo"
    assert bool(closed.get("office_closed")) is True


def test_followup_store_payment_and_financial_close(tmp_path):
    history = FinanceOperationsFollowupHistoryStore(path=tmp_path / "finance_operations_followup_history.json")
    store = FinanceOperationsFollowupStore(
        path=tmp_path / "finance_operations_followup.json",
        history_store=history,
    )
    invoiced = store.mark_invoiced(
        "pt-pay-1",
        invoice_number="FV/11/2026",
        invoice_date="2026-04-11",
        note="do zaplaty",
        updated_by="biuro",
    )
    assert invoiced.get("office_status") == "zafakturowane"
    assert invoiced.get("payment_status") == "oczekuje_na_platnosc"

    paid = store.mark_paid(
        "pt-pay-1",
        paid_amount=1234.56,
        payment_date="2026-04-12",
        payment_method="przelew",
        note="oplacone calkowicie",
        updated_by="biuro",
    )
    assert paid.get("office_status") == "oplacone"
    assert paid.get("payment_status") == "oplacone"
    assert float(paid.get("paid_amount", 0.0)) == 1234.56
    assert paid.get("payment_date") == "2026-04-12"
    assert paid.get("payment_method") == "przelew"
    assert paid.get("payment_note") == "oplacone calkowicie"

    fin_closed = store.mark_financially_closed("pt-pay-1", note="zamkniete", updated_by="biuro")
    assert fin_closed.get("office_status") == "domkniete_finansowo"
    assert bool(fin_closed.get("financially_closed")) is True
    hist = history.list_for_point("pt-pay-1")
    assert any(str(x.get("action_type")) == "mark_invoiced" for x in hist)
    assert any(str(x.get("action_type")) == "mark_paid" for x in hist)
    assert any(str(x.get("action_type")) == "mark_financially_closed" for x in hist)


def test_followup_store_logs_sent_and_note_change(tmp_path):
    history = FinanceOperationsFollowupHistoryStore(path=tmp_path / "finance_operations_followup_history.json")
    store = FinanceOperationsFollowupStore(
        path=tmp_path / "finance_operations_followup.json",
        history_store=history,
    )
    store.mark_sent_to_invoicing("pt-log-1", note="do faktury", updated_by="biuro")
    store.upsert_record("pt-log-1", "przekazane_do_fakturowania", office_note="zmiana notatki", updated_by="biuro")
    hist = history.list_for_point("pt-log-1")
    assert any(str(x.get("action_type")) == "mark_sent_to_invoicing" for x in hist)
    assert any(str(x.get("action_type")) == "save_office_note" for x in hist)


def test_followup_store_merge_with_operations_rows(tmp_path):
    store = FinanceOperationsFollowupStore(path=tmp_path / "finance_operations_followup.json")
    store.mark_paid(
        "pt-2",
        paid_amount=99.99,
        payment_date="2026-04-13",
        payment_method="gotowka",
        note="zaplacone",
        updated_by="A",
    )
    rows = [
        {"point_id": "pt-1", "project_name": "P1"},
        {"point_id": "pt-2", "project_name": "P2"},
    ]
    merged = store.merge_with_operations_rows(rows)
    assert len(merged) == 2
    by_id = {str(x.get("point_id")): x for x in merged}
    assert by_id["pt-1"].get("office_status") == "nowe"
    assert by_id["pt-2"].get("office_status") == "oplacone"
    assert str(by_id["pt-2"].get("office_note")) == "zaplacone"
    assert by_id["pt-2"].get("payment_status") == "oplacone"
    assert float(by_id["pt-2"].get("paid_amount", 0.0)) == 99.99
    assert by_id["pt-2"].get("payment_date") == "2026-04-13"
    assert by_id["pt-2"].get("payment_method") == "gotowka"


def test_followup_store_build_office_queue_and_priority(tmp_path):
    store = FinanceOperationsFollowupStore(path=tmp_path / "finance_operations_followup.json")
    rows = [
        {
            "point_id": "pt-q-1",
            "office_status": "nowe",
            "project_name": "A",
            "ready_to_invoice": False,
            "requires_settlement": False,
            "requires_confirmation": False,
            "estimated_payment_unlock": 0.0,
            "blocks_payment": False,
            "last_visit_at": "2026-04-01",
        },
        {
            "point_id": "pt-q-2",
            "office_status": "przekazane_do_fakturowania",
            "project_name": "B",
            "ready_to_invoice": True,
            "requires_settlement": False,
            "requires_confirmation": False,
            "estimated_payment_unlock": 8000.0,
            "blocks_payment": True,
            "last_visit_at": "2026-03-20",
        },
    ]
    queue = store.build_office_queue(rows, today=date(2026, 4, 11))
    assert len(queue) == 2
    assert queue[0].get("point_id") == "pt-q-2"
    assert queue[0].get("office_priority") in {"krytyczny", "wysoki"}
    assert int(queue[0].get("days_since_last_activity", 0)) >= 20
    assert bool(queue[0].get("needs_attention_today")) is True
    assert bool(queue[0].get("is_stale")) is True


def test_followup_store_financially_closed_not_stale(tmp_path):
    store = FinanceOperationsFollowupStore(path=tmp_path / "finance_operations_followup.json")
    rows = [
        {
            "point_id": "pt-q-closed",
            "office_status": "domkniete_finansowo",
            "financially_closed": True,
            "project_name": "Closed",
            "estimated_payment_unlock": 100.0,
            "blocks_payment": True,
            "last_visit_at": "2026-03-01",
        }
    ]
    queue = store.build_office_queue(rows, today=date(2026, 4, 11))
    assert len(queue) == 1
    assert bool(queue[0].get("is_stale")) is False


def test_followup_store_next_action_and_snooze(tmp_path):
    history = FinanceOperationsFollowupHistoryStore(path=tmp_path / "finance_operations_followup_history.json")
    store = FinanceOperationsFollowupStore(
        path=tmp_path / "finance_operations_followup.json",
        history_store=history,
    )
    store.upsert_record("pt-a-1", "nowe", updated_by="biuro")
    rec = store.set_next_action(
        point_id="pt-a-1",
        next_action_date="2026-04-11",
        next_action_type="kontakt_z_klientem",
        next_action_note="telefon",
        needs_contact=True,
        needs_check=False,
        updated_by="biuro",
    )
    assert rec.get("next_action_date") == "2026-04-11"
    assert rec.get("next_action_type") == "kontakt_z_klientem"
    assert rec.get("next_action_note") == "telefon"
    assert bool(rec.get("needs_contact")) is True

    rec = store.snooze_record("pt-a-1", snoozed_until="2026-04-15", note="czekamy", updated_by="biuro")
    assert rec.get("snoozed_until") == "2026-04-15"
    rec = store.clear_snooze("pt-a-1", updated_by="biuro")
    assert rec.get("snoozed_until") == ""

    hist = history.list_for_point("pt-a-1")
    assert any(str(x.get("action_type")) == "set_next_action" for x in hist)
    assert any(str(x.get("action_type")) == "snooze_record" for x in hist)
    assert any(str(x.get("action_type")) == "clear_snooze" for x in hist)


def test_followup_store_compute_action_flags(tmp_path):
    store = FinanceOperationsFollowupStore(path=tmp_path / "finance_operations_followup.json")
    row = {
        "office_status": "zafakturowane",
        "financially_closed": False,
        "next_action_date": "2026-04-10",
        "next_action_type": "sprawdzenie_platnosci",
        "snoozed_until": "",
    }
    flags = store.compute_action_flags(row, today=date(2026, 4, 11))
    assert bool(flags.get("action_due_today")) is True
    assert bool(flags.get("action_overdue")) is True
    assert bool(flags.get("is_snoozed")) is False

    row2 = {
        "office_status": "zafakturowane",
        "financially_closed": False,
        "next_action_date": "2026-04-11",
        "next_action_type": "sprawdzenie_platnosci",
        "snoozed_until": "2026-04-12",
    }
    flags2 = store.compute_action_flags(row2, today=date(2026, 4, 11))
    assert bool(flags2.get("is_snoozed")) is True
    assert bool(flags2.get("action_due_today")) is False


def test_followup_store_closed_not_due_today(tmp_path):
    store = FinanceOperationsFollowupStore(path=tmp_path / "finance_operations_followup.json")
    rows = [
        {
            "point_id": "pt-a-closed",
            "office_status": "domkniete_finansowo",
            "financially_closed": True,
            "next_action_date": "2026-04-01",
            "next_action_type": "powrot_do_tematu",
            "snoozed_until": "",
            "last_visit_at": "2026-03-01",
        }
    ]
    queue = store.build_office_queue(rows, today=date(2026, 4, 11))
    assert len(queue) == 1
    assert bool(queue[0].get("action_due_today")) is False
    assert bool(queue[0].get("action_overdue")) is False


def test_followup_store_agenda_buckets(tmp_path):
    store = FinanceOperationsFollowupStore(path=tmp_path / "finance_operations_followup.json")
    rows = [
        {
            "point_id": "pt-ag-today",
            "office_status": "nowe",
            "financially_closed": False,
            "next_action_date": "2026-04-11",
            "next_action_type": "kontakt_z_klientem",
            "snoozed_until": "",
            "last_visit_at": "2026-04-10",
            "estimated_payment_unlock": 100.0,
        },
        {
            "point_id": "pt-ag-tomorrow",
            "office_status": "zafakturowane",
            "financially_closed": False,
            "next_action_date": "2026-04-12",
            "next_action_type": "sprawdzenie_platnosci",
            "snoozed_until": "",
            "last_visit_at": "2026-04-10",
            "estimated_payment_unlock": 200.0,
        },
        {
            "point_id": "pt-ag-overdue",
            "office_status": "zafakturowane",
            "financially_closed": False,
            "next_action_date": "2026-04-09",
            "next_action_type": "sprawdzenie_faktury",
            "snoozed_until": "",
            "last_visit_at": "2026-04-01",
            "estimated_payment_unlock": 300.0,
        },
        {
            "point_id": "pt-ag-snoozed",
            "office_status": "nowe",
            "financially_closed": False,
            "next_action_date": "2026-04-11",
            "next_action_type": "powrot_do_tematu",
            "snoozed_until": "2026-04-13",
            "last_visit_at": "2026-04-10",
            "estimated_payment_unlock": 400.0,
        },
    ]
    buckets = store.get_agenda_buckets(rows=rows, today=date(2026, 4, 11))
    assert any(str(x.get("point_id")) == "pt-ag-today" for x in buckets["today"])
    assert any(str(x.get("point_id")) == "pt-ag-tomorrow" for x in buckets["tomorrow"])
    assert any(str(x.get("point_id")) == "pt-ag-overdue" for x in buckets["overdue"])
    assert any(str(x.get("point_id")) == "pt-ag-snoozed" for x in buckets["snoozed"])


def test_followup_store_snooze_end_returns_to_active_bucket(tmp_path):
    store = FinanceOperationsFollowupStore(path=tmp_path / "finance_operations_followup.json")
    rows = [
        {
            "point_id": "pt-ag-back",
            "office_status": "nowe",
            "financially_closed": False,
            "next_action_date": "2026-04-11",
            "next_action_type": "powrot_do_tematu",
            "snoozed_until": "2026-04-11",
            "last_visit_at": "2026-04-10",
            "estimated_payment_unlock": 100.0,
        }
    ]
    buckets = store.get_agenda_buckets(rows=rows, today=date(2026, 4, 11))
    assert not any(str(x.get("point_id")) == "pt-ag-back" for x in buckets["snoozed"])
    assert any(str(x.get("point_id")) == "pt-ag-back" for x in buckets["today"])
