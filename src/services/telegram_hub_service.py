from __future__ import annotations

from datetime import datetime
from typing import Any, List, Dict

from src.app.app_settings import load_telegram_settings
from src.integrations.telegram_checklist import sync_telegram_hub_callbacks
from src.storage.order_store_json import OrderStoreJson
from src.storage.worker_store_json import WorkerStoreJson
from src.storage.work_time_session_store_json import WorkTimeSessionStoreJson, WorkTimeSessionDef
from src.storage.work_time_store_json import WorkTimeStoreJson
from src.domain.work_time_models import WorkTimeEntryDef
import os
import re
import requests
from src.api.data_manager import data_manager

class TelegramHubService:
    @staticmethod
    def _build_low_stock_lines(limit: int = 8) -> List[str]:
        rows = data_manager.get_low_stock_materials(limit=max(1, int(limit or 8)))
        if not rows:
            return ["  ✅ Brak pozycji poniżej minimum."]
        out: List[str] = []
        for item in rows:
            name = str(item.get("name", "") or "").strip() or f"Material #{int(item.get('id') or 0)}"
            stock = float(item.get("stock_quantity") or 0.0)
            min_stock = float(item.get("min_stock") or 0.0)
            missing = float(item.get("missing_qty") or 0.0)
            unit = str(item.get("unit", "") or "m2").strip() or "m2"
            supplier = str(item.get("supplier", "") or "").strip()
            wholesaler = str(item.get("wholesaler", "") or "").strip()
            vendor = " / ".join([v for v in [supplier, wholesaler] if v]) or "brak dostawcy"
            out.append(
                f"  • {name}: stan {stock:.2f} {unit}, min {min_stock:.2f}, brakuje {missing:.2f} ({vendor})"
            )
        return out

    @staticmethod
    def sync_all() -> Dict[str, Any]:
        settings = load_telegram_settings()
        if not settings.enabled or not settings.bot_token:
            return {"ok": False, "message": "Telegram not configured"}

        try:
            summary = sync_telegram_hub_callbacks(settings.bot_token)
        except Exception as e:
            return {"ok": False, "message": f"Sync failed: {str(e)}"}

        applied_other = summary.get("applied_other", [])
        updates_count = 0
        
        order_store = OrderStoreJson()
        worker_store = WorkerStoreJson()
        session_store = WorkTimeSessionStoreJson()
        work_time_store = WorkTimeStoreJson()

        for update in applied_other:
            upd_type = update.get("type")
            
            if upd_type == "production":
                order_id = update.get("order_id")
                new_state = update.get("state") # todo / done
                order = order_store.get_by_id(order_id)
                if order:
                    # Update status based on checklist toggle
                    order.status = "Zakonczone" if new_state == "done" else "W produkcji"
                    order.progress_percent = 100.0 if new_state == "done" else 50.0
                    order_store.overwrite(order)
                    updates_count += 1
            
            elif upd_type == "worktime_punch":
                worker_id = update.get("worker_id")
                worker = worker_store.get(worker_id)
                if not worker: continue
                
                now = datetime.now()
                now_iso = now.isoformat()
                
                session = session_store.get(worker_id)
                if session and session.started_at_iso:
                    # CLOSE SESSION
                    start = datetime.fromisoformat(session.started_at_iso)
                    duration = (now - start).total_seconds() / 3600.0
                    
                    # Create permanent record
                    record = WorkTimeEntryDef(
                        date_iso=now.strftime("%Y-%m-%d"),
                        hours=max(0.1, round(duration, 2)),
                        work_type="Produkcja (Telegram)",
                        note=f"Sesja zamknieta przez Telegram ({start.strftime('%H:%M')} - {now.strftime('%H:%M')})"
                    )
                    work_time_store.save_record(record)
                    session_store.delete(worker_id)
                    updates_count += 1
                else:
                    # START SESSION
                    new_session = WorkTimeSessionDef(
                        worker_id=worker_id,
                        worker_name=worker.name or "Pracownik",
                        work_type="Produkcja",
                        started_at_iso=now_iso,
                        last_action_iso=now_iso
                    )
                    session_store.set(new_session)
                    updates_count += 1

        return {
            "ok": True,
            "processed": summary.get("processed_updates", 0),
            "applied_other": len(applied_other),
            "db_updates": updates_count
        }

    @staticmethod
    def generate_briefing() -> str:
        """Generuje treść briefingu deweloperskiego na podstawie stanu systemu."""
        now = datetime.now()
        day_names = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
        day_name = day_names[now.weekday()]
        
        # 1. Dane z bazy
        stats = data_manager.get_db_overview()
        
        # 2. Skanowanie TODO/FIXME w kodzie
        todo_list = []
        src_path = os.path.join(os.getcwd(), "src")
        try:
            for root, _, files in os.walk(src_path):
                for file in files:
                    if file.endswith(".py"):
                        path = os.path.join(root, file)
                        with open(path, "r", encoding="utf-8") as f:
                            for i, line in enumerate(f, 1):
                                if "TODO:" in line or "FIXME:" in line or "# todo" in line.lower():
                                    rel_path = os.path.relpath(path, os.getcwd())
                                    clean_line = line.strip().split("#")[-1].strip()
                                    todo_list.append(f"{rel_path}:{i} → {clean_line}")
        except:
             pass

        # 3. Formatowanie raportu
        briefing = f"╔══════════════════════════════════════════════════════╗\n"
        briefing += f"║  BRIEFING DEWELOPERSKI — TECH_modul\n"
        briefing += f"║  {day_name}, {now.strftime('%d %B %Y')}\n"
        briefing += f"╚══════════════════════════════════════════════════════╝\n\n"
        
        briefing += "========================================================\n"
        briefing += "  1. STAN DANYCH (SQLite)\n"
        briefing += "========================================================\n"
        briefing += f"  • Zamówienia: {stats.get('orders_count', 0)}\n"
        briefing += f"  • Projekty (Ściany): {stats.get('projects_count', 0)}\n"
        briefing += f"  • Moduły (Szafki): {stats.get('modules_count', 0)}\n"
        briefing += f"  • Baza materiałów: {stats.get('materials_count', 0)}\n"
        briefing += f"  • Kontrahenci: {stats.get('clients_count', 0)}\n\n"
        
        briefing += "========================================================\n"
        briefing += "  2. TODO / FIXME W KODZIE\n"
        briefing += "========================================================\n"
        if todo_list:
            for item in todo_list[:10]: # Limit do 10 pozycji
                briefing += f"  • {item}\n"
            if len(todo_list) > 10:
                briefing += f"  ... i {len(todo_list)-10} więcej.\n"
        else:
            briefing += "  ✅ Brak zaległości technicznych w kodzie.\n"
        
        briefing += "\n========================================================\n"
        briefing += "  3. PRIORYTETY NA DZIŚ\n"
        briefing += "========================================================\n"
        briefing += "  1. Etap 4 — Rozszerz Magazyn o logikę rezerwacji materiałów\n"
        briefing += "  2. Etap 1A — Szybka kalkulacja: urealnij cennik z Biblioteki\n"
        briefing += "  3. Weryfikacja importu 3D z nowymi profilami\n\n"

        briefing += "========================================================\n"
        briefing += "  4. NISKIE STANY MAGAZYNOWE (AUTO)\n"
        briefing += "========================================================\n"
        for line in TelegramHubService._build_low_stock_lines(limit=8):
            briefing += f"{line}\n"
        briefing += "\n"
        
        briefing += "────────────────────────────────────────────────────────\n"
        briefing += "  Dobrego dnia pracy!\n"
        briefing += "────────────────────────────────────────────────────────"
        
        return briefing

    @staticmethod
    def send_briefing() -> Dict[str, Any]:
        """Wysyła wygenerowany briefing na skonfigurowany chat Telegram."""
        settings = load_telegram_settings()
        if not settings.enabled or not settings.bot_token or not settings.chat_id:
            return {"ok": False, "message": "Telegram partially configured"}
            
        briefing = TelegramHubService.generate_briefing()
        
        url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
        payload = {
            "chat_id": settings.chat_id,
            "text": briefing,
            "parse_mode": "HTML"
        }
        
        try:
            # Note: We use monospace for better alignment of our formatting boxes
            payload["text"] = f"<pre>{briefing}</pre>"
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                return {"ok": True, "message": "Briefing sent"}
            else:
                return {"ok": False, "message": f"Telegram API error: {resp.text}"}
        except Exception as e:
            return {"ok": False, "message": f"Send failed: {str(e)}"}

    @staticmethod
    def send_low_stock_report(limit: int = 20) -> Dict[str, Any]:
        """Wysyła sam raport braków magazynowych na Telegram."""
        settings = load_telegram_settings()
        if not settings.enabled or not settings.bot_token or not settings.chat_id:
            return {"ok": False, "message": "Telegram partially configured"}

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = TelegramHubService._build_low_stock_lines(limit=limit)
        text = "🚨 NISKIE STANY MAGAZYNOWE\n" + f"{now}\n\n" + "\n".join(lines)

        url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
        payload = {
            "chat_id": settings.chat_id,
            "text": text,
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                return {"ok": True, "message": "Low stock report sent"}
            return {"ok": False, "message": f"Telegram API error: {resp.text}"}
        except Exception as e:
            return {"ok": False, "message": f"Send failed: {str(e)}"}
