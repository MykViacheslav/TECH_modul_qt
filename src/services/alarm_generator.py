from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

from src.domain.alarm_models import AlarmDef, new_alarm_id
from src.storage.alarm_store_json import AlarmStoreJson
from src.storage.client_store_json import ClientStoreJson
from src.storage.data_paths import data_dir
from src.storage.order_store_json import OrderStoreJson
from src.storage.service_store_json import ServiceStoreJson

if TYPE_CHECKING:
    from src.services.alarm_service import AlarmService


class AlarmGenerator:
    SRC_PAYMENT = "alarm_generator_payment"
    SRC_DEADLINE = "alarm_generator_deadline"
    SRC_SERVICE = "alarm_generator_service"
    SRC_MATERIAL = "alarm_generator_material"
    SRC_ORDER_INTEGRITY = "alarm_generator_order_integrity"
    SRC_PRODUCION = "alarm_generator_production"

    def __init__(self, alarm_service: "AlarmService | None" = None) -> None:
        self._store = AlarmStoreJson()
        self._order_store = OrderStoreJson()
        self._client_store = ClientStoreJson()
        self._service_store = ServiceStoreJson()
        self._existing_alarms = []
        self._batch_to_save = []
        self._alarm_service = alarm_service

    def _refresh_existing(self) -> None:
        self._existing_alarms = self._store.list_alarms()

    def _safe_float(self, value: Any) -> float:
        raw = str(value or "").strip().replace(" ", "").replace(",", ".")
        if not raw:
            return 0.0
        try:
            return float(raw)
        except ValueError:
            return 0.0

    def _alarm_exists(self, title: str, category: str, source: str) -> bool:
        combined = self._existing_alarms + self._batch_to_save
        for alarm in combined:
            if alarm.is_resolved:
                continue
            if str(alarm.title or "") != str(title or ""):
                continue
            if str(alarm.category or "") != str(category or ""):
                continue
            if str((alarm.extra or {}).get("source", "") or "") != str(source or ""):
                continue
            return True
        return False

    def _clear_generated_source(self, source: str) -> None:
        self._flush_batch()
        self._store.delete_alarms_by_source(source)
        self._refresh_existing()
        self._batch_to_save = []

    def _add_alarm(self, alarm: AlarmDef, source: str) -> None:
        alarm.extra = dict(alarm.extra or {})
        alarm.extra["source"] = source
        if not alarm.alarm_id:
            alarm.alarm_id = new_alarm_id()
        if not alarm.created_at:
            alarm.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._batch_to_save.append(alarm)

    def _flush_batch(self) -> None:
        if self._batch_to_save:
            self._store.save_alarms_batch(self._batch_to_save)
            self._batch_to_save = []
            self._refresh_existing()

    def generate_all(self) -> None:
        """Run all alarm generation methods and also run AlarmService checks if available."""
        self._refresh_existing()
        
        self._generate_payment_alarms()
        self._generate_deadline_alarms()
        self._generate_service_alarms()
        self._generate_material_alarms()
        self._generate_order_integrity_alarms()
        self._generate_production_alarms()
        
        self._flush_batch()
        
        # Also run AlarmService checks if available
        if self._alarm_service is not None:
            try:
                self._alarm_service.run_all_checks()
            except Exception as e:
                print(f"AlarmService checks failed: {e}")

    def _generate_payment_alarms(self) -> None:
        self._clear_generated_source(self.SRC_PAYMENT)
        orders = self._order_store.list_orders()
        today = datetime.now().date()

        for order in orders:
            order_name = str(getattr(order, "order_id", "") or getattr(order, "code", "") or "").strip()
            if not order_name:
                continue

            date_montaz = str(getattr(order, "date_montaz", "") or "").strip()
            if date_montaz:
                try:
                    montaz_date = datetime.strptime(date_montaz, "%Y-%m-%d").date()
                except ValueError:
                    montaz_date = None
                if montaz_date is not None:
                    days_until = (montaz_date - today).days
                    if days_until < 0:
                        title = f"Zamowienie {order_name} - montaz zalegly"
                        if not self._alarm_exists(title, "terminy", self.SRC_PAYMENT):
                            self._add_alarm(
                                AlarmDef(
                                    category="terminy",
                                    severity="krytyczny",
                                    title=title,
                                    description=f"Montaz zamowienia {order_name} jest zalegly o {-days_until} dni.",
                                    related_order=order_name,
                                    due_date=date_montaz,
                                ),
                                self.SRC_PAYMENT,
                            )
                    elif days_until <= 3:
                        title = f"Zamowienie {order_name} - montaz w ciagu 3 dni"
                        if not self._alarm_exists(title, "terminy", self.SRC_PAYMENT):
                            self._add_alarm(
                                AlarmDef(
                                    category="terminy",
                                    severity="ostrzezenie",
                                    title=title,
                                    description=f"Montaz zamowienia {order_name} zaplanowany za {days_until} dni.",
                                    related_order=order_name,
                                    due_date=date_montaz,
                                ),
                                self.SRC_PAYMENT,
                            )

            client_name = str(getattr(order, "client_name", "") or "").strip()
            date_wycena = str(getattr(order, "date_wycena", "") or "").strip()
            if client_name and date_wycena:
                try:
                    wycena_date = datetime.strptime(date_wycena, "%Y-%m-%d").date()
                except ValueError:
                    wycena_date = None
                if wycena_date is not None:
                    days_old = (today - wycena_date).days
                    if days_old > 30:
                        title = f"Wycena {order_name} - stare dane"
                        if not self._alarm_exists(title, "projekty", self.SRC_PAYMENT):
                            self._add_alarm(
                                AlarmDef(
                                    category="projekty",
                                    severity="info",
                                    title=title,
                                    description=f"Wycena dla {client_name} nie byla aktualizowana od {days_old} dni.",
                                    related_order=order_name,
                                    related_client=client_name,
                                ),
                                self.SRC_PAYMENT,
                            )

    def _generate_deadline_alarms(self) -> None:
        self._clear_generated_source(self.SRC_DEADLINE)
        orders = self._order_store.list_orders()
        today = datetime.now().date()

        for order in orders:
            order_name = str(getattr(order, "order_id", "") or getattr(order, "code", "") or "").strip()
            if not order_name:
                continue

            for stage, date_field in (
                ("Projekt", "date_projekt"),
                ("Zakup materialow", "date_zakup_mat"),
                ("Produkcja", "date_produkcja"),
                ("Montaz", "date_montaz"),
            ):
                date_str = str(getattr(order, date_field, "") or "").strip()
                if not date_str:
                    continue
                try:
                    stage_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    continue
                days_until = (stage_date - today).days
                if days_until < 0:
                    title = f"{order_name} - {stage} zalegly"
                    if not self._alarm_exists(title, "terminy", self.SRC_DEADLINE):
                        self._add_alarm(
                            AlarmDef(
                                category="terminy",
                                severity="krytyczny",
                                title=title,
                                description=f"Etap '{stage}' zamowienia {order_name} jest zalegly.",
                                related_order=order_name,
                                due_date=date_str,
                            ),
                            self.SRC_DEADLINE,
                        )

    def _generate_material_alarms(self) -> None:
        self._clear_generated_source(self.SRC_MATERIAL)
        material_rows = self._load_material_rows()
        by_id: dict[str, dict[str, Any]] = {}
        by_name: dict[str, dict[str, Any]] = {}
        for row in material_rows:
            mat_id = str(row.get("id", "") or "").strip()
            name = str(row.get("nazwa", "") or "").strip()
            if mat_id:
                by_id[mat_id] = row
            if name:
                by_name[name.lower()] = row

        for row in material_rows:
            mat_id = str(row.get("id", "") or "").strip()
            name = str(row.get("nazwa", "") or "").strip() or mat_id or "[material]"
            stock = self._safe_float(row.get("ilosc_magazyn", row.get("ilosc", 0.0)))
            if stock <= 0:
                title = f"Material {name} - brak stanu magazynowego"
                if not self._alarm_exists(title, "materialy", self.SRC_MATERIAL):
                    self._add_alarm(
                        AlarmDef(
                            category="materialy",
                            severity="ostrzezenie",
                            title=title,
                            description=f"Uzupelnij magazyn dla materialu {name}.",
                            related_material=mat_id or name,
                        ),
                        self.SRC_MATERIAL,
                    )

        required_by_key: dict[str, float] = {}
        name_by_key: dict[str, str] = {}
        quote_ids_by_key: dict[str, set[str]] = {}
        for quote in self._load_usluga_quotes():
            quote_id = str(quote.get("quote_id", "") or "").strip()
            rows = quote.get("rows", [])
            for row in rows if isinstance(rows, list) else []:
                if not isinstance(row, dict):
                    continue
                mat_id = str(row.get("material_id", "") or "").strip()
                mat_name = str(row.get("material_name", "") or "").strip()
                if not mat_id and not mat_name:
                    continue
                key = mat_id or mat_name.lower()
                qty = max(0.0, self._safe_float(row.get("qty", 0.0)))
                if qty <= 0:
                    continue
                required_by_key[key] = required_by_key.get(key, 0.0) + qty
                name_by_key[key] = mat_name or mat_id or key
                if quote_id:
                    quote_ids_by_key.setdefault(key, set()).add(quote_id)

        for key, required in required_by_key.items():
            source_row = by_id.get(key) if key in by_id else by_name.get(key.lower())
            stock = self._safe_float((source_row or {}).get("ilosc_magazyn", (source_row or {}).get("ilosc", 0.0)))
            if required > stock:
                missing = required - stock
                mat_name = str(name_by_key.get(key, key))
                quote_ids = sorted(list(quote_ids_by_key.get(key, set())))
                quote_ref = quote_ids[0] if quote_ids else ""
                title = f"Material {mat_name} - brak ilosci do uslug"
                if not self._alarm_exists(title, "materialy", self.SRC_MATERIAL):
                    self._add_alarm(
                        AlarmDef(
                            category="materialy",
                            severity="krytyczny",
                            title=title,
                            description=f"Potrzeba {required:.2f}, na magazynie {stock:.2f}, brakuje {missing:.2f}.",
                            related_order=quote_ref,
                            related_material=mat_name,
                        ),
                        self.SRC_MATERIAL,
                    )

        for order in self._order_store.list_orders():
            order_code = str(getattr(order, "order_id", "") or getattr(order, "code", "") or "").strip()
            if not order_code:
                continue
            status = str(getattr(order, "status", "") or "").strip().lower()
            if status not in {"zaakceptowane", "zakup materialow", "w produkcji", "lakiernia", "montaz"}:
                continue
            raw_choices = getattr(order, "material_choices", [])
            choices = [x for x in raw_choices if isinstance(x, dict)]
            final_choices = [x for x in choices if str(x.get("status", "") or "").strip().lower() == "wybrane finalnie"]
            if final_choices:
                continue
            title = f"Zamowienie {order_code} - brak finalnych materialow"
            if not self._alarm_exists(title, "materialy", self.SRC_MATERIAL):
                self._add_alarm(
                    AlarmDef(
                        category="materialy",
                        severity="ostrzezenie",
                        title=title,
                        description="Dodaj finalne materialy, aby uruchomic produkcje bez konfliktow.",
                        related_order=order_code,
                    ),
                    self.SRC_MATERIAL,
                )

    def _generate_service_alarms(self) -> None:
        self._clear_generated_source(self.SRC_SERVICE)
        services = self._service_store.list_services()
        today = datetime.now().date()

        for svc in services:
            service_name = str(getattr(svc, "name", "") or "").strip()
            if not service_name:
                continue

            service_id = str(getattr(svc, "service_id", "") or "").strip()
            category = str(getattr(svc, "category", "") or "").strip()
            price = float(getattr(svc, "price", 0.0) or 0.0)

            if price <= 0:
                title = f"Usluga {service_name} - brak ceny"
                if not self._alarm_exists(title, "projekty", self.SRC_SERVICE):
                    self._add_alarm(
                        AlarmDef(
                            category="projekty",
                            severity="ostrzezenie",
                            title=title,
                            description=f"Uzupelnij cennik uslugi ({category or 'inne'}).",
                            related_order=service_id,
                        ),
                        self.SRC_SERVICE,
                    )

            deadline = str(getattr(svc, "deadline", "") or "").strip()
            if not deadline:
                continue
            try:
                deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
            except ValueError:
                continue

            days_until = (deadline_date - today).days
            if days_until < 0:
                title = f"Usluga {service_name} - termin zalegly"
                if not self._alarm_exists(title, "terminy", self.SRC_SERVICE):
                    self._add_alarm(
                        AlarmDef(
                            category="terminy",
                            severity="krytyczny",
                            title=title,
                            description=f"Termin uslugi minal {-days_until} dni temu.",
                            related_order=service_id,
                            due_date=deadline,
                        ),
                        self.SRC_SERVICE,
                    )
            elif days_until <= 3:
                title = f"Usluga {service_name} - termin do 3 dni"
                if not self._alarm_exists(title, "terminy", self.SRC_SERVICE):
                    self._add_alarm(
                        AlarmDef(
                            category="terminy",
                            severity="ostrzezenie",
                            title=title,
                            description=f"Termin uslugi za {days_until} dni.",
                            related_order=service_id,
                            due_date=deadline,
                        ),
                        self.SRC_SERVICE,
                    )

    def _generate_order_integrity_alarms(self) -> None:
        self._clear_generated_source(self.SRC_ORDER_INTEGRITY)
        orders = self._order_store.list_orders()
        for order in orders:
            order_code = str(getattr(order, "order_id", "") or getattr(order, "code", "") or "").strip()
            if not order_code:
                continue
            client = str(getattr(order, "client_name", "") or "").strip()
            worker = str(getattr(order, "worker_name", "") or "").strip()
            status = str(getattr(order, "status", "") or "").strip().lower()

            if not client:
                title = f"Zamowienie {order_code} - brak klienta"
                if not self._alarm_exists(title, "projekty", self.SRC_ORDER_INTEGRITY):
                    self._add_alarm(
                        AlarmDef(
                            category="projekty",
                            severity="krytyczny",
                            title=title,
                            description="Uzupelnij klienta w zamowieniu.",
                            related_order=order_code,
                        ),
                        self.SRC_ORDER_INTEGRITY,
                    )

            if not worker:
                title = f"Zamowienie {order_code} - brak pracownika"
                if not self._alarm_exists(title, "pracownicy", self.SRC_ORDER_INTEGRITY):
                    self._add_alarm(
                        AlarmDef(
                            category="pracownicy",
                            severity="ostrzezenie",
                            title=title,
                            description="Przypisz pracownika odpowiedzialnego za realizacje.",
                            related_order=order_code,
                            related_client=client,
                        ),
                        self.SRC_ORDER_INTEGRITY,
                    )

            if status in {"zaakceptowane", "zakup materialow", "w produkcji", "lakiernia", "montaz"}:
                for field, label in (
                    ("date_zakup_mat", "zakup materialow"),
                    ("date_produkcja", "produkcja"),
                    ("date_montaz", "montaz"),
                ):
                    value = str(getattr(order, field, "") or "").strip()
                    if value:
                        continue
                    title = f"Zamowienie {order_code} - brak terminu: {label}"
                    if not self._alarm_exists(title, "terminy", self.SRC_ORDER_INTEGRITY):
                        self._add_alarm(
                            AlarmDef(
                                category="terminy",
                                severity="ostrzezenie",
                                title=title,
                                description=f"Dodaj date etapu: {label}.",
                                related_order=order_code,
                                related_client=client,
                            ),
                            self.SRC_ORDER_INTEGRITY,
                        )

            quote_items = getattr(order, "quote_items", [])
            if isinstance(quote_items, list) and len(quote_items) == 0:
                title = f"Zamowienie {order_code} - brak pozycji do wyceny"
                if not self._alarm_exists(title, "projekty", self.SRC_ORDER_INTEGRITY):
                    self._add_alarm(
                        AlarmDef(
                            category="projekty",
                            severity="info",
                            title=title,
                            description="Dodaj pozycje do wyceny, aby kontrolowac koszt i termin.",
                            related_order=order_code,
                            related_client=client,
                        ),
                        self.SRC_ORDER_INTEGRITY,
                    )

    def _load_material_rows(self) -> list[dict[str, Any]]:
        path = data_dir() / "baza_materialu.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            rows = raw.get("rows", []) if isinstance(raw, dict) else []
            return [dict(x) for x in rows if isinstance(x, dict)]
        except Exception:
            return []

    def _load_usluga_quotes(self) -> list[dict[str, Any]]:
        path = data_dir() / "usluga_quotes.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
            return [dict(x) for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []
        except Exception:
            return []

    def _generate_production_alarms(self) -> None:
        self._clear_generated_source(self.SRC_PRODUCION)
        orders = self._order_store.list_orders()
        today = datetime.now().date()

        for order in orders:
            order_name = str(getattr(order, "order_id", "") or getattr(order, "code", "") or "").strip()
            if not order_name:
                continue

            date_produkcja = str(getattr(order, "date_produkcja", "") or "").strip()
            date_produkcja_end = str(getattr(order, "date_produkcja_end", "") or "").strip()
            status = str(getattr(order, "status", "") or "").strip().lower()

            if date_produkcja:
                try:
                    prod_date = datetime.strptime(date_produkcja, "%Y-%m-%d").date()
                except ValueError:
                    prod_date = None

                if prod_date and prod_date < today and status not in ("zakonczone", "zakończone"):
                    title = f"{order_name} - produkcja zalegla"
                    if not self._alarm_exists(title, "produkcja", self.SRC_PRODUCION):
                        days_late = (today - prod_date).days
                        self._add_alarm(
                            AlarmDef(
                                category="produkcja",
                                severity="krytyczny",
                                title=title,
                                description=f"Produkcja zamowienia {order_name} jest zalegla o {days_late} dni.",
                                related_order=order_name,
                                due_date=date_produkcja,
                            ),
                            self.SRC_PRODUCION,
                        )

            if not date_produkcja and status == "w produkcji":
                title = f"{order_name} - brak daty produkcji"
                if not self._alarm_exists(title, "produkcja", self.SRC_PRODUCION):
                    self._add_alarm(
                        AlarmDef(
                            category="produkcja",
                            severity="ostrzezenie",
                            title=title,
                            description=f"Zamowienie {order_name} jest w produkcji, ale nie ma ustawionej daty.",
                            related_order=order_name,
                        ),
                        self.SRC_PRODUCION,
                    )

            if date_produkcja and not date_produkcja_end and status == "w produkcji":
                title = f"{order_name} - brak daty zakonczenia produkcji"
                if not self._alarm_exists(title, "produkcja", self.SRC_PRODUCION):
                    self._add_alarm(
                        AlarmDef(
                            category="produkcja",
                            severity="info",
                            title=title,
                            description=f"Ustaw date zakonczenia produkcji dla {order_name}.",
                            related_order=order_name,
                        ),
                        self.SRC_PRODUCION,
                    )

            date_montaz = str(getattr(order, "date_montaz", "") or "").strip()
            if date_montaz:
                try:
                    montaz_date = datetime.strptime(date_montaz, "%Y-%m-%d").date()
                except ValueError:
                    montaz_date = None

                if montaz_date and status not in ("zakonczone", "zakończone", "zamontowane", "zamonowane"):
                    days_to_montaz = (montaz_date - today).days
                    if days_to_montaz <= 3 and days_to_montaz >= 0:
                        title = f"{order_name} - montaz za {days_to_montaz} dni"
                        if not self._alarm_exists(title, "produkcja", self.SRC_PRODUCION):
                            self._add_alarm(
                                AlarmDef(
                                    category="produkcja",
                                    severity="ostrzezenie",
                                    title=title,
                                    description=f"Montaz zamowienia {order_name} zaplanowany za {days_to_montaz} dni.",
                                    related_order=order_name,
                                    due_date=date_montaz,
                                ),
                                self.SRC_PRODUCION,
                            )
