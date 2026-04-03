from __future__ import annotations


def wire_cross_tab_signals(window) -> None:
    tab_start = window._tabs_by_title.get("Start")
    tab_nowe_zamowienie = window._tabs_by_title.get("Nowe zamowienie")
    tab_modul = window._tabs_by_title.get("Modul")
    tab_ustawienia = window._tabs_by_title.get("Ustawienia")
    tab_komplet = window._tabs_by_title.get("Komplet")
    tab_sciana = window._tabs_by_title.get("Sciana")
    tab_bazy = window._tabs_by_title.get("Bazy")
    tab_quote_base = window._tabs_by_title.get("Baza szybkich wycen")
    tab_grafika = window._tabs_by_title.get("Grafika")
    tab_tech_modul = window._tabs_by_title.get("TECH_modul")

    if tab_start is not None:
        if hasattr(tab_start, "sig_new_order_requested"):
            tab_start.sig_new_order_requested.connect(window._open_new_order)
        if hasattr(tab_start, "sig_open_quote_requested"):
            tab_start.sig_open_quote_requested.connect(window._open_quote)
        if hasattr(tab_start, "sig_open_calendar_requested"):
            tab_start.sig_open_calendar_requested.connect(window._open_calendar)
        if hasattr(tab_start, "sig_open_work_time_requested"):
            tab_start.sig_open_work_time_requested.connect(window._open_work_time)
        if hasattr(tab_start, "sig_open_time_kiosk_requested"):
            tab_start.sig_open_time_kiosk_requested.connect(window._open_time_kiosk)
        if hasattr(tab_start, "sig_open_clients_requested"):
            tab_start.sig_open_clients_requested.connect(window._open_clients_in_bazy)
        if hasattr(tab_start, "sig_new_wall_requested"):
            tab_start.sig_new_wall_requested.connect(window._open_new_wall)
        if hasattr(tab_start, "sig_new_assembly_requested"):
            tab_start.sig_new_assembly_requested.connect(window._open_new_assembly)
        if hasattr(tab_start, "sig_new_module_requested"):
            tab_start.sig_new_module_requested.connect(window._open_new_module)
        if hasattr(tab_start, "sig_open_bazy_requested"):
            tab_start.sig_open_bazy_requested.connect(window._open_bazy)
        if hasattr(tab_start, "sig_open_settings_requested"):
            tab_start.sig_open_settings_requested.connect(window._open_settings)
        if hasattr(tab_start, "sig_theme_profile_requested"):
            tab_start.sig_theme_profile_requested.connect(window._apply_theme_profile)

    if tab_nowe_zamowienie is not None:
        if hasattr(tab_nowe_zamowienie, "sig_open_clients_base_requested"):
            tab_nowe_zamowienie.sig_open_clients_base_requested.connect(window._open_clients_in_bazy)
        if hasattr(tab_nowe_zamowienie, "sig_open_orders_base_requested"):
            tab_nowe_zamowienie.sig_open_orders_base_requested.connect(window._open_orders_in_bazy)
        if hasattr(tab_nowe_zamowienie, "sig_open_sciana_requested"):
            tab_nowe_zamowienie.sig_open_sciana_requested.connect(window._open_new_wall)
        if hasattr(tab_nowe_zamowienie, "sig_open_komplet_requested"):
            tab_nowe_zamowienie.sig_open_komplet_requested.connect(window._open_new_assembly)
        if hasattr(tab_nowe_zamowienie, "sig_open_existing_sciana_requested"):
            tab_nowe_zamowienie.sig_open_existing_sciana_requested.connect(window._open_wall_in_sciana)
        if hasattr(tab_nowe_zamowienie, "sig_calendar_events_changed"):
            tab_kalendarz = window._tabs_by_title.get("Kalendarz")
            if tab_kalendarz is not None and hasattr(tab_kalendarz, "refresh_data"):
                tab_nowe_zamowienie.sig_calendar_events_changed.connect(tab_kalendarz.refresh_data)

    if tab_sciana is not None and hasattr(tab_sciana, "sig_open_komplet_requested"):
        tab_sciana.sig_open_komplet_requested.connect(window._open_new_assembly)

    if tab_komplet is not None and hasattr(tab_komplet, "sig_open_order_requested"):
        tab_komplet.sig_open_order_requested.connect(window._open_new_order)

    if tab_komplet is not None and hasattr(tab_komplet, "sig_open_wycena_requested"):
        tab_komplet.sig_open_wycena_requested.connect(window._open_assembly_in_wycena)

    if (
        tab_modul is not None
        and tab_ustawienia is not None
        and hasattr(tab_ustawienia, "sig_settings_saved")
        and hasattr(tab_modul, "reload_drawing_settings_from_storage")
    ):
        tab_ustawienia.sig_settings_saved.connect(tab_modul.reload_drawing_settings_from_storage)

    if tab_ustawienia is not None and hasattr(tab_ustawienia, "sig_ui_theme_changed"):
        tab_ustawienia.sig_ui_theme_changed.connect(window._apply_ui_theme)

    if (
        tab_bazy is not None
        and tab_modul is not None
        and hasattr(tab_bazy, "sig_open_module_requested")
        and hasattr(tab_modul, "load_module_from_store_name")
    ):
        tab_bazy.sig_open_module_requested.connect(window._open_module_in_modul)

    if (
        tab_bazy is not None
        and tab_sciana is not None
        and hasattr(tab_bazy, "sig_open_wall_requested")
        and hasattr(tab_sciana, "load_wall_from_store_name")
    ):
        tab_bazy.sig_open_wall_requested.connect(window._open_wall_in_sciana)

    if (
        tab_bazy is not None
        and tab_komplet is not None
        and hasattr(tab_bazy, "sig_open_assembly_requested")
        and hasattr(tab_komplet, "load_assembly_from_store_name")
    ):
        tab_bazy.sig_open_assembly_requested.connect(window._open_assembly_in_komplet)

    if tab_bazy is not None and hasattr(tab_bazy, "sig_new_module_requested"):
        tab_bazy.sig_new_module_requested.connect(window._open_new_module)

    if tab_bazy is not None and hasattr(tab_bazy, "sig_new_wall_requested"):
        tab_bazy.sig_new_wall_requested.connect(window._open_new_wall)

    if tab_bazy is not None and hasattr(tab_bazy, "sig_new_assembly_requested"):
        tab_bazy.sig_new_assembly_requested.connect(window._open_new_assembly)

    if tab_quote_base is not None and hasattr(tab_quote_base, "sig_open_order_requested"):
        tab_quote_base.sig_open_order_requested.connect(window._open_orders_in_bazy_code)

    if tab_grafika is not None and hasattr(tab_grafika, "sig_open_tab_requested"):
        tab_grafika.sig_open_tab_requested.connect(window._navigate_to_tab)

    if tab_tech_modul is not None and hasattr(tab_tech_modul, "sig_open_tab_requested"):
        tab_tech_modul.sig_open_tab_requested.connect(window._navigate_to_tab)
