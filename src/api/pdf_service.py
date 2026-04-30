from fpdf import FPDF
from datetime import datetime
import os

class TechModulOfferPDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Load local Arial TTF for UTF-8 and Polish chars support
        font_path = "c:/Windows/Fonts/arial.ttf"
        font_bold_path = "c:/Windows/Fonts/arialbd.ttf"
        font_italic_path = "c:/Windows/Fonts/ariali.ttf"
        
        try:
            if os.path.exists(font_path):
                self.add_font("ArialText", "", font_path, uni=True)
                if os.path.exists(font_bold_path):
                    self.add_font("ArialText", "B", font_bold_path, uni=True)
                if os.path.exists(font_italic_path):
                    self.add_font("ArialText", "I", font_italic_path, uni=True)
                self.custom_font = "ArialText"
            else:
                self.custom_font = "helvetica"
        except Exception:
            self.custom_font = "helvetica"

    def header(self):
        # Logo placeholder
        self.set_fill_color(30, 64, 175) # Dark blue
        self.rect(0, 0, 210, 40, 'F')
        
        self.set_font(self.custom_font, "B", 24)
        self.set_text_color(255, 255, 255)
        self.cell(0, 20, "TECH MODUŁ", ln=True, align="C")
        self.set_font(self.custom_font, "I", 10)
        self.cell(0, 5, "PROFESSIONAL FURNITURE SYSTEMS", ln=True, align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.custom_font, "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Strona {self.page_no()}/{{nb}} | Wygenerowano: {datetime.now().strftime('%d.%m.%Y %H:%M')}", align="C")

def generate_offer_pdf(project_data: dict, output_path: str):
    pdf = TechModulOfferPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    font = pdf.custom_font
    
    # Project Header
    pdf.set_font(font, "B", 16)
    pdf.set_text_color(31, 41, 55)
    pdf.cell(0, 15, f"OFERTA: {project_data.get('title', '---')}", ln=True)
    
    # Info Box
    pdf.set_fill_color(243, 244, 246)
    pdf.rect(10, 60, 190, 30, 'F')
    pdf.set_font(font, "B", 10)
    pdf.set_xy(15, 65)
    pdf.cell(40, 5, "KLIENT:")
    pdf.cell(60, 5, "KOD PROJEKTU:")
    pdf.cell(0, 5, "DATA:")
    pdf.ln(6)
    pdf.set_font(font, "", 12)
    pdf.set_x(15)
    pdf.cell(40, 10, str(project_data.get('client_name', '---')))
    pdf.cell(60, 10, f"PRJ-{project_data.get('id', '0'):04}")
    pdf.cell(0, 10, datetime.now().strftime("%d.%m.%Y"))
    
    pdf.ln(30)
    
    # Table Header
    pdf.set_fill_color(31, 41, 55)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(font, "B", 10)
    pdf.cell(90, 10, " NAZWA MODUŁU / OPIS", border=1, fill=True)
    pdf.cell(30, 10, " WYMIARY", border=1, fill=True, align="C")
    pdf.cell(30, 10, " ILOŚĆ", border=1, fill=True, align="C")
    pdf.cell(0, 10, " CENA NETTO", border=1, fill=True, align="R")
    pdf.ln()
    
    # Table Rows
    pdf.set_text_color(31, 41, 55)
    pdf.set_font(font, "", 10)
    
    modules = project_data.get("modules", [])
    if not modules:
        pdf.cell(0, 10, "Brak zdefiniowanych modułów w ofercie.", border=1, align="C")
        pdf.ln()
    else:
        for mod in modules:
            name = mod.get("name", "Szafka")
            dims = f"{mod.get('width', 0)}x{mod.get('height', 0)}x{mod.get('depth', 0)}"
            pdf.cell(90, 10, f" {name}", border=1)
            pdf.cell(30, 10, f" {dims}", border=1, align="C")
            pdf.cell(30, 10, " 1 szt.", border=1, align="C")
            pdf.cell(0, 10, f"{mod.get('price_net', 0):.2f} PLN ", border=1, align="R")
            pdf.ln()

    # --- MATERIAL STATS SECTION ---
    pdf.ln(10)
    pdf.set_font(font, "B", 12)
    pdf.set_text_color(30, 64, 175)
    pdf.cell(0, 10, "ZESTAWIENIE MATERIAŁOWE (BOM)", ln=True)
    pdf.set_draw_color(30, 64, 175)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(31, 41, 55)
    pdf.set_font(font, "B", 9)
    pdf.cell(80, 8, " MATERIAŁ / PŁYTA", border=1, fill=True)
    pdf.cell(40, 8, " ILOŚĆ SZT.", border=1, fill=True, align="C")
    pdf.cell(40, 8, " POWIERZCHNIA", border=1, fill=True, align="C")
    pdf.cell(0, 8, " KOSZT SZAC.", border=1, fill=True, align="R")
    pdf.ln()

    pdf.set_font(font, "", 9)
    material_stats = project_data.get("material_stats", [])
    for mat in material_stats:
        pdf.cell(80, 8, f" {mat.get('name')}", border=1)
        pdf.cell(40, 8, f" {mat.get('parts_count')} el.", border=1, align="C")
        pdf.cell(40, 8, f" {mat.get('total_m2'):.2f} m2", border=1, align="C")
        pdf.cell(0, 8, f"{mat.get('cost'):.2f} PLN ", border=1, align="R")
        pdf.ln()

    if not material_stats:
        pdf.cell(0, 8, "Brak szczegółowych danych materiałowych.", border=1, align="C")
        pdf.ln()

    pdf.ln(5)
    
    # --- PRICING BREAKDOWN ---
    pdf.set_font(font, "B", 10)
    pdf.cell(0, 8, "Analiza Kosztów Produkcji:", ln=True)
    pdf.set_font(font, "", 9)
    pricing = project_data.get("pricing_breakdown", {})
    pdf.cell(50, 6, f"Sumaryczny koszt materiałów:")
    pdf.cell(0, 6, f"{pricing.get('materials_cost', 0):.2f} PLN", ln=True)
    pdf.cell(50, 6, f"Szacowany koszt robocizny:")
    pdf.cell(0, 6, f"{pricing.get('labor_cost', 0):.2f} PLN", ln=True)
    pdf.cell(50, 6, f"Narzut handlowy (Marża):")
    pdf.cell(0, 6, f"{pricing.get('margin_percent', 0):.1f}%", ln=True)

    pdf.ln(10)
    
    # Totals
    pdf.set_x(120)
    pdf.set_font(font, "B", 12)
    pdf.cell(40, 10, "SUMA NETTO:")
    pdf.cell(0, 10, f"{project_data.get('total_net', 0):.2f} PLN", align="R")
    pdf.ln()
    pdf.set_x(120)
    pdf.cell(40, 10, "VAT 23%:")
    pdf.cell(0, 10, f"{project_data.get('vat', 0):.2f} PLN", align="R")
    pdf.ln()
    
    # Final Total
    pdf.set_x(120)
    pdf.set_fill_color(30, 64, 175)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(font, "B", 14)
    pdf.cell(40, 15, " DO ZAPŁATY:", fill=True)
    pdf.cell(0, 15, f"{project_data.get('total_gross', 0):.2f} PLN ", fill=True, align="R")
    
    pdf.ln(30)
    pdf.set_text_color(31, 41, 55)
    pdf.set_font(font, "I", 9)
    pdf.multi_cell(0, 5, "Niniejsza oferta ma charakter informacyjny i nie stanowi oferty handlowej w rozumieniu Art. 66 par. 1 Kodeksu Cywilnego. Termin realizacji do ustalenia po wpłacie zadatku.")

    pdf.output(output_path)
    return output_path
