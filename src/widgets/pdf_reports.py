"""
PDF Reports module for TECH_modul.
Generates professional PDF reports for orders, quotes, and production.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QByteArray, QBuffer, QIODevice, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QTextDocument
from PyQt6.QtGui import QPageLayout, QPageSize
from PyQt6.QtPrintSupport import QPrinter

from src.storage.data_paths import data_dir


def _format_currency(value: float) -> str:
    """Format currency value as PLN."""
    return f"{value:,.2f} zł".replace(",", " ").replace(".", ",").replace(" ", ".")


def _format_date(date_str: str) -> str:
    """Format date string for display."""
    if not date_str:
        return "-"
    return str(date_str)


def _safe(value: object, default: str = "") -> str:
    """Safely convert value to string."""
    return str(value or default).strip()


@dataclass
class OrderSummaryData:
    """Data class for order summary report."""
    code: str = ""
    order_name: str = ""
    client_name: str = ""
    status: str = ""
    created_at: str = ""
    
    # Costs
    material_cost: float = 0.0
    edgeband_cost: float = 0.0
    hardware_cost: float = 0.0
    labor_cost: float = 0.0
    total_cost: float = 0.0
    
    # Pricing
    margin_percent: float = 0.0
    netto: float = 0.0
    vat_percent: float = 23.0
    vat_amount: float = 0.0
    brutto: float = 0.0
    
    # Dates
    date_wycena: str = ""
    date_projekt: str = ""
    date_produkcja: str = ""
    date_montaz: str = ""
    
    # Items
    items: list[dict] | None = None
    materials: list[dict] | None = None
    payments: list[dict] | None = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
        if self.materials is None:
            self.materials = []
        if self.payments is None:
            self.payments = []


class OrderReportPDF:
    """Generates PDF reports for orders."""
    
    # HTML styles for reports
    STYLES = """
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10pt;
            color: #1f2937;
            margin: 0;
            padding: 0;
        }
        .page {
            padding: 20mm 15mm;
            page-break-after: always;
        }
        .page:last-child {
            page-break-after: avoid;
        }
        h1 {
            color: #1e40af;
            font-size: 18pt;
            margin: 0 0 10pt 0;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 8pt;
        }
        h2 {
            color: #374151;
            font-size: 12pt;
            margin: 15pt 0 8pt 0;
            border-bottom: 1px solid #d1d5db;
            padding-bottom: 4pt;
        }
        h3 {
            color: #4b5563;
            font-size: 10pt;
            margin: 10pt 0 5pt 0;
        }
        .header-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 15pt;
        }
        .header-box {
            background: #f3f4f6;
            border-radius: 6pt;
            padding: 10pt;
            flex: 1;
            margin: 0 5pt;
        }
        .header-box:first-child {
            margin-left: 0;
        }
        .header-box:last-child {
            margin-right: 0;
        }
        .label {
            color: #6b7280;
            font-size: 8pt;
            text-transform: uppercase;
        }
        .value {
            font-size: 11pt;
            font-weight: bold;
            color: #1f2937;
        }
        .highlight {
            background: #dbeafe;
            border-left: 3pt solid #3b82f6;
            padding: 8pt 12pt;
            margin: 10pt 0;
        }
        .highlight-total {
            background: #fef3c7;
            border-left: 3pt solid #f59e0b;
            padding: 8pt 12pt;
            margin: 10pt 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 10pt 0;
        }
        th {
            background: #374151;
            color: white;
            padding: 6pt 8pt;
            text-align: left;
            font-size: 9pt;
            font-weight: 600;
        }
        td {
            padding: 5pt 8pt;
            border-bottom: 1px solid #e5e7eb;
            font-size: 9pt;
        }
        tr:nth-child(even) {
            background: #f9fafb;
        }
        .text-right {
            text-align: right;
        }
        .text-center {
            text-align: center;
        }
        .footer {
            position: fixed;
            bottom: 10mm;
            left: 15mm;
            right: 15mm;
            text-align: center;
            font-size: 8pt;
            color: #9ca3af;
            border-top: 1px solid #e5e7eb;
            padding-top: 5pt;
        }
        .page-number {
            text-align: right;
            font-size: 8pt;
            color: #9ca3af;
        }
        .badge {
            display: inline-block;
            padding: 2pt 8pt;
            border-radius: 10pt;
            font-size: 8pt;
            font-weight: 600;
        }
        .badge-new { background: #dbeafe; color: #1e40af; }
        .badge-progress { background: #fef3c7; color: #92400e; }
        .badge-done { background: #d1fae5; color: #065f46; }
        .payment-row {
            display: flex;
            justify-content: space-between;
            padding: 5pt 0;
            border-bottom: 1px dashed #e5e7eb;
        }
        .payment-stage { flex: 1; }
        .payment-amount { width: 100pt; text-align: right; }
        .payment-status { width: 80pt; text-align: center; }
    </style>
    """
    
    def __init__(self):
        self._doc = QTextDocument()
    
    def _get_badge_class(self, status: str) -> str:
        """Get CSS class for status badge."""
        status_lower = status.lower()
        if "zakoncz" in status_lower or "gotow" in status_lower:
            return "badge-done"
        elif "start" in status_lower or "produk" in status_lower or "montaz" in status_lower:
            return "badge-progress"
        return "badge-new"
    
    def _build_header(self, data: OrderSummaryData) -> str:
        """Build report header."""
        return f"""
        <div class="header-row">
            <div class="header-box">
                <div class="label">Zamówienie</div>
                <div class="value">{_safe(data.code, '---')}</div>
                <div style="margin-top: 4pt; font-size: 9pt;">{_safe(data.order_name)}</div>
            </div>
            <div class="header-box">
                <div class="label">Klient</div>
                <div class="value">{_safe(data.client_name, '---')}</div>
            </div>
            <div class="header-box">
                <div class="label">Status</div>
                <div class="value">
                    <span class="badge {self._get_badge_class(data.status)}">
                        {_safe(data.status, 'Nowe')}
                    </span>
                </div>
                <div style="margin-top: 4pt; font-size: 9pt;">{_format_date(data.created_at)}</div>
            </div>
        </div>
        """
    
    def _build_dates_section(self, data: OrderSummaryData) -> str:
        """Build dates section."""
        dates = []
        if data.date_wycena:
            dates.append(("Wycena", data.date_wycena))
        if data.date_projekt:
            dates.append(("Projekt", data.date_projekt))
        if data.date_produkcja:
            dates.append(("Produkcja", data.date_produkcja))
        if data.date_montaz:
            dates.append(("Montaż", data.date_montaz))
        
        if not dates:
            return ""
        
        date_items = "".join([
            f'<div class="header-box"><div class="label">{label}</div><div class="value">{_format_date(date_val)}</div></div>'
            for label, date_val in dates
        ])
        
        return f"""
        <h2>📅 Terminy</h2>
        <div class="header-row">{date_items}</div>
        """
    
    def _build_items_table(self, items: list[dict]) -> str:
        """Build quote items table."""
        if not items:
            return ""
        
        rows = ""
        for item in items:
            name = _safe(item.get("name", ""))
            kind = _safe(item.get("kind", ""))
            description = _safe(item.get("description", ""))
            quantity = item.get("quantity", 1)
            price = float(item.get("price", 0) or 0)
            
            rows += f"""
            <tr>
                <td>{name}</td>
                <td>{kind}</td>
                <td class="text-center">{quantity}</td>
                <td>{description}</td>
                <td class="text-right">{_format_currency(price)}</td>
            </tr>
            """
        
        return f"""
        <h2>📋 Pozycje zamówienia</h2>
        <table>
            <thead>
                <tr>
                    <th style="width: 25%">Nazwa</th>
                    <th style="width: 15%">Typ</th>
                    <th style="width: 10%" class="text-center">Ilość</th>
                    <th style="width: 35%">Opis</th>
                    <th style="width: 15%" class="text-right">Cena</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """
    
    def _build_materials_table(self, materials: list[dict]) -> str:
        """Build materials table."""
        if not materials:
            return ""
        
        rows = ""
        for mat in materials:
            name = _safe(mat.get("name", ""))
            scope = _safe(mat.get("scope", ""))
            color = _safe(mat.get("color", ""))
            code = _safe(mat.get("code", ""))
            
            rows += f"""
            <tr>
                <td>{scope}</td>
                <td>{name}</td>
                <td>{color}</td>
                <td>{code}</td>
            </tr>
            """
        
        return f"""
        <h2>🎨 Wybrane materiały</h2>
        <table>
            <thead>
                <tr>
                    <th style="width: 20%">Zakres</th>
                    <th style="width: 30%">Materiał</th>
                    <th style="width: 25%">Kolor</th>
                    <th style="width: 25%">Kod</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """
    
    def _build_costs_section(self, data: OrderSummaryData) -> str:
        """Build cost summary section."""
        return f"""
        <h2>💰 Podsumowanie kosztów</h2>
        <div class="header-row">
            <div class="header-box">
                <div class="label">Materiały</div>
                <div class="value">{_format_currency(data.material_cost)}</div>
            </div>
            <div class="header-box">
                <div class="label">Okleiny</div>
                <div class="value">{_format_currency(data.edgeband_cost)}</div>
            </div>
            <div class="header-box">
                <div class="label">Okucia</div>
                <div class="value">{_format_currency(data.hardware_cost)}</div>
            </div>
            <div class="header-box">
                <div class="label">Robocizna</div>
                <div class="value">{_format_currency(data.labor_cost)}</div>
            </div>
        </div>
        
        <div class="highlight-total">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: bold;">Koszt całkowity (cena techniczna):</span>
                <span style="font-size: 14pt; font-weight: bold;">{_format_currency(data.total_cost)}</span>
            </div>
            <div style="margin-top: 5pt; font-size: 9pt; color: #6b7280;">
                Marża: {data.margin_percent:.1f}%
            </div>
        </div>
        """
    
    def _build_pricing_section(self, data: OrderSummaryData) -> str:
        """Build pricing section (netto/VAT/brutto)."""
        return f"""
        <h2>📊 Wycena</h2>
        <div class="highlight">
            <table style="margin: 0; border: none;">
                <tr style="background: transparent;">
                    <td style="border: none; padding: 4pt 0; width: 60%;"><strong>Cena netto:</strong></td>
                    <td style="border: none; padding: 4pt 0; text-align: right; font-size: 12pt;">
                        {_format_currency(data.netto)}
                    </td>
                </tr>
                <tr style="background: transparent;">
                    <td style="border: none; padding: 4pt 0;">VAT ({data.vat_percent:.0f}%):</td>
                    <td style="border: none; padding: 4pt 0; text-align: right;">
                        {_format_currency(data.vat_amount)}
                    </td>
                </tr>
                <tr style="background: transparent;">
                    <td style="border: none; padding: 8pt 0 4pt 0; font-size: 12pt;">
                        <strong style="color: #1e40af;">Cena brutto:</strong>
                    </td>
                    <td style="border: none; padding: 8pt 0 4pt 0; text-align: right; font-size: 16pt; font-weight: bold; color: #1e40af;">
                        {_format_currency(data.brutto)}
                    </td>
                </tr>
            </table>
        </div>
        """
    
    def _build_payments_section(self, payments: list[dict]) -> str:
        """Build payments schedule section."""
        if not payments:
            return ""
        
        rows = ""
        for pay in payments:
            stage = _safe(pay.get("stage", ""))
            amount = float(pay.get("amount", 0) or 0)
            paid = pay.get("paid", False)
            status = "✓ Opłacone" if paid else "○ Oczekuje"
            status_class = "color: #059669;" if paid else "color: #d97706;"
            
            rows += f"""
            <div class="payment-row">
                <span class="payment-stage">{stage}</span>
                <span class="payment-amount">{_format_currency(amount)}</span>
                <span class="payment-status" style="{status_class}">{status}</span>
            </div>
            """
        
        total = sum(float(p.get("amount", 0) or 0) for p in payments)
        paid = sum(float(p.get("amount", 0) or 0) for p in payments if p.get("paid"))
        
        return f"""
        <h2>💳 Harmonogram płatności</h2>
        <div style="background: #f9fafb; border-radius: 6pt; padding: 10pt;">
            {rows}
            <div class="payment-row" style="border-top: 2pt solid #374151; margin-top: 8pt; padding-top: 8pt;">
                <span class="payment-stage" style="font-weight: bold;">Razem:</span>
                <span class="payment-amount" style="font-weight: bold;">{_format_currency(total)}</span>
                <span class="payment-status" style="font-size: 8pt;">{_format_currency(paid)} opłacone</span>
            </div>
        </div>
        """
    
    def generate_summary(self, data: OrderSummaryData) -> str:
        """Generate complete order summary HTML."""
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            {self.STYLES}
        </head>
        <body>
            <div class="page">
                <h1>📦 Zamówienie: {_safe(data.code, '---')}</h1>
                
                {self._build_header(data)}
                
                {self._build_dates_section(data)}
                
                {self._build_items_table(data.items or [])}
                
                {self._build_materials_section(data.materials or [])}
                
                {self._build_costs_section(data)}
                
                {self._build_pricing_section(data)}
                
                {self._build_payments_section(data.payments or [])}
                
                <div class="footer">
                    Wygenerowano: {now} | TECH_modul - System zarządzania meblami
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _build_materials_section(self, materials: list[dict]) -> str:
        """Build materials section."""
        if not materials:
            return ""
        return self._build_materials_table(materials)
    
    def export_summary_pdf(self, data: OrderSummaryData, output_path: str | Path) -> Path:
        """Export order summary to PDF file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        html = self.generate_summary(data)
        
        # Set HTML content
        self._doc.setHtml(html)
        
        # Configure printer
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(output_path))
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageMargins(QPageLayout.Margins(15, 15, 15, 15), QPageLayout.Unit.Millimeter)
        
        # Print document
        self._doc.print(printer)
        
        return output_path


class BOMReportPDF:
    """Generates Bill of Materials (BOM) PDF report."""
    
    STYLES = OrderReportPDF.STYLES  # Reuse styles
    
    def __init__(self):
        self._doc = QTextDocument()
    
    def generate_bom(self, order_code: str, items: list[dict], 
                     materials_summary: dict | None = None) -> str:
        """Generate BOM report HTML."""
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # Group materials by category
        grouped = {}
        for item in items:
            category = _safe(item.get("category", "Inne"))
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(item)
        
        # Build tables for each category
        tables_html = ""
        total_materials = 0
        total_area = 0.0
        total_cost = 0.0
        
        for category, cat_items in sorted(grouped.items()):
            rows = ""
            for item in cat_items:
                name = _safe(item.get("name", ""))
                dimensions = _safe(item.get("dimensions", ""))
                material = _safe(item.get("material", ""))
                quantity = item.get("quantity", 1)
                area = float(item.get("area", 0) or 0)
                cost = float(item.get("cost", 0) or 0)
                
                total_materials += 1
                total_area += area
                total_cost += cost
                
                rows += f"""
                <tr>
                    <td>{name}</td>
                    <td>{dimensions}</td>
                    <td>{material}</td>
                    <td class="text-center">{quantity}</td>
                    <td class="text-right">{area:.2f} m²</td>
                    <td class="text-right">{_format_currency(cost)}</td>
                </tr>
                """
            
            tables_html += f"""
            <h3>{category}</h3>
            <table>
                <thead>
                    <tr>
                        <th style="width: 25%">Nazwa</th>
                        <th style="width: 20%">Wymiary</th>
                        <th style="width: 25%">Materiał</th>
                        <th style="width: 10%" class="text-center">Ilość</th>
                        <th style="width: 10%" class="text-right">Powierzchnia</th>
                        <th style="width: 10%" class="text-right">Koszt</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            {self.STYLES}
        </head>
        <body>
            <div class="page">
                <h1>📦 BOM - Bill of Materials</h1>
                
                <div class="header-row">
                    <div class="header-box">
                        <div class="label">Zamówienie</div>
                        <div class="value">{order_code}</div>
                    </div>
                    <div class="header-box">
                        <div class="label">Data</div>
                        <div class="value">{now}</div>
                    </div>
                    <div class="header-box">
                        <div class="label">Pozycji</div>
                        <div class="value">{total_materials}</div>
                    </div>
                </div>
                
                {tables_html}
                
                <div class="highlight-total">
                    <div style="display: flex; justify-content: space-between;">
                        <span><strong>Razem pozycji:</strong> {total_materials}</span>
                        <span><strong>Powierzchnia:</strong> {total_area:.2f} m²</span>
                        <span><strong>Koszt materiałów:</strong> {_format_currency(total_cost)}</span>
                    </div>
                </div>
                
                <div class="footer">
                    Wygenerowano: {now} | TECH_modul - BOM Report
                </div>
            </div>
        </body>
        </html>
        """
    
    def export_bom_pdf(self, order_code: str, items: list[dict],
                       output_path: str | Path) -> Path:
        """Export BOM to PDF file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        html = self.generate_bom(order_code, items)
        
        self._doc.setHtml(html)
        
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(output_path))
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageMargins(QPageLayout.Margins(15, 15, 15, 15), QPageLayout.Unit.Millimeter)
        
        self._doc.print(printer)
        
        return output_path


def get_default_export_dir() -> Path:
    """Get default PDF export directory."""
    export_dir = data_dir() / "export" / "pdf"
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def export_order_summary(data: OrderSummaryData, 
                         filename: str | None = None) -> Path:
    """Convenience function to export order summary."""
    if filename is None:
        safe_code = "".join(c if c.isalnum() or c in "-_" else "_" for c in data.code)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"zamowienie_{safe_code}_{timestamp}.pdf"
    
    output_path = get_default_export_dir() / filename
    report = OrderReportPDF()
    return report.export_summary_pdf(data, output_path)


def export_order_bom(order_code: str, items: list[dict],
                     filename: str | None = None) -> Path:
    """Convenience function to export BOM."""
    if filename is None:
        safe_code = "".join(c if c.isalnum() or c in "-_" else "_" for c in order_code)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"BOM_{safe_code}_{timestamp}.pdf"
    
    output_path = get_default_export_dir() / filename
    report = BOMReportPDF()
    return report.export_bom_pdf(order_code, items, output_path)


@dataclass
class ProductionCalendarData:
    """Data class for production calendar report."""
    week_start: str = ""
    week_end: str = ""
    events: list[dict] | None = None
    stations: list[str] | None = None
    
    def __post_init__(self):
        if self.events is None:
            self.events = []
        if self.stations is None:
            self.stations = ["Biuro główne", "CNC", "Oklejanie", "Lakiernia", "Montaż"]


class ProductionCalendarPDF:
    """Generates PDF production calendar reports."""
    
    STYLES = """
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 9pt;
            color: #1f2937;
            margin: 0;
            padding: 0;
        }
        .page {
            padding: 15mm 12mm;
            page-break-after: always;
        }
        h1 {
            color: #1e40af;
            font-size: 16pt;
            margin: 0 0 8pt 0;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 6pt;
        }
        h2 {
            color: #374151;
            font-size: 11pt;
            margin: 12pt 0 6pt 0;
            background: #f3f4f6;
            padding: 4pt 8pt;
            border-radius: 4pt;
        }
        .week-info {
            display: flex;
            justify-content: space-between;
            background: #dbeafe;
            padding: 8pt;
            border-radius: 6pt;
            margin-bottom: 10pt;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 5pt 0;
        }
        th {
            background: #374151;
            color: white;
            padding: 5pt 6pt;
            text-align: left;
            font-size: 8pt;
        }
        td {
            padding: 4pt 6pt;
            border: 1px solid #e5e7eb;
            font-size: 8pt;
            vertical-align: top;
        }
        .day-header {
            background: #f9fafb;
            font-weight: bold;
            padding: 6pt;
            border-bottom: 2pt solid #374151;
        }
        .station-cnc { background: #dbeafe; }
        .station-oklejanie { background: #fef3c7; }
        .station-lakiernia { background: #d1fae5; }
        .station-montaz { background: #fce7f3; }
        .event-box {
            border-radius: 4pt;
            padding: 3pt 5pt;
            margin: 2pt 0;
            font-size: 7pt;
        }
        .footer {
            text-align: center;
            font-size: 7pt;
            color: #9ca3af;
            margin-top: 10pt;
        }
    </style>
    """
    
    STATION_CLASSES = {
        "CNC": "station-cnc",
        "Oklejanie": "station-oklejanie",
        "Lakiernia": "station-lakiernia",
        "Montaż": "station-montaz",
        "Montaz": "station-montaz",
    }
    
    def __init__(self):
        self._doc = QTextDocument()
    
    def _get_station_class(self, station: str) -> str:
        """Get CSS class for station."""
        return self.STATION_CLASSES.get(station, "")
    
    def _build_events_by_day(self, events: list[dict], day: str) -> str:
        """Build events HTML for a specific day."""
        day_events = [e for e in events if _safe(e.get("day", "")) == day]
        if not day_events:
            return "<em>Brak zleceń</em>"
        
        html_parts = []
        for event in day_events:
            order_code = _safe(event.get("order_code", ""))
            client = _safe(event.get("client_name", ""))
            station = _safe(event.get("station", ""))
            status = _safe(event.get("status", ""))
            class_name = self._get_station_class(station)
            
            html_parts.append(f"""
                <div class="event-box {class_name}">
                    <strong>{order_code}</strong><br>
                    {client} - {station}<br>
                    <small>{status}</small>
                </div>
            """)
        
        return "".join(html_parts)
    
    def generate_weekly_schedule(self, data: ProductionCalendarData) -> str:
        """Generate weekly production schedule HTML."""
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        days = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"]
        
        tables_html = ""
        for day in days:
            events_html = self._build_events_by_day(data.events or [], day)
            tables_html += f"""
                <tr>
                    <td class="day-header" style="width: 25%;">{day}</td>
                    <td>{events_html}</td>
                </tr>
            """
        
        # Count statistics
        total_events = len(data.events or [])
        by_station = {}
        for event in (data.events or []):
            station = _safe(event.get("station", "Inne"))
            by_station[station] = by_station.get(station, 0) + 1
        
        stats_parts = [f"<strong>Razem:</strong> {total_events}"]
        for station, count in sorted(by_station.items()):
            stats_parts.append(f"{station}: {count}")
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            {self.STYLES}
        </head>
        <body>
            <div class="page">
                <h1>📅 Kalendarz produkcji - Harmonogram tygodniowy</h1>
                
                <div class="week-info">
                    <div>
                        <strong>Od:</strong> {_safe(data.week_start, '---')}<br>
                        <strong>Do:</strong> {_safe(data.week_end, '---')}
                    </div>
                    <div>
                        <strong>Wygenerowano:</strong> {now}
                    </div>
                    <div>
                        {" | ".join(stats_parts)}
                    </div>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th style="width: 25%;">Dzień</th>
                            <th>Zlecenia produkcyjne</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tables_html}
                    </tbody>
                </table>
                
                <h2>Legenda stacji</h2>
                <table>
                    <tr>
                        <td class="station-cnc"><strong>CNC</strong> - Cięcie, frezowanie</td>
                        <td class="station-oklejanie"><strong>Oklejanie</strong> - Obrzeża, laminat</td>
                        <td class="station-lakiernia"><strong>Lakiernia</strong> - Malowanie, wykończenie</td>
                        <td class="station-montaz"><strong>Montaż</strong> - Składanie, kontrola jakości</td>
                    </tr>
                </table>
                
                <div class="footer">
                    TECH_modul - Kalendarz produkcji | Wygenerowano: {now}
                </div>
            </div>
        </body>
        </html>
        """
    
    def export_weekly_schedule_pdf(self, data: ProductionCalendarData, 
                                   output_path: str | Path) -> Path:
        """Export weekly schedule to PDF file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        html = self.generate_weekly_schedule(data)
        self._doc.setHtml(html)
        
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(output_path))
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageMargins(QPageLayout.Margins(12, 12, 12, 12), QPageLayout.Unit.Millimeter)
        
        self._doc.print(printer)
        
        return output_path


def export_production_calendar(data: ProductionCalendarData,
                               filename: str | None = None) -> Path:
    """Convenience function to export production calendar."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"kalendarz_produkcji_{timestamp}.pdf"
    
    output_path = get_default_export_dir() / filename
    report = ProductionCalendarPDF()
    return report.export_weekly_schedule_pdf(data, output_path)


@dataclass
class WorkTimeReportData:
    """Data class for work time report."""
    period_start: str = ""
    period_end: str = ""
    worker_name: str = ""
    entries: list[dict] | None = None
    total_hours: float = 0.0
    overtime_hours: float = 0.0
    
    def __post_init__(self):
        if self.entries is None:
            self.entries = []


class WorkTimeReportPDF:
    """Generates PDF work time reports."""
    
    STYLES = """
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 9pt;
            color: #1f2937;
            margin: 0;
            padding: 0;
        }
        .page {
            padding: 15mm 12mm;
            page-break-after: always;
        }
        h1 {
            color: #1e40af;
            font-size: 16pt;
            margin: 0 0 8pt 0;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 6pt;
        }
        h2 {
            color: #374151;
            font-size: 11pt;
            margin: 12pt 0 6pt 0;
        }
        .header-row {
            display: flex;
            justify-content: space-between;
            background: #f3f4f6;
            padding: 10pt;
            border-radius: 6pt;
            margin-bottom: 10pt;
        }
        .header-box {
            text-align: center;
        }
        .label {
            color: #6b7280;
            font-size: 8pt;
            text-transform: uppercase;
        }
        .value {
            font-size: 12pt;
            font-weight: bold;
            color: #1f2937;
        }
        .highlight-box {
            background: #dbeafe;
            border-left: 3pt solid #3b82f6;
            padding: 8pt 12pt;
            margin: 10pt 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 5pt 0;
        }
        th {
            background: #374151;
            color: white;
            padding: 5pt 6pt;
            text-align: left;
            font-size: 8pt;
        }
        td {
            padding: 4pt 6pt;
            border: 1px solid #e5e7eb;
            font-size: 8pt;
        }
        tr:nth-child(even) {
            background: #f9fafb;
        }
        .text-right {
            text-align: right;
        }
        .summary-box {
            background: #fef3c7;
            border: 2pt solid #f59e0b;
            border-radius: 6pt;
            padding: 10pt;
            margin-top: 10pt;
        }
        .footer {
            text-align: center;
            font-size: 7pt;
            color: #9ca3af;
            margin-top: 10pt;
        }
    </style>
    """
    
    def __init__(self):
        self._doc = QTextDocument()
    
    def generate_work_time_report(self, data: WorkTimeReportData) -> str:
        """Generate work time report HTML."""
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # Build entries table
        rows = ""
        total_hours = 0.0
        for entry in (data.entries or []):
            date = _safe(entry.get("date", ""))
            start = _safe(entry.get("start_time", ""))
            end = _safe(entry.get("end_time", ""))
            hours = float(entry.get("hours", 0) or 0)
            project = _safe(entry.get("project", ""))
            notes = _safe(entry.get("notes", ""))
            total_hours += hours
            
            rows += f"""
            <tr>
                <td>{date}</td>
                <td>{start}</td>
                <td>{end}</td>
                <td class="text-right">{hours:.2f}</td>
                <td>{project}</td>
                <td>{notes}</td>
            </tr>
            """
        
        # Calculate stats
        work_days = len(data.entries or [])
        avg_hours = total_hours / work_days if work_days > 0 else 0
        regular_hours = min(total_hours, 160.0)  # Assuming 160h/month
        overtime = max(0, total_hours - 160.0)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            {self.STYLES}
        </head>
        <body>
            <div class="page">
                <h1>⏱ Raport czasu pracy</h1>
                
                <div class="header-row">
                    <div class="header-box">
                        <div class="label">Pracownik</div>
                        <div class="value">{_safe(data.worker_name, 'Wszyscy')}</div>
                    </div>
                    <div class="header-box">
                        <div class="label">Okres od</div>
                        <div class="value">{_safe(data.period_start, '---')}</div>
                    </div>
                    <div class="header-box">
                        <div class="label">Okres do</div>
                        <div class="value">{_safe(data.period_end, '---')}</div>
                    </div>
                </div>
                
                <h2>Szczegóły czasu pracy</h2>
                <table>
                    <thead>
                        <tr>
                            <th style="width: 12%">Data</th>
                            <th style="width: 10%">Start</th>
                            <th style="width: 10%">Koniec</th>
                            <th style="width: 10%">Godziny</th>
                            <th style="width: 25%">Projekt</th>
                            <th style="width: 30%">Uwagi</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows if rows else '<tr><td colspan="6" style="text-align:center;">Brak wpisów</td></tr>'}
                    </tbody>
                </table>
                
                <div class="summary-box">
                    <h2 style="margin-top: 0;">📊 Podsumowanie</h2>
                    <table style="border: none;">
                        <tr style="background: transparent;">
                            <td style="border: none; width: 33%;">
                                <strong>Dni roboczych:</strong> {work_days}
                            </td>
                            <td style="border: none; width: 33%;">
                                <strong>Średnio:</strong> {avg_hours:.2f} h/dzień
                            </td>
                            <td style="border: none; width: 33%;">
                                <strong>Razem godzin:</strong> {total_hours:.2f} h
                            </td>
                        </tr>
                        <tr style="background: transparent;">
                            <td style="border: none;">
                                <strong>Norma:</strong> 160 h
                            </td>
                            <td style="border: none;">
                                <strong>Nadgodziny:</strong> {overtime:.2f} h
                            </td>
                            <td style="border: none;">
                                <strong>Stawka:</strong> {"Normalna" if overtime == 0 else "Z nadgodzinami"}
                            </td>
                        </tr>
                    </table>
                </div>
                
                <div class="footer">
                    Wygenerowano: {now} | TECH_modul - Raport czasu pracy
                </div>
            </div>
        </body>
        </html>
        """
    
    def export_work_time_report_pdf(self, data: WorkTimeReportData,
                                    output_path: str | Path) -> Path:
        """Export work time report to PDF file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        html = self.generate_work_time_report(data)
        self._doc.setHtml(html)
        
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(output_path))
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageMargins(QPageLayout.Margins(12, 12, 12, 12), QPageLayout.Unit.Millimeter)
        
        self._doc.print(printer)
        
        return output_path


def export_work_time_report(data: WorkTimeReportData,
                            filename: str | None = None) -> Path:
    """Convenience function to export work time report."""
    if filename is None:
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in data.worker_name) or "pracownik"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"czas_pracy_{safe_name}_{timestamp}.pdf"
    
    output_path = get_default_export_dir() / filename
    report = WorkTimeReportPDF()
    return report.export_work_time_report_pdf(data, output_path)


