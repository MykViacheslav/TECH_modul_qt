"""
Excel/CSV export utilities for TECH_modul.
Exports orders, clients, and other data to CSV or Excel format.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.storage.data_paths import data_dir


def _safe(value: Any, default: str = "") -> str:
    """Safely convert value to string."""
    return str(value or default).strip()


def _format_currency(value: float) -> str:
    """Format currency value as PLN."""
    return f"{value:,.2f} zł".replace(",", " ").replace(".", ",").replace(" ", ".")


class CSVExporter:
    """Export data to CSV format."""
    
    @staticmethod
    def export_orders(orders: list[dict], output_path: str | Path) -> Path:
        """Export orders to CSV file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        headers = [
            "Kod", "Klient", "Status", "Postep", "Data utworzenia",
            "Termin projekt", "Termin produkcja", "Termin montaz",
            "Netto", "Brutto"
        ]
        
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(headers)
            
            for order in orders:
                row = [
                    _safe(order.get("code")),
                    _safe(order.get("client_name")),
                    _safe(order.get("status")),
                    order.get("progress_percent", 0),
                    _safe(order.get("created_at")),
                    _safe(order.get("date_projekt")),
                    _safe(order.get("date_produkcja")),
                    _safe(order.get("date_montaz")),
                    order.get("netto", 0),
                    order.get("brutto", 0),
                ]
                writer.writerow(row)
        
        return output_path
    
    @staticmethod
    def export_clients(clients: list[dict], output_path: str | Path) -> Path:
        """Export clients to CSV file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        headers = [
            "Nazwa", "Telefon", "Email", "Ulica", "Miasto", "NIP"
        ]
        
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(headers)
            
            for client in clients:
                row = [
                    _safe(client.get("name")),
                    _safe(client.get("phone")),
                    _safe(client.get("email")),
                    _safe(client.get("street")),
                    _safe(client.get("city")),
                    _safe(client.get("nip")),
                ]
                writer.writerow(row)
        
        return output_path
    
    @staticmethod
    def export_payments(payments: list[dict], output_path: str | Path) -> Path:
        """Export payments to CSV file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        headers = [
            "Zamowienie", "Etap", "Kwota", "Oplacone", "Data", "Uwagi"
        ]
        
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(headers)
            
            for pay in payments:
                row = [
                    _safe(pay.get("order_code")),
                    _safe(pay.get("stage")),
                    pay.get("amount", 0),
                    "Tak" if pay.get("paid") else "Nie",
                    _safe(pay.get("date")),
                    _safe(pay.get("notes")),
                ]
                writer.writerow(row)
        
        return output_path
    
    @staticmethod
    def export_materials(materials: list[dict], output_path: str | Path) -> Path:
        """Export materials to CSV file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        headers = [
            "Zakres", "Material", "Kolor", "Kod", "Status", "Data", "Uwagi"
        ]
        
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(headers)
            
            for mat in materials:
                row = [
                    _safe(mat.get("scope")),
                    _safe(mat.get("name")),
                    _safe(mat.get("color")),
                    _safe(mat.get("code")),
                    _safe(mat.get("status")),
                    _safe(mat.get("date")),
                    _safe(mat.get("notes")),
                ]
                writer.writerow(row)
        
        return output_path
    
    @staticmethod
    def export_work_time(entries: list[dict], output_path: str | Path) -> Path:
        """Export work time entries to CSV file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        headers = [
            "Data", "Pracownik", "Godzina start", "Godzina koniec",
            "Godziny", "Rodzaj pracy", "Projekt", "Uwagi"
        ]
        
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(headers)
            
            for entry in entries:
                row = [
                    _safe(entry.get("date")),
                    _safe(entry.get("worker_name")),
                    _safe(entry.get("start_time")),
                    _safe(entry.get("end_time")),
                    entry.get("hours", 0),
                    _safe(entry.get("work_type")),
                    _safe(entry.get("project")),
                    _safe(entry.get("notes")),
                ]
                writer.writerow(row)
        
        return output_path


class ExcelExporter:
    """
    Export data to Excel format.
    Requires openpyxl package.
    """
    
    @staticmethod
    def is_available() -> bool:
        """Check if openpyxl is installed."""
        try:
            import openpyxl
            return True
        except ImportError:
            return False
    
    @staticmethod
    def export_orders(orders: list[dict], output_path: str | Path) -> Path:
        """Export orders to Excel file."""
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Zamowienia"
        
        # Headers
        headers = [
            "Kod", "Klient", "Status", "Postep", "Data utworzenia",
            "Termin projekt", "Termin produkcja", "Termin montaz",
            "Notatki"
        ]
        
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border
        
        # Data rows
        for row_idx, order in enumerate(orders, 2):
            values = [
                _safe(order.get("code")),
                _safe(order.get("client_name")),
                _safe(order.get("status")),
                order.get("progress_percent", 0),
                _safe(order.get("created_at")),
                _safe(order.get("date_projekt")),
                _safe(order.get("date_produkcja")),
                _safe(order.get("date_montaz")),
                _safe(order.get("notes")),
            ]
            for col, val in enumerate(values, 1):
                cell = ws.cell(row=row_idx, column=col, value=val)
                cell.border = thin_border
        
        # Auto-width columns
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 15
        
        wb.save(str(output_path))
        return output_path
    
    @staticmethod
    def export_multiple_sheets(data: dict[str, list[dict]], output_path: str | Path) -> Path:
        """Export multiple data sets to different sheets in one Excel file."""
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        sheet_definitions = {
            "Zamowienia": {
                "headers": ["Kod", "Klient", "Status", "Postep", "Data"],
                "fields": ["code", "client_name", "status", "progress_percent", "created_at"],
            },
            "Klienci": {
                "headers": ["Nazwa", "Telefon", "Email", "Miasto"],
                "fields": ["name", "phone", "email", "city"],
            },
            "Platnosci": {
                "headers": ["Zamowienie", "Etap", "Kwota", "Oplacone"],
                "fields": ["order_code", "stage", "amount", "paid"],
            },
        }
        
        for sheet_name, definition in sheet_definitions.items():
            if sheet_name not in data or not data[sheet_name]:
                continue
            
            ws = wb.create_sheet(title=sheet_name)
            
            # Headers
            for col, header in enumerate(definition["headers"], 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")
                cell.border = thin_border
            
            # Data rows
            for row_idx, item in enumerate(data[sheet_name], 2):
                for col, field in enumerate(definition["fields"], 1):
                    val = item.get(field, "")
                    if isinstance(val, bool):
                        val = "Tak" if val else "Nie"
                    cell = ws.cell(row=row_idx, column=col, value=val)
                    cell.border = thin_border
            
            # Auto-width
            for col in range(1, len(definition["headers"]) + 1):
                from openpyxl.utils import get_column_letter
                ws.column_dimensions[get_column_letter(col)].width = 15
        
        wb.save(str(output_path))
        return output_path


def export_to_csv(data: list[dict], headers: list[str], fields: list[str], 
                  output_path: str | Path) -> Path:
    """Generic CSV export function."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(headers)
        
        for item in data:
            row = [item.get(field, "") for field in fields]
            writer.writerow(row)
    
    return output_path


def get_default_export_dir() -> Path:
    """Get default export directory."""
    export_dir = data_dir() / "export" / "csv"
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir
