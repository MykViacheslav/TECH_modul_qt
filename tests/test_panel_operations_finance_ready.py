from datetime import date

from PyQt6.QtWidgets import QApplication

from src.core.finance_operations_followup_history_store import FinanceOperationsFollowupHistoryStore
from src.core.finance_operations_followup_store import FinanceOperationsFollowupStore
from src.tabs.finanse_hub.panel_operations_finance_ready import OperationsFinanceReadyPanel


def test_operations_finance_ready_panel_loads_and_filters():
    app = QApplication.instance() or QApplication([])
    _ = app
    sample_rows = [
        {
            "point_id": "p1",
            "project_name": "Projekt Alfa",
            "client_name": "Klient A",
            "full_address": "Krakow, A 1",
            "visit_status": "zrealizowana",
            "finance_followup_status": "gotowe_do_fakturowania",
            "estimated_payment_unlock": 300.0,
            "ready_to_invoice": True,
            "requires_settlement": False,
            "requires_confirmation": False,
            "blocks_payment": True,
            "last_visit_at": "2026-04-11",
            "last_finance_result": "ok",
            "finance_followup_note": "potwierdzone",
        },
        {
            "point_id": "p2",
            "project_name": "Projekt Beta",
            "client_name": "Klient B",
            "full_address": "Warszawa, B 2",
            "visit_status": "w_toku",
            "finance_followup_status": "wymaga_rozliczenia",
            "estimated_payment_unlock": 0.0,
            "ready_to_invoice": False,
            "requires_settlement": True,
            "requires_confirmation": False,
            "blocks_payment": False,
            "last_visit_at": "2026-04-10",
            "last_finance_result": "w trakcie",
            "finance_followup_note": "",
        },
    ]
    panel = OperationsFinanceReadyPanel(adapter=lambda: sample_rows)
    panel.refresh_data()
    assert panel.tbl.rowCount() == 2
    assert panel.tbl.columnCount() == 23
    assert panel._kpi_widgets["ready"].text() == "1"
    assert panel._kpi_widgets["settlement"].text() == "1"
    assert panel._kpi_widgets["blocking"].text() == "1"
    assert panel._kpi_widgets["office_new"].text() == "2"
    assert panel._kpi_widgets["office_sent"].text() == "0"

    panel.f_project.setText("alfa")
    panel.refresh_data()
    assert panel.tbl.rowCount() == 1


def test_operations_finance_ready_panel_navigate_callback_payload():
    app = QApplication.instance() or QApplication([])
    _ = app
    sample_rows = [
        {
            "point_id": "pt-1",
            "project_name": "Projekt Test",
            "client_name": "Klient Test",
            "full_address": "Krakow 1",
            "visit_status": "zrealizowana",
            "finance_followup_status": "gotowe_do_fakturowania",
            "estimated_payment_unlock": 100.0,
            "ready_to_invoice": True,
            "requires_settlement": False,
            "requires_confirmation": False,
            "blocks_payment": True,
            "last_visit_at": "2026-04-11",
            "last_finance_result": "ok",
            "finance_followup_note": "x",
        }
    ]
    captured = {}

    def _capture(payload):
        captured.update(payload)

    panel = OperationsFinanceReadyPanel(adapter=lambda: sample_rows, on_navigate_to_operations=_capture)
    panel.refresh_data()
    panel.tbl.selectRow(0)
    panel._on_go_ops()
    assert captured.get("point_id") == "pt-1"
    assert captured.get("project_name") == "Projekt Test"
    assert captured.get("client_name") == "Klient Test"
    assert captured.get("target_tab") == "mapa_zlecen"


def test_operations_finance_ready_panel_office_status_actions(tmp_path):
    app = QApplication.instance() or QApplication([])
    _ = app
    sample_rows = [
        {
            "point_id": "pt-office-1",
            "project_name": "Projekt Office",
            "client_name": "Klient Office",
            "full_address": "Krakow 5",
            "visit_status": "zrealizowana",
            "finance_followup_status": "wymaga_rozliczenia",
            "estimated_payment_unlock": 0.0,
            "ready_to_invoice": False,
            "requires_settlement": True,
            "requires_confirmation": False,
            "blocks_payment": False,
            "last_visit_at": "2026-04-11",
            "last_finance_result": "ok",
            "finance_followup_note": "",
        }
    ]
    followup = FinanceOperationsFollowupStore(path=tmp_path / "finance_operations_followup.json")
    panel = OperationsFinanceReadyPanel(adapter=lambda: sample_rows, followup_store=followup)
    panel.set_current_user("Biuro Test", "biuro")
    panel.refresh_data()
    panel.tbl.selectRow(0)

    panel.ed_office_note.setPlainText("Do faktury")
    panel._on_mark_sent_to_invoicing()
    rec = followup.get_record("pt-office-1")
    assert rec is not None
    assert rec.get("office_status") == "przekazane_do_fakturowania"

    panel._on_mark_settled()
    rec = followup.get_record("pt-office-1")
    assert rec is not None
    assert rec.get("office_status") == "rozliczone"

    panel._on_mark_office_closed()
    rec = followup.get_record("pt-office-1")
    assert rec is not None
    assert rec.get("office_status") == "zamkniete_biurowo"

    idx = panel.f_office_status.findData("zamkniete_biurowo")
    assert idx >= 0
    panel.f_office_status.setCurrentIndex(idx)
    panel.refresh_data()
    assert panel.tbl.rowCount() == 1


def test_operations_finance_ready_panel_mark_invoiced_and_filter(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    _ = app
    sample_rows = [
        {
            "point_id": "pt-inv-1",
            "project_name": "Projekt Inv",
            "client_name": "Klient Inv",
            "full_address": "Warszawa 8",
            "visit_status": "zrealizowana",
            "finance_followup_status": "gotowe_do_fakturowania",
            "estimated_payment_unlock": 500.0,
            "ready_to_invoice": True,
            "requires_settlement": False,
            "requires_confirmation": False,
            "blocks_payment": True,
            "last_visit_at": "2026-04-11",
            "last_finance_result": "ok",
            "finance_followup_note": "gotowe",
        }
    ]
    followup = FinanceOperationsFollowupStore(path=tmp_path / "finance_operations_followup.json")
    panel = OperationsFinanceReadyPanel(adapter=lambda: sample_rows, followup_store=followup)
    panel.set_current_user("Biuro Test", "biuro")
    panel.refresh_data()
    panel.tbl.selectRow(0)

    class _FakeDialog:
        class _Code:
            Accepted = 1

        class DialogCode:
            Accepted = 1

        def __init__(self, *_a, **_k):
            self.ed_invoice_number = type("_X", (), {"setText": lambda *_a, **_k: None})()
            self.ed_invoice_date = type("_X", (), {"setText": lambda *_a, **_k: None})()
            self.ed_linked_invoice_id = type("_X", (), {"setText": lambda *_a, **_k: None})()
            self.ed_linked_invoice_source = type("_X", (), {"setText": lambda *_a, **_k: None})()
            self.ed_note = type("_X", (), {"setPlainText": lambda *_a, **_k: None})()

        def exec(self):
            return 1

        def payload(self):
            return {
                "invoice_number": "FV/77/2026",
                "invoice_date": "2026-04-11",
                "linked_invoice_id": "inv-77",
                "linked_invoice_source": "manual",
                "note": "wystawiona",
            }

    monkeypatch.setattr("src.tabs.finanse_hub.panel_operations_finance_ready.MarkInvoicedDialog", _FakeDialog)
    panel._on_mark_invoiced()

    rec = followup.get_record("pt-inv-1")
    assert rec is not None
    assert rec.get("office_status") == "zafakturowane"
    assert rec.get("invoice_number") == "FV/77/2026"
    assert rec.get("invoice_date") == "2026-04-11"

    panel.refresh_data()
    assert panel._kpi_widgets["office_invoiced"].text() == "1"
    idx = panel.f_office_status.findData("zafakturowane")
    assert idx >= 0
    panel.f_office_status.setCurrentIndex(idx)
    panel.refresh_data()
    assert panel.tbl.rowCount() == 1


def test_operations_finance_ready_panel_mark_paid_and_fin_close(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    _ = app
    sample_rows = [
        {
            "point_id": "pt-pay-ui-1",
            "project_name": "Projekt Platnosc",
            "client_name": "Klient Platnosc",
            "full_address": "Lodz 12",
            "visit_status": "zrealizowana",
            "finance_followup_status": "gotowe_do_fakturowania",
            "estimated_payment_unlock": 250.0,
            "ready_to_invoice": True,
            "requires_settlement": False,
            "requires_confirmation": False,
            "blocks_payment": True,
            "last_visit_at": "2026-04-11",
            "last_finance_result": "ok",
            "finance_followup_note": "czeka",
        }
    ]
    followup = FinanceOperationsFollowupStore(path=tmp_path / "finance_operations_followup.json")
    panel = OperationsFinanceReadyPanel(adapter=lambda: sample_rows, followup_store=followup)
    panel.set_current_user("Biuro Test", "biuro")
    panel.refresh_data()
    panel.tbl.selectRow(0)

    class _FakePaidDialog:
        class DialogCode:
            Accepted = 1

        def __init__(self, *_a, **_k):
            pass

        def exec(self):
            return 1

        def payload(self):
            return {
                "paid_amount": 777.77,
                "payment_date": "2026-04-12",
                "payment_method": "przelew",
                "note": "zaplacone",
            }

    monkeypatch.setattr("src.tabs.finanse_hub.panel_operations_finance_ready.MarkPaidDialog", _FakePaidDialog)
    panel._on_mark_paid()

    rec = followup.get_record("pt-pay-ui-1")
    assert rec is not None
    assert rec.get("office_status") == "oplacone"
    assert rec.get("payment_status") == "oplacone"
    assert float(rec.get("paid_amount", 0.0)) == 777.77

    panel.refresh_data()
    assert panel._kpi_widgets["office_paid"].text() == "1"
    idx = panel.f_office_status.findData("oplacone")
    assert idx >= 0
    panel.f_office_status.setCurrentIndex(idx)
    panel.refresh_data()
    assert panel.tbl.rowCount() == 1

    panel._on_mark_financially_closed()
    rec = followup.get_record("pt-pay-ui-1")
    assert rec is not None
    assert rec.get("office_status") == "domkniete_finansowo"
    assert bool(rec.get("financially_closed")) is True

    idx_all = panel.f_office_status.findData("all")
    assert idx_all >= 0
    panel.f_office_status.setCurrentIndex(idx_all)
    panel.refresh_data()
    assert panel._kpi_widgets["office_fin_closed"].text() == "1"


def test_operations_finance_ready_panel_history_refresh(tmp_path):
    app = QApplication.instance() or QApplication([])
    _ = app
    sample_rows = [
        {
            "point_id": "pt-h-ui-1",
            "project_name": "Projekt Historia",
            "client_name": "Klient Historia",
            "full_address": "Gdansk 1",
            "visit_status": "zrealizowana",
            "finance_followup_status": "gotowe_do_fakturowania",
            "estimated_payment_unlock": 100.0,
            "ready_to_invoice": True,
            "requires_settlement": False,
            "requires_confirmation": False,
            "blocks_payment": True,
            "last_visit_at": "2026-04-11",
            "last_finance_result": "ok",
            "finance_followup_note": "",
        }
    ]
    history = FinanceOperationsFollowupHistoryStore(path=tmp_path / "finance_operations_followup_history.json")
    followup = FinanceOperationsFollowupStore(
        path=tmp_path / "finance_operations_followup.json",
        history_store=history,
    )
    panel = OperationsFinanceReadyPanel(adapter=lambda: sample_rows, followup_store=followup)
    panel.set_current_user("Biuro Test", "biuro")
    panel.refresh_data()
    panel.tbl.selectRow(0)
    assert "Brak historii" in panel.txt_history.toPlainText()

    panel.ed_office_note.setPlainText("Do faktury")
    panel._on_mark_sent_to_invoicing()
    panel.refresh_data()
    panel.tbl.selectRow(0)
    text = panel.txt_history.toPlainText()
    assert "Przekazane do fakturowania" in text
    assert "Biuro Test" in text


def test_operations_finance_ready_panel_queue_filters_and_sorting():
    app = QApplication.instance() or QApplication([])
    _ = app
    sample_rows = [
        {
            "point_id": "p-crit",
            "project_name": "Projekt Krytyczny",
            "client_name": "Klient K",
            "full_address": "Poznan 1",
            "visit_status": "zrealizowana",
            "finance_followup_status": "gotowe_do_fakturowania",
            "estimated_payment_unlock": 9000.0,
            "ready_to_invoice": True,
            "requires_settlement": False,
            "requires_confirmation": False,
            "blocks_payment": True,
            "last_visit_at": "2020-01-01",
            "last_finance_result": "ok",
            "finance_followup_note": "",
        },
        {
            "point_id": "p-norm",
            "project_name": "Projekt Normalny",
            "client_name": "Klient N",
            "full_address": "Sopot 2",
            "visit_status": "w_toku",
            "finance_followup_status": "wymaga_rozliczenia",
            "estimated_payment_unlock": 100.0,
            "ready_to_invoice": False,
            "requires_settlement": False,
            "requires_confirmation": False,
            "blocks_payment": False,
            "last_visit_at": date.today().isoformat(),
            "last_finance_result": "ok",
            "finance_followup_note": "",
        },
    ]
    panel = OperationsFinanceReadyPanel(adapter=lambda: sample_rows)
    panel.refresh_data()

    # Domyslne sortowanie: najpierw rekord do reakcji z wyzszym priorytetem.
    assert panel.tbl.rowCount() == 2
    assert panel.tbl.item(0, 0).text() == "Projekt Krytyczny"

    panel.f_stale_only.setChecked(True)
    panel.refresh_data()
    assert panel.tbl.rowCount() == 1
    assert panel.tbl.item(0, 0).text() == "Projekt Krytyczny"

    panel.f_stale_only.setChecked(False)
    idx = panel.f_priority.findData("krytyczny")
    assert idx >= 0
    panel.f_priority.setCurrentIndex(idx)
    panel.refresh_data()
    assert panel.tbl.rowCount() == 1
    assert panel.tbl.item(0, 0).text() == "Projekt Krytyczny"


def test_operations_finance_ready_panel_next_action_and_snooze_filters(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    _ = app
    sample_rows = [
        {
            "point_id": "pt-a-ui-1",
            "project_name": "Projekt Akcja",
            "client_name": "Klient Akcja",
            "full_address": "Wroclaw 7",
            "visit_status": "zrealizowana",
            "finance_followup_status": "gotowe_do_fakturowania",
            "estimated_payment_unlock": 400.0,
            "ready_to_invoice": True,
            "requires_settlement": False,
            "requires_confirmation": False,
            "blocks_payment": True,
            "last_visit_at": "2026-04-11",
            "last_finance_result": "ok",
            "finance_followup_note": "",
        }
    ]
    followup = FinanceOperationsFollowupStore(path=tmp_path / "finance_operations_followup.json")
    panel = OperationsFinanceReadyPanel(adapter=lambda: sample_rows, followup_store=followup)
    panel.set_current_user("Biuro Test", "biuro")
    panel.refresh_data()
    panel.tbl.selectRow(0)

    class _FakeNextActionDialog:
        class DialogCode:
            Accepted = 1

        def __init__(self, *_a, **_k):
            pass

        def exec(self):
            return 1

        def payload(self):
            return {
                "next_action_type": "kontakt_z_klientem",
                "next_action_date": date.today().isoformat(),
                "next_action_note": "telefon",
                "needs_contact": True,
                "needs_check": False,
            }

    class _FakeSnoozeDialog:
        class DialogCode:
            Accepted = 1

        def __init__(self, *_a, **_k):
            pass

        def exec(self):
            return 1

        def payload(self):
            return {"snoozed_until": "2099-01-01", "note": "odlozone"}

    monkeypatch.setattr("src.tabs.finanse_hub.panel_operations_finance_ready.NextActionDialog", _FakeNextActionDialog)
    monkeypatch.setattr("src.tabs.finanse_hub.panel_operations_finance_ready.SnoozeRecordDialog", _FakeSnoozeDialog)

    panel._on_set_next_action()
    rec = followup.get_record("pt-a-ui-1")
    assert rec is not None
    assert rec.get("next_action_type") == "kontakt_z_klientem"

    panel.refresh_data()
    assert panel._kpi_widgets["action_due_today"].text() == "1"
    panel.f_action_due_today.setChecked(True)
    panel.refresh_data()
    assert panel.tbl.rowCount() == 1

    panel.f_action_due_today.setChecked(False)
    panel._on_snooze_record()
    rec = followup.get_record("pt-a-ui-1")
    assert rec is not None
    assert rec.get("snoozed_until") == "2099-01-01"

    panel.refresh_data()
    assert panel._kpi_widgets["action_snoozed"].text() == "1"
    panel.f_snoozed_only.setChecked(True)
    panel.refresh_data()
    assert panel.tbl.rowCount() == 1

    panel._on_clear_snooze()
    rec = followup.get_record("pt-a-ui-1")
    assert rec is not None
    assert rec.get("snoozed_until") == ""


def test_operations_finance_ready_panel_agenda_view_and_sections(tmp_path):
    app = QApplication.instance() or QApplication([])
    _ = app
    sample_rows = [
        {
            "point_id": "pt-ag-ui-today",
            "project_name": "Projekt Today",
            "client_name": "Klient T",
            "full_address": "Krakow 1",
            "visit_status": "zrealizowana",
            "finance_followup_status": "gotowe_do_fakturowania",
            "estimated_payment_unlock": 500.0,
            "ready_to_invoice": True,
            "requires_settlement": False,
            "requires_confirmation": False,
            "blocks_payment": True,
            "last_visit_at": "2026-04-10",
            "last_finance_result": "ok",
            "finance_followup_note": "",
        },
        {
            "point_id": "pt-ag-ui-overdue",
            "project_name": "Projekt Overdue",
            "client_name": "Klient O",
            "full_address": "Warszawa 2",
            "visit_status": "zrealizowana",
            "finance_followup_status": "wymaga_rozliczenia",
            "estimated_payment_unlock": 300.0,
            "ready_to_invoice": False,
            "requires_settlement": True,
            "requires_confirmation": False,
            "blocks_payment": False,
            "last_visit_at": "2026-04-01",
            "last_finance_result": "ok",
            "finance_followup_note": "",
        },
    ]
    followup = FinanceOperationsFollowupStore(path=tmp_path / "finance_operations_followup.json")
    followup.set_next_action("pt-ag-ui-today", next_action_date=date.today().isoformat(), next_action_type="kontakt_z_klientem")
    past_day = date.fromordinal(date.today().toordinal() - 1).isoformat()
    followup.set_next_action("pt-ag-ui-overdue", next_action_date=past_day, next_action_type="sprawdzenie_platnosci")

    panel = OperationsFinanceReadyPanel(adapter=lambda: sample_rows, followup_store=followup)
    panel.refresh_data()
    idx_agenda = panel.view_mode.findData("agenda")
    assert idx_agenda >= 0
    panel.view_mode.setCurrentIndex(idx_agenda)
    assert panel.left_views.currentIndex() == 1

    # Buckety agendy istnieja
    assert panel.agenda_tabs.count() == 4
    assert panel.agenda_tabs.tabText(0) == "Na dzis"
    assert panel.agenda_tabs.tabText(1) == "Na jutro"
    assert panel.agenda_tabs.tabText(2) == "Po terminie"
    assert panel.agenda_tabs.tabText(3) == "Odlozone"

    # Klik rekordu z agendy pokazuje szczegoly.
    today_tbl = panel._agenda_tables["today"]
    if today_tbl.rowCount() > 0:
        today_tbl.selectRow(0)
        panel._on_selection_changed()
        assert "Projekt:" in panel.txt_details.toPlainText()


def test_operations_finance_ready_panel_daily_report_and_exports(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    _ = app
    sample_rows = [
        {
            "point_id": "pt-r-1",
            "project_name": "Projekt Raport",
            "client_name": "Klient Raport",
            "full_address": "Krakow 4",
            "visit_status": "zrealizowana",
            "finance_followup_status": "gotowe_do_fakturowania",
            "estimated_payment_unlock": 1200.0,
            "ready_to_invoice": True,
            "requires_settlement": False,
            "requires_confirmation": False,
            "blocks_payment": True,
            "last_visit_at": "2026-04-11",
            "last_finance_result": "ok",
            "finance_followup_note": "pilne",
        }
    ]
    panel = OperationsFinanceReadyPanel(adapter=lambda: sample_rows)
    panel.refresh_data()
    assert panel.btn_report_refresh.text() == "Odswiez raport"
    assert "Na dzis:" in panel.txt_daily_summary.toPlainText()

    csv_path = tmp_path / "report.csv"
    html_path = tmp_path / "report.html"
    panel._export_daily_report_csv(str(csv_path))
    panel._export_daily_report_html(str(html_path))
    assert csv_path.exists()
    assert html_path.exists()
    assert "Raport dnia" in csv_path.read_text(encoding="utf-8")
    assert "<html>" in html_path.read_text(encoding="utf-8")

    panel._on_copy_daily_summary()
    assert "Na dzis:" in QApplication.clipboard().text()

    class _FakePreview:
        def __init__(self, *_a, **_k):
            pass

        def exec(self):
            return 0

    monkeypatch.setattr("src.tabs.finanse_hub.panel_operations_finance_ready.DailyReportPreviewDialog", _FakePreview)
    panel._on_preview_daily_report()
