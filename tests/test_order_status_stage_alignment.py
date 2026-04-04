def test_tab_bazy_order_status_items_include_extended_pipeline_statuses():
    from src.tabs.bazy.tab_bazy import ORDER_STATUS_ITEMS

    assert "Wycena gotowa" in ORDER_STATUS_ITEMS
    assert "Zaakceptowane" in ORDER_STATUS_ITEMS
    assert "Oczekiwanie na klienta" in ORDER_STATUS_ITEMS
    assert "Zakup materialow" in ORDER_STATUS_ITEMS
    assert "Wstrzymane" in ORDER_STATUS_ITEMS
    assert "Lakiernia" in ORDER_STATUS_ITEMS
    assert "Poprawki" in ORDER_STATUS_ITEMS
    assert "Gotowe" in ORDER_STATUS_ITEMS
    assert "Zamkniete" in ORDER_STATUS_ITEMS
    assert "Anulowane" in ORDER_STATUS_ITEMS


def test_order_calendar_sync_stage_index_supports_new_statuses():
    from src.services.order_calendar_sync import OrderCalendarSync

    idx_wycena = OrderCalendarSync._get_stage_index("Wycena")
    idx_wycena_szybka = OrderCalendarSync._get_stage_index("Wycena szybka")
    idx_wait_client = OrderCalendarSync._get_stage_index("Oczekiwanie na klienta")
    idx_hold = OrderCalendarSync._get_stage_index("Wstrzymane")
    idx_gotowe = OrderCalendarSync._get_stage_index("Gotowe")
    idx_cancelled = OrderCalendarSync._get_stage_index("Anulowane")
    idx_zakonczone = OrderCalendarSync._get_stage_index("Zakonczone")

    assert idx_wycena >= 0
    assert idx_wycena_szybka > idx_wycena
    assert idx_wait_client > idx_wycena_szybka
    assert idx_hold > idx_wait_client
    assert idx_gotowe >= 0
    assert idx_cancelled > idx_gotowe
    assert idx_zakonczone > idx_gotowe
