from __future__ import annotations

from dataclasses import dataclass, replace
from io import BytesIO
from pathlib import Path
import re
import statistics
import subprocess
import tempfile
from typing import Any


_MONEY_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[ .]\d{3})*(?:[.,]\d{2})|\d+[.,]\d{2})(?!\d)")
_DATE_RE = re.compile(
    r"(\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4})"
)
_VAT_RE = re.compile(r"(?P<vat>\d{1,2}(?:[.,]\d+)?)\s*%")
_NIP_RE = re.compile(
    r"(?i)\bnip\b[^0-9]{0,10}((?:\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2})|\d{10})(?!\d)"
)
MSI_PROJECT_NIP = "7123413192"

_UNIT_ALIASES: dict[str, str] = {
    "szt": "szt",
    "szt.": "szt",
    "sztuk": "szt",
    "sztuka": "szt",
    "m2": "m2",
    "m^2": "m2",
    "mÂ˛": "m2",
    "mkw": "m2",
    "mkw.": "m2",
    "m": "m",
    "m.": "m",
    "mb": "mb",
    "mb.": "mb",
    "m.b.": "mb",
    "metr": "m",
    "metry": "m",
    "kg": "kg",
    "kg.": "kg",
    "g": "g",
    "g.": "g",
    "kpl": "kpl",
    "kpl.": "kpl",
    "komplet": "kpl",
    "kompl": "kpl",
    "kompl.": "kpl",
    "op": "op",
    "op.": "op",
    "opak": "op",
    "opak.": "op",
    "opakowanie": "op",
    "l": "l",
    "l.": "l",
    "litr": "l",
    "litr.": "l",
    "ml": "ml",
    "ml.": "ml",
    "rolka": "rol",
    "rolki": "rol",
    "rol": "rol",
    "rol.": "rol",
    "pac": "pac",
    "pac.": "pac",
    "paczka": "pac",
    "paczki": "pac",
    "para": "para",
    "par": "para",
    "set": "set",
    "ark": "ark",
    "ark.": "ark",
    "arkusz": "ark",
    "karton": "karton",
    "kart": "karton",
    "pal": "pal",
    "palet": "pal",
    "paleta": "pal",
    "pkt": "pkt",
    "pkt.": "pkt",
}
_SUPPORTED_UNITS = tuple(sorted(set(_UNIT_ALIASES.values())))
_UNIT_PATTERN = "|".join(sorted((re.escape(key) for key in _UNIT_ALIASES.keys()), key=len, reverse=True))
_QTY_UNIT_RE = re.compile(
    rf"(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>{_UNIT_PATTERN})(?=\s|$|[;,:])",
    re.I,
)

_SUPPLIER_TEMPLATES: dict[str, dict[str, Any]] = {
    "pakdrew": {
        "name": "Pakdrew",
        "tokens": ("pakdrew",),
        "header_tokens": ("lp", "nazwa", "ilosc", "jedn", "netto", "brutto", "vat"),
        "require_qty_unit": True,
        "default_material_type": "plyta",
    },
    "wurth": {
        "name": "Wurth",
        "tokens": ("wurth", "wurth polska", "wurthpolska"),
        "header_tokens": ("art.nr", "indeks", "nazwa", "ilosc", "cena", "wartosc", "vat"),
        "require_qty_unit": True,
        "default_material_type": "okucie",
    },
    "tabal": {
        "name": "Tabal",
        "tokens": ("tabal",),
        "header_tokens": ("lp", "nazwa", "ilosc", "jednostka", "cena", "netto", "brutto", "vat"),
        "require_qty_unit": True,
        "default_material_type": "plyta",
    },
    "artex": {
        "name": "Artex",
        "tokens": ("artex",),
        "header_tokens": ("lp", "nazwa", "ilosc", "jedn", "cena", "netto", "brutto", "vat"),
        "require_qty_unit": True,
        "default_material_type": "plyta",
    },
    "ita": {
        "name": "ITA",
        "tokens": (" ita ", "ita ", " ita", "ita sp", "ita polska", "itapolska"),
        "header_tokens": ("lp", "nazwa", "ilosc", "jedn", "cena", "wartosc", "vat", "netto", "brutto"),
        "require_qty_unit": True,
        "default_material_type": "plyta",
    },
    "ica": {
        "name": "ICA",
        "tokens": ("ica polska", "ica group", "icapolska"),
        "header_tokens": ("nazwa produktu", "ilosc", "cena", "netto", "vat", "brutto"),
        "require_qty_unit": True,
        "default_material_type": "klej",
    },
    "gorpak": {
        "name": "GOR-PAK",
        "tokens": ("gor-pak", "gor pak", "gorpak"),
        "header_tokens": ("nazwa", "ilosc", "cena", "netto", "vat", "brutto"),
        "require_qty_unit": False,
        "default_material_type": "folia",
    },
    "mielec": {
        "name": "Mielec Serwis",
        "tokens": ("mielec serwis",),
        "header_tokens": ("nazwa", "ilosc", "cena", "netto", "vat", "brutto"),
        "require_qty_unit": False,
        "default_material_type": "serwis",
    },
    "adler": {
        "name": "ADLER",
        "tokens": ("adler-polska", "adler polska", "adler-lakiery", "adler lakiery"),
        "header_tokens": ("nazwa", "ilosc", "cena", "netto", "vat", "brutto"),
        "require_qty_unit": True,
        "default_material_type": "lakier",
    },
}


@dataclass(frozen=True)
class InvoiceLineItem:
    name: str
    quantity: float
    unit: str
    unit_price: float
    total_price: float
    material_type: str
    thickness_mm: str
    raw_line: str
    unit_price_net: float = 0.0
    unit_price_gross: float = 0.0
    total_price_net: float = 0.0
    total_price_gross: float = 0.0
    vat_amount: float = 0.0
    vat_rate: str = ""
    price_basis: str = "unknown"
    parse_source: str = "generic"


@dataclass(frozen=True)
class InvoiceParseResult:
    source_path: Path
    invoice_number: str
    invoice_date: str
    supplier: str
    text_length: int
    items: tuple[InvoiceLineItem, ...]
    price_basis: str = "unknown"
    total_net: float = 0.0
    total_vat: float = 0.0
    total_gross: float = 0.0
    amount_due: float = 0.0
    currency: str = "PLN"
    buyer_nip: str = ""
    is_msi_project_invoice: bool = False
    extraction_method: str = "text"
    ocr_confidence: float = 0.0
    supplier_template: str = ""
    ai_fallback_used: bool = False
    ai_confidence: float = 0.0
    ai_model: str = ""
    ai_error: str = ""


@dataclass(frozen=True)
class _PricePair:
    unit_price: float
    total_price: float


def _to_float(value: str) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    text = text.replace(" ", "").replace("\u00a0", "")
    text = text.replace(",", ".")
    if text.count(".") > 1:
        parts = text.split(".")
        text = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(text)
    except Exception:
        return 0.0


def _to_qty_float(value: str, unit: str = "") -> float:
    raw = str(value or "").strip().replace(" ", "").replace("\u00a0", "")
    unit_norm = normalize_unit(unit)
    if raw and "," not in raw and re.match(r"^\d{1,3}\.\d{3}$", raw) and unit_norm == "szt":
        try:
            return float(raw.replace(".", ""))
        except Exception:
            pass
    return _to_float(raw)


def _normalize_date(value: str) -> str:
    raw = str(value or "").strip().replace(".", "-").replace("/", "-")
    if not raw:
        return ""
    parts = [p for p in raw.split("-") if p]
    if len(parts) != 3:
        return ""
    try:
        if len(parts[0]) == 4:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
        else:
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2])
            if year < 100:
                year += 2000
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return ""
        return f"{year:04d}-{month:02d}-{day:02d}"
    except Exception:
        return ""


def _cleanup_name(text: str) -> str:
    name = re.sub(r"\s+", " ", str(text or "").strip())
    name = re.sub(r"^\d+[.)-]?\s*", "", name)
    return name.strip(" -;,.")


def supported_invoice_units() -> tuple[str, ...]:
    return _SUPPORTED_UNITS


def normalize_unit(value: str) -> str:
    raw = str(value or "").strip().lower().replace(" ", "")
    if not raw:
        return ""
    raw = raw.replace("Â˛", "2")
    normalized = _UNIT_ALIASES.get(raw, raw)
    return normalized.strip(".")


def _guess_material_type(name: str) -> str:
    low = str(name or "").strip().lower()
    rules = (
        ("okleina", ("okleina", "obrzeze", "obrzez")),
        ("okucie", ("zawias", "prowadnic", "wkret", "sruba", "uchwyt", "tandembox", "blum")),
        ("lakier", ("lakier", "farba", "bejc")),
        ("profil", ("profil", "listwa", "ceownik", "katownik")),
        ("front", ("front", "drzwicz", "drzwi")),
        ("plyta", ("plyta", "mdf", "hdf", "laminat", "sklejka", "blat")),
        ("korpus", ("korpus",)),
    )
    for material_type, tokens in rules:
        if any(token in low for token in tokens):
            return material_type
    return "plyta"


def _extract_thickness(name: str) -> str:
    low = str(name or "").lower()
    match = re.search(r"(\d{1,2}(?:[.,]\d+)?)\s*mm\b", low)
    if match:
        return str(match.group(1)).replace(",", ".")
    match = re.search(r"\bgr(?:\.|ubosc)?\s*(\d{1,2}(?:[.,]\d+)?)\b", low)
    if match:
        return str(match.group(1)).replace(",", ".")
    return ""


def _extract_invoice_number(text: str) -> str:
    def _is_valid_invoice_no(candidate: str) -> bool:
        value = str(candidate or "").strip().upper()
        if len(value) < 4 or len(value) > 40:
            return False
        if not any(ch.isdigit() for ch in value):
            return False
        if any(bad in value for bad in ("MSIPROJECT", "ODDZIAL", "SPRZEDAWCA", "NABYWCA", "WURTHPOLSKA")):
            return False
        has_sep = "/" in value or "-" in value
        compact = re.sub(r"[^A-Z0-9]", "", value)
        if not has_sep and not re.match(r"^[A-Z]{1,4}\d{3,}$", compact):
            return False
        return True

    def _is_date_like(value: str) -> bool:
        return bool(re.match(r"^\d{4}[-./]\d{1,2}[-./]\d{1,2}$", value.strip()))

    patterns = (
        # "Nr 1097/O/26/FVS (MAG)" â€” standalone Nr prefix (Symfonia Handel, EKOMAR, etc.)
        re.compile(r"(?im)^Nr\s+([A-Z0-9][A-Z0-9/\-.]{3,})\b"),
        re.compile(r"(?im)\bNr\s+([A-Z0-9][A-Z0-9/\-.]{3,})\b"),
        re.compile(r"(?im)\bnr\s*faktury\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-.]{2,})"),
        re.compile(
            r"(?im)\bfaktura(?:\s*vat)?[ \t]*(?:nr|numer|no|#)[ \t]*[:\-]?[ \t]*([A-Z0-9][A-Z0-9/\-.]{2,})"
        ),
    )
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            candidate = str(match.group(1)).strip().strip(".,;:")
            if (
                candidate.lower() not in {"vat", "faktura"}
                and not _is_date_like(candidate)
                and _is_valid_invoice_no(candidate)
            ):
                return candidate
    fallback = re.search(
        r"(?im)\b(?:nr|numer)\s*[:\-]?\s*((?:FA|FS|FV)[A-Z0-9/-]{4,})\b",
        str(text or ""),
    )
    if fallback:
        candidate = str(fallback.group(1)).strip().strip(".,;:")
        if _is_valid_invoice_no(candidate):
            return candidate
    # Pakdrew/ADLER style: bare FS/000985/03/2026//MLU without "Nr" prefix
    # (OCR often shows "Faktura\n7 FS/..." or just "FS/XXXXXX/...")
    bare = re.search(
        r"(?im)(?:^|(?<=\s)|(?<=\n))\s*\d*\s*((?:FS|FA|FV|FVS|FS)[/]\d{3,}[A-Z0-9/\-.]{4,})",
        str(text or ""),
    )
    if bare:
        candidate = str(bare.group(1)).strip().strip(".,;:")
        if _is_valid_invoice_no(candidate):
            return candidate
    # ADLER style: "Faktura sprzedaży Nr. : 80035498" — czysto numeryczne ID ≥6 cyfr
    adler = re.search(
        r"(?im)\bfaktura\b[^\n]{0,30}(?:nr\.?|numer\.?)\s*[:\-]?\s*(\d{6,})",
        str(text or ""),
    )
    if adler:
        candidate = str(adler.group(1)).strip()
        # Dla długich czysto numerycznych numerów (styl ADLER) pomijamy wymóg liter/separatora.
        if len(candidate) >= 6 and candidate.isdigit():
            return candidate
        if _is_valid_invoice_no(candidate):
            return candidate
    return ""


def _detect_supplier_template(text: str) -> str:
    low = f" {str(text or '').lower()} "
    for key, cfg in _SUPPLIER_TEMPLATES.items():
        tokens = tuple(cfg.get("tokens", ()))
        if any(str(token or "").lower() in low for token in tokens):
            return key
    return ""


def _template_name(key: str) -> str:
    cfg = _SUPPLIER_TEMPLATES.get(str(key or "").strip().lower(), {})
    return str(cfg.get("name", "") or "").strip()


def _template_from_supplier_name(name: str) -> str:
    low = f" {str(name or '').strip().lower()} "
    for key, cfg in _SUPPLIER_TEMPLATES.items():
        tokens = tuple(cfg.get("tokens", ()))
        if any(str(token or "").lower() in low for token in tokens):
            return key
    return ""


def _normalize_supplier_name(name: str, text: str) -> str:
    explicit = str(name or "").strip()
    # Usuń artefakty OCR z końca nazwy: "|", "[Data wystawienia:...", nawiasy itp.
    explicit = re.sub(r"\s*\|.*$", "", explicit).strip()
    explicit = re.sub(r"\s*\[.*$", "", explicit).strip()
    explicit = re.sub(r"\s*\(.*$", "", explicit).strip()
    explicit_key = _template_from_supplier_name(explicit)
    if explicit_key:
        return _template_name(explicit_key)
    text_key = _detect_supplier_template(text)
    if text_key:
        return _template_name(text_key)
    return explicit


def _prepare_line_for_supplier(raw_line: str, template_key: str) -> str:
    line = str(raw_line or "").strip()
    if not line:
        return ""
    key = str(template_key or "").strip().lower()
    if key in {"pakdrew", "wurth", "tabal", "artex", "ita"}:
        line = line.replace("\t", " ").replace("|", " ").replace(";", " ")
    line = re.sub(r"\s+", " ", line).strip()
    return line


def _template_config(template_key: str) -> dict[str, Any]:
    return dict(_SUPPLIER_TEMPLATES.get(str(template_key or "").strip().lower(), {}))


def _is_supplier_header_line(line: str, template_key: str) -> bool:
    low = str(line or "").strip().lower()
    if not low:
        return True
    cfg = _template_config(template_key)
    header_tokens = tuple(str(x or "").strip().lower() for x in cfg.get("header_tokens", ()))
    if header_tokens and sum(1 for token in header_tokens if token and token in low) >= 2:
        return True
    # Common OCR table noise
    if any(token in low for token in ("strona", "razem", "podsumowanie", "wartosc netto", "wartosc brutto")):
        return True
    return False


def _sanitize_template_item_name(name: str, template_key: str) -> str:
    value = _cleanup_name(name)
    if not value:
        return ""
    key = str(template_key or "").strip().lower()
    if key in {"wurth", "pakdrew", "tabal", "artex", "ita"}:
        # Remove leading index/code blocks often present before item name.
        value = re.sub(r"^[A-Z0-9][A-Z0-9.\-_/]{2,}\s+", "", value)
        value = re.sub(r"^\d{6,}\s+", "", value)
    return _cleanup_name(value)


def _is_template_name_allowed(value: str) -> bool:
    text = _cleanup_name(value)
    if not text or sum(1 for ch in text if ch.isalpha()) < 3:
        return False
    low = text.lower()
    blocked = (
        "sprzedawca",
        "nabywca",
        "faktura",
        "nip",
        "odpowiedzialnoscia",
        "msi project",
        "zaplacono",
        "razem",
        "wartosc",
        "kwota",
        "cn/pkwiu",
        "nazwatowaru",
        "podatek",
        "vat",
        "ilosc",
        "hlose",
        "llosc",
        "lloscj.m",
        "forma platnosci",
        "www.",
    )
    if any(token in low for token in blocked):
        return False
    return True


def _material_type_for_supplier(name: str, template_key: str, fallback: str) -> str:
    guessed = str(fallback or "").strip().lower() or _guess_material_type(name)
    cfg = _template_config(template_key)
    default_typ = str(cfg.get("default_material_type", "") or "").strip().lower()
    if not default_typ:
        return guessed
    if guessed not in {"", "plyta"}:
        return guessed
    return default_typ


def _parse_line_item_template(line: str, default_basis: str, template_key: str) -> InvoiceLineItem | None:
    raw_line = str(line or "").strip()
    if len(raw_line) < 6 or _is_summary_line(raw_line):
        return None
    if _is_supplier_header_line(raw_line, template_key):
        return None

    cfg = _template_config(template_key)
    require_qty_unit = bool(cfg.get("require_qty_unit", True))
    qty_match = _QTY_UNIT_RE.search(raw_line)
    if require_qty_unit and qty_match is None:
        return None

    item = _parse_line_item(raw_line, default_basis)
    if item is None:
        return None

    sanitized_name = _sanitize_template_item_name(item.name, template_key)
    if not _is_template_name_allowed(sanitized_name):
        return None

    material_type = _material_type_for_supplier(
        sanitized_name,
        template_key,
        item.material_type,
    )
    return replace(
        item,
        name=sanitized_name,
        material_type=material_type,
        raw_line=raw_line,
        parse_source=f"template:{template_key}",
    )


def _join_ocr_tokens_into_lines(tokens: list[dict[str, Any]]) -> str:
    if not tokens:
        return ""
    heights = [float(row.get("h", 0.0) or 0.0) for row in tokens if float(row.get("h", 0.0) or 0.0) > 0.0]
    if heights:
        median_h = statistics.median(heights)
        threshold = max(6.0, float(median_h) * 0.40)
    else:
        median_h = 12.0
        threshold = 8.0

    sorted_tokens = sorted(tokens, key=lambda row: (float(row.get("y", 0.0) or 0.0), float(row.get("x", 0.0) or 0.0)))
    groups: list[dict[str, Any]] = []
    for row in sorted_tokens:
        y = float(row.get("y", 0.0) or 0.0)
        if not groups:
            groups.append({"y": y, "tokens": [row]})
            continue
        if abs(y - float(groups[-1]["y"])) <= threshold:
            groups[-1]["tokens"].append(row)
            current_count = len(groups[-1]["tokens"])
            groups[-1]["y"] = ((float(groups[-1]["y"]) * (current_count - 1)) + y) / current_count
        else:
            groups.append({"y": y, "tokens": [row]})

    lines: list[str] = []
    for group in groups:
        pieces = sorted(group["tokens"], key=lambda row: float(row.get("x", 0.0) or 0.0))
        row_parts: list[str] = []
        prev_right: float | None = None
        for piece in pieces:
            token_text = str(piece.get("text", "") or "").strip()
            if not token_text:
                continue
            x = float(piece.get("x", 0.0) or 0.0)
            x2 = float(piece.get("x2", x) or x)
            if prev_right is not None:
                gap = x - prev_right
                row_parts.append(" | " if gap > max(20.0, float(median_h) * 0.9) else " ")
            row_parts.append(token_text)
            prev_right = max(prev_right or x2, x2)
        line = "".join(row_parts)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


_TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
_TESSERACT_LANGS = "pol+eng"


def _run_tesseract_for_image_path(image_path: Path) -> str:
    cmd = [
        _TESSERACT_CMD,
        str(image_path),
        "stdout",
        "-l",
        _TESSERACT_LANGS,
        "--psm",
        "6",
        "--oem",
        "3",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=False,
            timeout=60,
            check=False,
        )
    except Exception:
        return ""
    if proc.returncode != 0:
        return ""
    raw = bytes(proc.stdout or b"")
    if not raw:
        return ""
    try:
        return raw.decode("utf-8", errors="ignore").strip()
    except Exception:
        try:
            return raw.decode("cp1250", errors="ignore").strip()
        except Exception:
            return ""


def _ocr_image_tesseract(img: Any) -> str:
    """Run local tesseract.exe on a PIL image, auto-correcting landscape scans."""
    if not Path(_TESSERACT_CMD).exists():
        return ""
    with tempfile.TemporaryDirectory(prefix="ocr_invoice_") as tmp_dir:
        base = Path(tmp_dir) / "page.png"
        try:
            img.save(base, format="PNG")
        except Exception:
            return ""
        variants: list[Path] = [base]
        try:
            w, h = img.size
        except Exception:
            w, h = (0, 0)
        if w > h:
            try:
                img_cw = img.rotate(270, expand=True)
                cw_path = Path(tmp_dir) / "page_cw.png"
                img_cw.save(cw_path, format="PNG")
                variants.append(cw_path)
            except Exception:
                pass
            try:
                img_ccw = img.rotate(90, expand=True)
                ccw_path = Path(tmp_dir) / "page_ccw.png"
                img_ccw.save(ccw_path, format="PNG")
                variants.append(ccw_path)
            except Exception:
                pass
        best_text = ""
        best_score = -1
        for path in variants:
            out = _run_tesseract_for_image_path(path)
            if not out:
                continue
            score = sum(1 for ch in out if ch.isalnum())
            if score > best_score:
                best_text = out
                best_score = score
        return best_text.strip()


def _extract_pdf_text_with_ocr(payload: bytes) -> tuple[str, float]:
    """Extract text from a scanned PDF using local tesseract.exe.

    Works without pytesseract and falls back to rendered pages when
    embedded image extraction is not available.
    """
    try:
        from PIL import Image  # type: ignore
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return "", 0.0

    if not Path(_TESSERACT_CMD).exists():
        return "", 0.0
    try:
        version_proc = subprocess.run(
            [_TESSERACT_CMD, "--version"],
            capture_output=True,
            text=False,
            timeout=10,
            check=False,
        )
        if version_proc.returncode != 0:
            return "", 0.0
    except Exception:
        return "", 0.0

    page_texts: list[str] = []
    try:
        reader = PdfReader(BytesIO(payload))
        fitz_doc = None
        try:
            import fitz  # type: ignore
        except Exception:
            fitz = None  # type: ignore[assignment]
        else:
            try:
                fitz_doc = fitz.open(stream=payload, filetype="pdf")
            except Exception:
                fitz_doc = None

        for page_index, page in enumerate(reader.pages):
            page_best = ""
            try:
                page_imgs = page.images
            except Exception:
                page_imgs = []
            for embedded in page_imgs[:3]:
                try:
                    img = Image.open(BytesIO(embedded.data))
                    page_text = _ocr_image_tesseract(img)
                except Exception:
                    page_text = ""
                if len(page_text) > len(page_best):
                    page_best = page_text

            if (not page_best or len(page_best) < 40) and fitz_doc is not None and page_index < fitz_doc.page_count:
                try:
                    fitz_page = fitz_doc.load_page(page_index)
                    mat = fitz.Matrix(2.0, 2.0)
                    pix = fitz_page.get_pixmap(matrix=mat, alpha=False)
                    img = Image.open(BytesIO(pix.tobytes("png")))
                    rendered_text = _ocr_image_tesseract(img)
                except Exception:
                    rendered_text = ""
                if len(rendered_text) > len(page_best):
                    page_best = rendered_text

            if page_best.strip():
                page_texts.append(page_best.strip())
    except Exception:
        return "", 0.0

    full_text = "\n\n".join(page_texts).strip()
    if not full_text:
        return "", 0.0
    word_chars = sum(1 for c in full_text if c.isalpha())
    total_chars = max(1, len(full_text))
    confidence = min(1.0, word_chars / total_chars)
    return full_text, confidence


def _extract_invoice_date(text: str) -> str:
    hints = (
        "data sprzedazy",
        "data sprzeda",
        "data wystawienia",
        "data zakupu",
        "data",
    )
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    for hint in hints:
        for line in lines:
            if hint not in line.lower():
                continue
            match = _DATE_RE.search(line)
            if match:
                normalized = _normalize_date(str(match.group(1)))
                if normalized:
                    return normalized
    for line in lines:
        match = _DATE_RE.search(line)
        if match:
            normalized = _normalize_date(str(match.group(1)))
            if normalized:
                return normalized
    return ""


def _extract_supplier(text: str) -> str:
    template_key = _detect_supplier_template(text)
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    for idx, line in enumerate(lines):
        low = line.lower()
        if not any(token in low for token in ("sprzedawca", "wystawca", "dostawca")):
            continue
        match_inline = re.search(
            r"(?i)(?:sprzedawca|wystawca|dostawca)\s*[:\-]\s*(.+)$",
            line,
        )
        if match_inline:
            inline = str(match_inline.group(1) or "").strip()
            inline_low = inline.lower()
            # Odrzuć jeśli wyciągniętą treścią jest "Nabywca:" lub podobne — dwukolumnowy OCR
            if any(tok in inline_low for tok in ("nabywca", "odbiorca", "kupujacy", "buyer")):
                inline = ""
            inline_alpha = sum(1 for ch in inline if ch.isalpha())
            inline_digits = sum(1 for ch in inline if ch.isdigit())
            if inline and inline_alpha >= 3 and inline_digits <= max(6, inline_alpha):
                return _normalize_supplier_name(inline[:160], text)
        if idx + 1 < len(lines):
            nxt = lines[idx + 1].strip()
            # W dwukolumnowym OCR: "HEMPLAB SP. Z O.O. MSI PROJECT SP. Z O.O."
            # — bierz tylko część przed nazwą nabywcy (MSI PROJECT lub słowami-nabywcy)
            buyer_cut = re.search(r"\bMSI PROJECT\b|\bNABYWCA\b|\bODBIORCA\b", nxt, re.I)
            if buyer_cut:
                nxt = nxt[:buyer_cut.start()].strip()
            nxt_alpha = sum(1 for ch in nxt if ch.isalpha())
            nxt_digits = sum(1 for ch in nxt if ch.isdigit())
            if ":" not in nxt and len(nxt) > 2 and len(nxt.split()) <= 10 and nxt_alpha >= 3 and nxt_digits <= max(6, nxt_alpha):
                return _normalize_supplier_name(nxt[:160], text)
    if template_key:
        return _template_name(template_key)
    return ""


def _extract_nip_digits(value: str) -> str:
    text = str(value or "")
    for match in _NIP_RE.finditer(text):
        digits = "".join(ch for ch in str(match.group(1) or "") if ch.isdigit())
        if len(digits) == 10:
            return digits
    return ""


def _extract_all_nips(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in _NIP_RE.finditer(str(text or "")):
        digits = "".join(ch for ch in str(match.group(1) or "") if ch.isdigit())
        if len(digits) != 10 or digits in seen:
            continue
        seen.add(digits)
        found.append(digits)
    return found


def _extract_buyer_nip(text: str) -> str:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    buyer_tokens = ("nabywca", "odbiorca", "kupujacy", "buyer")
    seller_tokens = ("sprzedawca", "wystawca", "dostawca", "seller")

    for idx, line in enumerate(lines):
        low = line.lower()
        if not any(token in low for token in buyer_tokens):
            continue
        block = " ".join(lines[idx : min(len(lines), idx + 3)])
        candidate = _extract_nip_digits(block)
        if candidate:
            return candidate

    for idx, line in enumerate(lines):
        if "nip" not in line.lower():
            continue
        start = max(0, idx - 1)
        stop = min(len(lines), idx + 2)
        context_lines = lines[start:stop]
        context = " ".join(context_lines).lower()
        has_seller = any(token in context for token in seller_tokens)
        has_buyer = any(token in context for token in buyer_tokens)
        if has_seller and not has_buyer:
            continue
        candidate = _extract_nip_digits(" ".join(context_lines))
        if candidate:
            return candidate

    all_nips = _extract_all_nips(text)
    if len(all_nips) == 1:
        return all_nips[0]
    return ""


def _detect_price_basis(text: str) -> str:
    low = str(text or "").lower()
    has_net = any(token in low for token in ("cena netto", "wartosc netto", "razem netto", "suma netto"))
    has_gross = any(token in low for token in ("cena brutto", "wartosc brutto", "razem brutto", "suma brutto"))
    if has_net and has_gross:
        return "mixed"
    if has_gross:
        return "brutto"
    if has_net:
        return "netto"
    return "unknown"


def _extract_currency(text: str) -> str:
    low = str(text or "").lower()
    if "eur" in low:
        return "EUR"
    if "usd" in low:
        return "USD"
    return "PLN"


def _extract_last_money(line: str) -> float:
    values: list[float] = []
    date_spans = [(m.start(), m.end()) for m in _DATE_RE.finditer(str(line or ""))]
    for match in _MONEY_RE.finditer(str(line or "")):
        span = (match.start(), match.end())
        if any(_spans_overlap(span, ds) for ds in date_spans):
            continue
        end = match.end()
        after = str(line[end:end + 1] if end < len(line) else "")
        if after == "%":
            continue
        values.append(_to_float(match.group(1)))
    values = [v for v in values if v > 0]
    return values[-1] if values else 0.0


def _extract_money_after_token(line: str, token: str) -> float | None:
    raw_line = str(line or "")
    low = raw_line.lower()
    token_low = str(token or "").strip().lower()
    if not token_low:
        return None
    idx = low.find(token_low)
    if idx < 0:
        return None
    tail = raw_line[idx + len(token_low) :]
    for match in _MONEY_RE.finditer(tail):
        end = match.end()
        after = tail[end:end + 1] if end < len(tail) else ""
        if after == "%":
            continue
        return _to_float(match.group(1))
    return None


def _is_totals_candidate_line(low: str) -> bool:
    text = str(low or "").strip().lower()
    if not text:
        return False
    summary_markers = (
        "razem",
        "suma",
        "podsumowanie",
        "kwota",
        "naleznosc",
        "do zaplaty",
        "pozostalo",
        "wartosc",      # "Wartosc netto/brutto" bez diakrytyków
        "warto\u015b",  # "Wartość netto/brutto" z ó/ś (UTF-8)
    )
    if any(marker in text for marker in summary_markers):
        return True
    if text.startswith(("netto", "brutto", "vat", "podatek")):
        return True
    # "23% VAT 690,82" — VAT w środku linii
    if re.search(r"\bvat\b", text):
        return True
    return False


def _extract_totals(
    text: str,
    *,
    fallback_total: float = 0.0,
    fallback_net: float = 0.0,
    fallback_gross: float = 0.0,
) -> tuple[float, float, float, float]:
    total_net = 0.0
    total_gross = 0.0
    total_vat = 0.0
    amount_due = 0.0
    amount_due_seen = False
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]

    for line in reversed(lines):
        low = line.lower()
        if _QTY_UNIT_RE.search(low) and not _is_totals_candidate_line(low):
            continue
        value = _extract_last_money(line)
        if value <= 0:
            continue

        if any(token in low for token in ("do zaplaty", "pozostalo do zaplaty", "kwota do zaplaty")):
            due_value = (
                _extract_money_after_token(line, "do zaplaty")
                or _extract_money_after_token(line, "kwota do zaplaty")
                or _extract_money_after_token(line, "pozostalo do zaplaty")
            )
            if due_value is not None:
                amount_due_seen = True
                amount_due = max(0.0, float(due_value))
            elif amount_due <= 0:
                amount_due = value
            continue
        if total_vat <= 0 and _is_totals_candidate_line(low) and any(
            token in low for token in ("razem vat", "kwota vat", "suma vat", "podatek vat", "vat")
        ):
            # Ignore lines like "VAT 23%" without money amount.
            vat_value = (
                _extract_money_after_token(line, "kwota vat")
                or _extract_money_after_token(line, "vat")
            )
            if vat_value is not None:
                total_vat = max(0.0, float(vat_value))
            elif any(ch.isdigit() for ch in line):
                total_vat = value
            continue
        if total_gross <= 0 and _is_totals_candidate_line(low) and any(
            token in low for token in ("razem brutto", "wartosc brutto", "suma brutto", "brutto")
        ):
            gross_value = (
                _extract_money_after_token(line, "wartosc brutto")
                or _extract_money_after_token(line, "razem brutto")
                or _extract_money_after_token(line, "suma brutto")
                or _extract_money_after_token(line, "brutto")
            )
            total_gross = max(0.0, float(gross_value if gross_value is not None else value))
            continue
        if total_net <= 0 and _is_totals_candidate_line(low) and any(
            token in low for token in ("razem netto", "wartosc netto", "suma netto", "netto")
        ):
            net_value = (
                _extract_money_after_token(line, "wartosc netto")
                or _extract_money_after_token(line, "razem netto")
                or _extract_money_after_token(line, "suma netto")
                or _extract_money_after_token(line, "netto")
            )
            total_net = max(0.0, float(net_value if net_value is not None else value))
            continue

    # Użyj fallback_net/fallback_gross (sumy pozycji) gdy parsowanie tekstu nic nie znalazło.
    effective_fallback_net = fallback_net if fallback_net > 0 else fallback_total
    effective_fallback_gross = fallback_gross if fallback_gross > 0 else fallback_total
    if total_net <= 0 and effective_fallback_net > 0:
        total_net = effective_fallback_net
    if total_gross <= 0:
        total_gross = effective_fallback_gross if effective_fallback_gross > 0 else total_net
    if total_vat <= 0 and total_gross > 0 and total_net > 0 and total_gross >= total_net:
        total_vat = total_gross - total_net
    if amount_due <= 0 and not amount_due_seen:
        amount_due = total_gross if total_gross > 0 else total_net

    return max(0.0, total_net), max(0.0, total_vat), max(0.0, total_gross), max(0.0, amount_due)


def _is_summary_line(line: str) -> bool:
    low = str(line or "").strip().lower()
    if not low:
        return True
    blocked_tokens = (
        "razem",
        "suma",
        "podsumowanie",
        "do zaplaty",
        "kwota do zaplaty",
        "wartosc netto",
        "wartosc brutto",
        "naleznosc",
        "zaplacono",
        "pozostalo",
        "strona",
        "faktura",
        "data",
        "termin platnosci",
        "forma platnosci",
        "sprzedawca",
        "nabywca",
        "nip",
    )
    if any(token in low for token in blocked_tokens):
        return True
    alpha_count = sum(1 for ch in low if ch.isalpha())
    if alpha_count < 2:
        return True
    return False


def _spans_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return max(a[0], b[0]) < min(a[1], b[1])


def _extract_money_values(raw_line: str, excluded_spans: list[tuple[int, int]]) -> list[float]:
    values: list[float] = []
    spans = list(excluded_spans)
    spans.extend((m.start(), m.end()) for m in _DATE_RE.finditer(str(raw_line or "")))
    for match in _MONEY_RE.finditer(raw_line):
        span = (match.start(), match.end())
        if any(_spans_overlap(span, ex) for ex in spans):
            continue
        end = match.end()
        after = raw_line[end:end + 1] if end < len(raw_line) else ""
        if after == "%":
            continue
        value = _to_float(match.group(1))
        if value > 0:
            values.append(value)
    return values


def _pick_unit_total(values: list[float], qty: float) -> _PricePair:
    if not values:
        return _PricePair(0.0, 0.0)
    if len(values) == 1:
        total = values[0]
        if qty > 0:
            return _PricePair(total / qty, total)
        return _PricePair(total, total)

    if qty <= 0:
        return _PricePair(values[0], values[-1])

    best_idx_u = 0
    best_idx_t = 1
    best_score = 10**9

    for idx_u, unit_candidate in enumerate(values):
        if unit_candidate <= 0:
            continue
        for idx_t, total_candidate in enumerate(values):
            if idx_t == idx_u:
                continue
            if total_candidate <= 0:
                continue
            if total_candidate < unit_candidate:
                continue
            expected = unit_candidate * qty
            error = abs(expected - total_candidate)
            rel = error / max(total_candidate, 1.0)
            score = rel + (0.001 * abs(idx_t - idx_u))
            if score < best_score:
                best_score = score
                best_idx_u = idx_u
                best_idx_t = idx_t

    if best_score <= 0.15:
        return _PricePair(values[best_idx_u], values[best_idx_t])

    return _PricePair(values[0], values[1])


def _resolve_line_prices(
    values: list[float],
    qty: float,
    line_basis: str,
    default_basis: str,
) -> tuple[float, float, float, float, float, float, str]:
    pair = _pick_unit_total(values, qty)
    unit_price = max(0.0, pair.unit_price)
    total_price = max(0.0, pair.total_price)

    max_value = max(values) if values else total_price
    if max_value <= 0:
        max_value = total_price

    total_net = 0.0
    total_gross = 0.0

    if line_basis == "brutto":
        total_gross = total_price
        total_net = min(total_price, max_value)
    elif line_basis == "netto":
        total_net = total_price
        total_gross = max(total_price, max_value)
    elif max_value > total_price + 0.01:
        total_net = total_price
        total_gross = max_value
    else:
        if default_basis == "brutto":
            total_gross = total_price
            total_net = total_price
        elif default_basis == "netto":
            total_net = total_price
            total_gross = max(total_price, max_value)
        else:
            total_net = total_price
            total_gross = max(total_price, max_value)

    if total_net <= 0 and total_gross > 0:
        total_net = total_gross
    if total_gross <= 0 and total_net > 0:
        total_gross = total_net
    # Sanity-check: brutto nie może być >2× netto — OCR mógł wciągnąć cyfrę z kodu produktu.
    if total_net > 0 and total_gross > total_net * 2.0:
        total_gross = round(total_net * 1.23, 2)

    unit_net = total_net / qty if qty > 0 else unit_price
    unit_gross = total_gross / qty if qty > 0 else unit_price

    preferred_basis = default_basis if default_basis in {"netto", "brutto"} else "brutto"
    if line_basis in {"netto", "brutto"}:
        preferred_basis = line_basis

    if preferred_basis == "netto":
        preferred_unit = unit_net
        preferred_total = total_net
    else:
        preferred_unit = unit_gross
        preferred_total = total_gross

    return (
        max(0.0, preferred_unit),
        max(0.0, preferred_total),
        max(0.0, unit_net),
        max(0.0, unit_gross),
        max(0.0, total_net),
        max(0.0, total_gross),
        preferred_basis,
    )


def _parse_line_item(line: str, default_basis: str) -> InvoiceLineItem | None:
    raw_line = str(line or "").strip()
    low = raw_line.lower()
    if len(raw_line) < 6 or _is_summary_line(raw_line):
        return None

    qty = 0.0
    unit = ""
    excluded_spans: list[tuple[int, int]] = []

    qty_match = _QTY_UNIT_RE.search(raw_line)
    if qty_match:
        unit = normalize_unit(str(qty_match.group("unit") or ""))
        qty = _to_qty_float(str(qty_match.group("qty") or ""), unit)
        excluded_spans.append((qty_match.start("qty"), qty_match.end("qty")))

    values = _extract_money_values(raw_line, excluded_spans)
    if not values:
        return None

    # If the line looks like a date/metadata row and has no qty-unit, skip it.
    if qty_match is None and _DATE_RE.search(raw_line):
        return None
    if qty_match is None and len(values) < 2:
        return None

    if qty <= 0:
        qty = 1.0

    line_basis = "unknown"
    if "brutto" in low and "netto" not in low:
        line_basis = "brutto"
    elif "netto" in low and "brutto" not in low:
        line_basis = "netto"

    unit_price, total_price, unit_net, unit_gross, total_net, total_gross, preferred_basis = _resolve_line_prices(
        values,
        qty,
        line_basis,
        default_basis,
    )

    if unit_price <= 0 and total_price <= 0:
        return None

    name = ""
    if qty_match:
        name = _cleanup_name(raw_line[: qty_match.start()])
    if not name:
        first_money = _MONEY_RE.search(raw_line)
        prefix = raw_line[: first_money.start()] if first_money else raw_line
        name = _cleanup_name(prefix)
    if not name:
        return None
    if sum(1 for ch in name if ch.isalpha()) < 3:
        return None
    blocked_name_tokens = (
        "wartosc",
        "kwota",
        "nabywca",
        "sprzedawca",
        "faktura",
        "termin",
        "zaplacono",
        "razem",
        "netto",
        "brutto",
        "konto",
        "nip",
        "data ",
    )
    name_low = name.lower()
    if any(token in name_low for token in blocked_name_tokens):
        return None

    vat_rate = ""
    vat_match = _VAT_RE.search(low)
    if vat_match:
        vat_rate = str(vat_match.group("vat") or "").replace(",", ".")
    vat_amount = max(0.0, total_gross - total_net)

    return InvoiceLineItem(
        name=name,
        quantity=max(0.0, qty),
        unit=unit,
        unit_price=max(0.0, unit_price),
        total_price=max(0.0, total_price),
        material_type=_guess_material_type(name),
        thickness_mm=_extract_thickness(name),
        raw_line=raw_line,
        unit_price_net=max(0.0, unit_net),
        unit_price_gross=max(0.0, unit_gross),
        total_price_net=max(0.0, total_net),
        total_price_gross=max(0.0, total_gross),
        vat_amount=vat_amount,
        vat_rate=vat_rate,
        price_basis=preferred_basis,
        parse_source="generic",
    )


def _section_after(text: str, pattern: str, max_len: int = 1200) -> str:
    raw = str(text or "")
    match = re.search(pattern, raw, re.I)
    if not match:
        return ""
    start = max(0, match.start())
    end = min(len(raw), start + max(120, int(max_len or 1200)))
    return raw[start:end]


def _money_values_from_text(raw_text: str) -> list[float]:
    values: list[float] = []
    text = str(raw_text or "")
    for match in _MONEY_RE.finditer(text):
        span = (match.start(), match.end())
        if any(_spans_overlap(span, ds) for ds in [(m.start(), m.end()) for m in _DATE_RE.finditer(text)]):
            continue
        end = match.end()
        if end < len(text) and text[end:end + 1] == "%":
            continue
        value = _to_float(match.group(1))
        if value > 0:
            values.append(value)
    return values


def _unique_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for row in values:
        key = str(row or "").strip().casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(str(row or "").strip())
    return out


def _split_candidate_names(blob: str, template_key: str) -> list[str]:
    text = re.sub(r"\s+", " ", str(blob or "").strip())
    if not text:
        return []

    split_pattern = r"(?i)(?=\b(?:TANDEM(?:plus)?|Regulator|Samodomykacz|Tor(?:gorny)?|Zestaw|Reling|Herakles|FILTR|ZAWOREK|Usluga|KLEJ|PR[0O]FIL|Wkret|Olej|Filtr|Frez)\b)"
    if str(template_key or "").strip().lower() == "ita":
        split_pattern = r"(?i)(?=\b(?:Frez|UPS)\b)"
    parts = [part.strip(" ,.;:-") for part in re.split(split_pattern, text) if str(part or "").strip()]
    cleaned: list[str] = []
    for part in parts:
        low = part.lower()
        if any(token in low for token in ("sprzedawca", "nabywca", "faktura", "nip:", "strona", "data ")):
            continue
        part = re.sub(r"\b[A-Z0-9]{8,}\b", " ", part)
        part = re.sub(r"\b\d{2,}\s*%\b", " ", part)
        part = re.sub(r"\bU:\s*\d+\b", " ", part, flags=re.I)
        part = re.sub(r"\s+", " ", part).strip()
        if sum(1 for ch in part if ch.isalpha()) < 3:
            continue
        cleaned.append(_cleanup_name(part))
    return _unique_keep_order(cleaned)


def _build_recovered_item(
    *,
    name: str,
    quantity: float,
    unit: str,
    unit_price_net: float,
    total_price_net: float,
    total_price_gross: float,
    vat_rate: str,
    source: str,
    template_key: str,
) -> InvoiceLineItem | None:
    item_name = _cleanup_name(name)
    item_name = re.split(r"\s*\|\s*", item_name, maxsplit=1)[0].strip()
    item_name = re.sub(r"(?i)\bzaplacono\b.*$", "", item_name).strip(" ,.;:-")
    noise_tokens = (
        "sprzedawca",
        "nabywca",
        "forma platnosci",
        "nazwa towaru",
        "cn/pkwiu",
        "energetykow",
        "www.",
        "http",
    )
    low_name = item_name.lower()
    if any(token in low_name for token in noise_tokens):
        return None
    qty = max(0.0, float(quantity or 0.0))
    if qty <= 0:
        qty = 1.0
    unit_norm = normalize_unit(unit)
    net_total = max(0.0, float(total_price_net or 0.0))
    if net_total <= 0 and unit_price_net > 0:
        net_total = max(0.0, float(unit_price_net or 0.0) * qty)
    gross_total = max(0.0, float(total_price_gross or 0.0))
    if gross_total <= 0:
        gross_total = net_total
    if net_total > 0 and gross_total > 0 and gross_total < net_total:
        gross_total = net_total
    # Sanity-check: brutto nie powinno być >2× netto (max sensowny VAT to ~25%).
    # Jeśli jest większe, OCR wziął cyfrę z kodu produktu jako cenę — odrzucamy.
    if net_total > 0 and gross_total > 0 and gross_total / net_total > 2.0:
        gross_total = round(net_total * 1.23, 2)  # zakładamy 23% VAT jako fallback
    unit_net = max(0.0, float(unit_price_net or 0.0))
    if unit_net <= 0 and qty > 0:
        unit_net = net_total / qty if net_total > 0 else 0.0
    unit_gross = gross_total / qty if qty > 0 else gross_total
    if not item_name or unit_net <= 0:
        return None

    material_type = _material_type_for_supplier(
        item_name,
        template_key,
        _guess_material_type(item_name),
    )
    return InvoiceLineItem(
        name=item_name,
        quantity=qty,
        unit=unit_norm,
        unit_price=unit_net,
        total_price=net_total,
        material_type=material_type,
        thickness_mm=_extract_thickness(item_name),
        raw_line=str(source or "").strip(),
        unit_price_net=unit_net,
        unit_price_gross=max(0.0, unit_gross),
        total_price_net=net_total,
        total_price_gross=gross_total,
        vat_amount=max(0.0, gross_total - net_total),
        vat_rate=str(vat_rate or "").strip(),
        price_basis="netto",
        parse_source=f"fallback:{template_key}:columns",
    )


def _recover_template_items_from_text(
    raw_text: str,
    *,
    template_key: str,
) -> list[InvoiceLineItem]:
    text = str(raw_text or "")
    key = str(template_key or "").strip().lower()
    if not key or not text:
        return []

    vat_match = _VAT_RE.search(text)
    vat_rate = str(vat_match.group("vat") or "").replace(",", ".") if vat_match else ""

    recovered: list[InvoiceLineItem] = []

    # Multi-row list recovery for suppliers where OCR often places names/qty/prices in separate rows.
    if key in {"pakdrew", "artex", "ita"}:
        names_blob = _section_after(text, r"\bnazwa\b", 2200)
        for marker in ("#Pakdrew", "Sprzedawca", "Nabywca", "Termin platnosci"):
            if marker in names_blob:
                names_blob = names_blob.split(marker, 1)[0]
        names: list[str] = []
        if key == "pakdrew":
            raw_names = _split_candidate_names(text, key)
            expanded: list[str] = []
            for value in raw_names:
                if "tor" in value.lower() and "zestaw" in value.lower():
                    expanded.extend([x.strip() for x in re.split(r"(?i)(?=\b(?:Tor(?:gorny)?|Zestaw)\b)", value) if x.strip()])
                else:
                    expanded.append(value)
            names = _unique_keep_order([
                _cleanup_name(re.sub(r"\|\s*$", "", row))
                for row in expanded
                if row and "|" not in row[-3:]
            ])
        if key == "artex":
            artex_names = re.findall(
                r"(FILTR[^\n]{2,120}?)(?=\s+ZAWOREK|\s+Ustuga|\s+Nabywca|$)|"
                r"(ZAWOREK[^\n]{2,120}?)(?=\s+Ustuga|\s+Nabywca|$)|"
                r"(Ustuga[^\n]{2,120}?)(?=\s+Nabywca|$)",
                text,
                flags=re.I,
            )
            flat_names = [part for row in artex_names for part in row if str(part or "").strip()]
            names = _unique_keep_order([_cleanup_name(x) for x in flat_names if _cleanup_name(x)])
        elif key != "pakdrew":
            names = _split_candidate_names(names_blob, key)
        if key == "ita" and not names:
            code_matches = re.findall(r"\b(?:DTA|DIA|UPS)[A-Z0-9.\-_/]{2,}\b", text, flags=re.I)
            names = _unique_keep_order([str(code or "").strip().upper() for code in code_matches])
        if not names:
            names = _split_candidate_names(names_blob, key)

        qty_unit_matches = list(_QTY_UNIT_RE.finditer(text))
        qty_rows: list[tuple[float, str]] = []
        for m in qty_unit_matches:
            unit = normalize_unit(str(m.group("unit") or ""))
            qty = _to_qty_float(str(m.group("qty") or ""), unit)
            if qty <= 0:
                continue
            if key in {"pakdrew", "ita"} and unit != "szt":
                continue
            if key == "artex" and unit not in {"szt", "kg", "m", "mb"}:
                continue
            # Skip obvious non-item noise.
            if qty > 5000:
                continue
            qty_rows.append((qty, unit))

        price_blob = _section_after(text, r"cena\s*netto", 1200) or _section_after(text, r"cena", 1200)
        price_values = [v for v in _money_values_from_text(price_blob) if 0.0 < v <= 5000.0]
        if key in {"pakdrew", "artex", "ita"}:
            # In table rows unit price is usually below 500 PLN; keep totals out.
            price_values = [v for v in price_values if v <= 500.0] or price_values

        if names and qty_rows and price_values:
            rows_count = min(len(names), len(qty_rows), len(price_values))
            for idx in range(rows_count):
                qty, unit = qty_rows[idx]
                unit_net = float(price_values[idx])
                item = _build_recovered_item(
                    name=names[idx],
                    quantity=qty,
                    unit=unit,
                    unit_price_net=unit_net,
                    total_price_net=qty * unit_net,
                    total_price_gross=0.0,
                    vat_rate=vat_rate,
                    source=f"{key}:table",
                    template_key=key,
                )
                if item is not None:
                    recovered.append(item)

    # Single-line fallback when the invoice has one material row.
    if not recovered:
        product_patterns = {
            "ica": r"(KLEJ[^\n]{3,180})",
            "tabal": r"(PR[0O]FIL[^\n]{3,180})",
            "wurth": r"(Wkret[^\n]{3,220})",
            "gorpak": r"(FOLIA[^\n]{3,220})",
            "mielec": r"(Olej[^\n]{2,120}|Filtr[^\n]{2,120})",
            "artex": r"(FILTR[^\n]{2,160}|ZAWOREK[^\n]{2,160}|Usluga[^\n]{2,120})",
        }
        product_name = ""
        product_match = re.search(product_patterns.get(key, r""), text, flags=re.I) if key in product_patterns else None
        if product_match:
            product_name = _cleanup_name(str(product_match.group(1) or ""))

        qty = 0.0
        unit = ""
        qty_match = _QTY_UNIT_RE.search(text)
        if qty_match:
            unit = normalize_unit(str(qty_match.group("unit") or ""))
            qty = _to_qty_float(str(qty_match.group("qty") or ""), unit)
        if qty <= 0:
            plain_qty_match = re.search(r"(?i)\b(?:ilosc|ilo[s$]c|hlose)\b[^0-9]{0,10}(\d+(?:[.,]\d+)?)", text)
            if plain_qty_match:
                qty = _to_float(str(plain_qty_match.group(1) or ""))
                if key in {"gorpak", "mielec", "wurth"}:
                    unit = "szt"

        price_net = 0.0
        price_candidates: list[float] = []
        for label in (r"cena\s*netto", r"cena\s*w\s*pln", r"cena"):
            blob = _section_after(text, label, 260)
            vals = [v for v in _money_values_from_text(blob) if 0.0 < v <= 5000.0]
            if vals:
                price_candidates = vals
                price_net = vals[0]
                break

        total_net = 0.0
        blob_net = _section_after(text, r"wartosc\s*netto", 320)
        vals_net = [v for v in _money_values_from_text(blob_net) if 0.0 < v <= 200000.0]
        if vals_net:
            total_net = vals_net[0]
        if total_net <= 0 and qty > 0 and price_net > 0:
            total_net = qty * price_net
        if total_net > 0 and qty > 0 and price_candidates:
            best = min(price_candidates, key=lambda v: abs((v * qty) - total_net))
            if best > 0:
                price_net = best

        total_gross = 0.0
        for gross_label in (r"wartosc\s*brutto", r"razem\s*do\s*zaplaty", r"do\s*zaplaty"):
            gross_blob = _section_after(text, gross_label, 320)
            vals_gross = [v for v in _money_values_from_text(gross_blob) if 0.0 < v <= 200000.0]
            if vals_gross:
                total_gross = vals_gross[0]
                break

        if key == "wurth":
            qty_w_match = re.search(r"(?i)j\.?miary[^0-9]{0,10}(\d+(?:[.,]\d+)?)\s*szt", text)
            if qty_w_match:
                qty = _to_qty_float(str(qty_w_match.group(1) or ""), "szt")
                unit = "szt"
            price_w_match = re.search(r"(?i)cena\w*pln[^0-9]{0,20}(\d+[.,]\d+)", text)
            if price_w_match:
                price_net = _to_float(str(price_w_match.group(1) or ""))
            price_before_vat = re.search(r"(?i)(\d+[.,]\d+)\s*vat\s*[:%]", text)
            if price_before_vat:
                price_net = _to_float(str(price_before_vat.group(1) or ""))
            net_w_match = re.search(r"(?i)netto\w*pln[^0-9]{0,20}(\d+[.,]\d+)", text)
            if net_w_match:
                total_net = _to_float(str(net_w_match.group(1) or ""))
            if total_net > 0 and price_net > 0 and qty > 0:
                rel_err = abs((qty * price_net) - total_net) / max(total_net, 1.0)
                if rel_err > 0.35:
                    inferred_qty = total_net / price_net
                    if 1.0 <= inferred_qty <= 1000.0:
                        qty = inferred_qty

        item = _build_recovered_item(
            name=product_name,
            quantity=qty,
            unit=unit,
            unit_price_net=price_net,
            total_price_net=total_net,
            total_price_gross=total_gross,
            vat_rate=vat_rate,
            source=f"{key}:single",
            template_key=key,
        )
        if item is not None:
            recovered.append(item)

    out: list[InvoiceLineItem] = []
    seen: set[tuple[str, str, str]] = set()
    for item in recovered:
        item_key = (
            str(item.name or "").strip().lower(),
            f"{float(item.quantity or 0.0):.3f}",
            f"{float(item.total_price or 0.0):.2f}",
        )
        if item_key in seen:
            continue
        seen.add(item_key)
        out.append(item)
    return out


def parse_invoice_text(text: str, source_path: Path | None = None) -> InvoiceParseResult:
    source = source_path or Path("invoice.pdf")
    raw_text = str(text or "")
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    parsed_items: list[InvoiceLineItem] = []
    seen: set[tuple[str, str, str]] = set()
    supplier_template = _detect_supplier_template(raw_text)

    default_basis = _detect_price_basis(raw_text)

    for line in lines:
        prepared_line = _prepare_line_for_supplier(line, supplier_template)
        if supplier_template:
            item = _parse_line_item_template(prepared_line, default_basis, supplier_template)
            if item is None and _QTY_UNIT_RE.search(prepared_line):
                generic_item = _parse_line_item(prepared_line, default_basis)
                if generic_item is not None:
                    sanitized_name = _sanitize_template_item_name(generic_item.name, supplier_template)
                    if _is_template_name_allowed(sanitized_name):
                        item = replace(
                            generic_item,
                            name=sanitized_name,
                            material_type=_material_type_for_supplier(
                                sanitized_name,
                                supplier_template,
                                generic_item.material_type,
                            ),
                            raw_line=prepared_line,
                            parse_source=f"fallback:{supplier_template}",
                        )
                    else:
                        item = None
        else:
            item = _parse_line_item(prepared_line, default_basis)
        if item is None:
            continue
        key = (
            item.name.strip().lower(),
            f"{item.quantity:.3f}",
            f"{item.total_price:.2f}",
        )
        if key in seen:
            continue
        seen.add(key)
        parsed_items.append(item)

    # OCR scans often separate table columns into different lines.
    # For known suppliers, run an extra recovery pass that zips name/qty/price columns.
    if supplier_template and len(parsed_items) <= 1:
        recovered_items = _recover_template_items_from_text(
            raw_text,
            template_key=supplier_template,
        )
        for item in recovered_items:
            key = (
                item.name.strip().lower(),
                f"{item.quantity:.3f}",
                f"{item.total_price:.2f}",
            )
            if key in seen:
                continue
            seen.add(key)
            parsed_items.append(item)

    # Dla faktur ADLER (OCR) — specjalny parser pozycji gdy generic nie znalazł nic.
    effective_template = supplier_template or _detect_supplier_template(raw_text)
    if effective_template == "adler" and not parsed_items:
        adler_items = _parse_adler_items(raw_text)
        for item in adler_items:
            key = (item.name.strip().lower(), f"{item.quantity:.3f}", f"{item.total_price:.2f}")
            if key not in seen:
                seen.add(key)
                parsed_items.append(item)

    items_total_net = sum(max(0.0, row.total_price_net) for row in parsed_items)
    items_total_gross = sum(max(0.0, row.total_price_gross) for row in parsed_items)
    total_net, total_vat, total_gross, amount_due = _extract_totals(
        raw_text,
        fallback_net=items_total_net,
        fallback_gross=items_total_gross,
        fallback_total=items_total_gross if items_total_gross > 0 else items_total_net,
    )
    supplier = _extract_supplier(raw_text)
    if not supplier_template:
        supplier_template = _template_from_supplier_name(supplier)
    buyer_nip = _extract_buyer_nip(raw_text)
    is_msi_project_invoice = buyer_nip == MSI_PROJECT_NIP

    return InvoiceParseResult(
        source_path=source,
        invoice_number=_extract_invoice_number(raw_text),
        invoice_date=_extract_invoice_date(raw_text),
        supplier=supplier,
        text_length=len(raw_text),
        items=tuple(parsed_items),
        price_basis=default_basis,
        total_net=total_net,
        total_vat=total_vat,
        total_gross=total_gross,
        amount_due=amount_due,
        currency=_extract_currency(raw_text),
        buyer_nip=buyer_nip,
        is_msi_project_invoice=is_msi_project_invoice,
        extraction_method="text",
        ocr_confidence=0.0,
        supplier_template=supplier_template,
    )


_ADLER_LINE_RE = re.compile(
    # kod_art  qty  [size unit]  nazwa  cena_jedn  [rabat%]  total_netto  vat%
    r"^\d{8,14}\s+"                       # kod artykułu (8-14 cyfr)
    r"(\d+[.,]\d+)\s+"                    # qty
    r"(?:\d+\s+\w+\s+)?"                  # opcjonalne: "24 kg", "20 kg" (rozmiar)
    r"\|?\s*"                             # opcjonalny separator |
    r"(.+?)"                              # nazwa produktu (non-greedy)
    r"\s+(\d+[.,]\d+)"                   # cena jednostkowa netto
    r"(?:\s+\d{1,2}%)?"                  # opcjonalny rabat procentowy
    r"\s+(\d+[.,]\d+)"                   # total netto (po rabacie)
    r"\s+(\d{1,2})%"                     # stawka VAT
    r"\s*$",
    re.MULTILINE,
)


def _parse_adler_items(text: str) -> list[InvoiceLineItem]:
    """Parsuje pozycje faktur ADLER z OCR-tekstu.

    Format linii ADLER:
    ``[kod_art] [qty] [rozmiar unit] [nazwa] [cena_jedn] [rabat%]? [total_netto] [vat%]``
    Przykład:
    ``241605000024 1,00 24 kg Aduro Ecofill WeiR 840,79 15% 714,69 23%``
    """
    items: list[InvoiceLineItem] = []
    for m in _ADLER_LINE_RE.finditer(str(text or "")):
        try:
            qty = _to_float(m.group(1))
            raw_name = m.group(2).strip().strip("|").strip()
            # Usuń artefakty OCR: krótkie tokeny (1-2 znaki) z początku nazwy
            raw_name = re.sub(r"^\s*[A-Z]{2,6}\s+", "", raw_name).strip()
            # Usuń pozostałości kodu artykułu (same cyfry na początku)
            raw_name = re.sub(r"^\d+\s+", "", raw_name).strip()
            if not raw_name or sum(1 for c in raw_name if c.isalpha()) < 3:
                continue
            total_net = _to_float(m.group(4))
            vat_rate_str = m.group(5)
            if qty <= 0 or total_net <= 0:
                continue
            vat_mult = 1.0 + _to_float(vat_rate_str) / 100.0
            total_gross = round(total_net * vat_mult, 2)
            unit_net = total_net / qty if qty > 0 else total_net
            name = _cleanup_name(raw_name)
            items.append(InvoiceLineItem(
                name=name,
                quantity=qty,
                unit="szt",
                unit_price=unit_net,
                total_price=total_net,
                material_type=_guess_material_type(name),
                thickness_mm="",
                raw_line=m.group(0).strip(),
                unit_price_net=unit_net,
                unit_price_gross=round(unit_net * vat_mult, 4),
                total_price_net=total_net,
                total_price_gross=total_gross,
                vat_amount=round(total_gross - total_net, 2),
                vat_rate=vat_rate_str,
                price_basis="netto",
                parse_source="adler:ocr",
            ))
        except Exception:
            continue
    return items


def _parse_pdfplumber_table_items(payload: bytes) -> list[InvoiceLineItem]:
    """Try to extract line items from pdfplumber table cells.

    Returns non-empty list only when a proper invoice table is found
    (header row with Lp/Nazwa/IloĹ›Ä‡ columns + data rows).
    """
    try:
        import pdfplumber  # type: ignore
    except Exception:
        return []
    items: list[InvoiceLineItem] = []
    try:
        with pdfplumber.open(BytesIO(payload)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    if not table or len(table) < 2:
                        continue
                    # Find header row: must contain "nazwa" and at least one price column
                    # Search up to row 12 â€” some invoices have large seller/buyer blocks before the table
                    header_idx = None
                    for row_idx, row in enumerate(table[:12]):
                        cells = [str(c or "").strip().lower() for c in (row or [])]
                        row_text = " ".join(cells)
                        if "nazwa" in row_text and any(
                            kw in row_text for kw in ("netto", "brutto", "cena", "warto")
                        ):
                            header_idx = row_idx
                            break
                    if header_idx is None:
                        continue
                    header = [str(c or "").strip().lower() for c in (table[header_idx] or [])]
                    # Map column indices
                    col_name = col_qty = col_unit = col_price = col_total = col_vat_rate = col_vat_amt = col_gross = -1
                    for ci, h in enumerate(header):
                        h2 = re.sub(r"\s+", "", h)
                        if "nazwa" in h2 and col_name == -1:
                            col_name = ci
                        elif any(k in h2 for k in ("ilo", "ilosc", "ilosc")) and col_qty == -1:
                            col_qty = ci
                        elif h2 in ("jm", "j.m.", "jed", "jedn", "jednostka") and col_unit == -1:
                            col_unit = ci
                        elif "cenanetto" in h2 or (h2 == "cena" and col_price == -1):
                            col_price = ci
                        elif "wartoscnetto" in h2 or "wartosc\nnetto" in h2.replace(" ", ""):
                            col_total = ci
                        elif "stawkavat" in h2 or "stawka" in h2:
                            col_vat_rate = ci
                        elif "kwotavat" in h2 or ("vat" in h2 and "stawka" not in h2 and "warto" not in h2):
                            col_vat_amt = ci
                        elif "wartoscbrutto" in h2 or "brutto" in h2:
                            col_gross = ci
                    if col_name == -1 or col_qty == -1:
                        continue
                    default_basis = "netto" if col_total != -1 else "brutto"
                    for row in table[header_idx + 1 :]:
                        if not row:
                            continue
                        cells = [str(c or "").strip() for c in row]
                        name_raw = cells[col_name] if col_name < len(cells) else ""
                        name = re.sub(r"\s+", " ", name_raw).strip()
                        if not name or len(name) < 2:
                            continue
                        # Skip summary/total rows
                        if re.match(r"^(?:razem|suma|w tym|ogĂłlem|Ĺ‚Ä…cznie)", name.lower()):
                            continue
                        # First cell is often the Lp number â€” skip if name is just digits
                        if re.match(r"^\d+$", name):
                            continue
                        qty_raw = cells[col_qty] if col_qty < len(cells) else "0"
                        unit_raw = cells[col_unit] if col_unit != -1 and col_unit < len(cells) else ""
                        price_raw = cells[col_price] if col_price != -1 and col_price < len(cells) else "0"
                        total_raw = cells[col_total] if col_total != -1 and col_total < len(cells) else "0"
                        vat_rate_raw = cells[col_vat_rate] if col_vat_rate != -1 and col_vat_rate < len(cells) else ""
                        vat_amt_raw = cells[col_vat_amt] if col_vat_amt != -1 and col_vat_amt < len(cells) else "0"
                        gross_raw = cells[col_gross] if col_gross != -1 and col_gross < len(cells) else "0"
                        unit = normalize_unit(unit_raw) or "szt"
                        qty = _to_qty_float(qty_raw, unit)
                        if qty <= 0:
                            continue
                        unit_price_net = _to_float(price_raw)
                        total_net = _to_float(total_raw) if col_total != -1 else round(unit_price_net * qty, 2)
                        total_gross = _to_float(gross_raw) if col_gross != -1 else 0.0
                        vat_amt = _to_float(vat_amt_raw)
                        vat_rate_str = re.sub(r"[^0-9.,]", "", vat_rate_raw)
                        material_type = _guess_material_type(name)
                        thickness = _extract_thickness(name)
                        items.append(
                            InvoiceLineItem(
                                name=name,
                                quantity=qty,
                                unit=unit,
                                unit_price=unit_price_net,
                                total_price=total_net if total_net > 0 else total_gross,
                                material_type=material_type,
                                thickness_mm=thickness,
                                raw_line="|".join(cells),
                                unit_price_net=unit_price_net,
                                unit_price_gross=round(unit_price_net * (1 + _to_float(vat_rate_str) / 100), 4) if vat_rate_str else 0.0,
                                total_price_net=total_net,
                                total_price_gross=total_gross if total_gross > 0 else round(total_net + vat_amt, 2),
                                vat_amount=vat_amt,
                                vat_rate=vat_rate_str,
                                price_basis=default_basis,
                                parse_source="pdfplumber_table",
                            )
                        )
    except Exception:
        pass
    return items


def parse_invoice_pdf(path: Path) -> InvoiceParseResult:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Nie znaleziono pliku PDF: {file_path}")
    try:
        payload = file_path.read_bytes()
    except Exception as exc:
        raise RuntimeError(f"Nie mozna odczytac pliku PDF: {exc}") from exc
    return parse_invoice_pdf_bytes(payload, source_name=file_path.name, source_path=file_path)


def parse_invoice_pdf_bytes(
    payload: bytes,
    source_name: str = "invoice.pdf",
    source_path: Path | None = None,
) -> InvoiceParseResult:
    if not bytes(payload or b"").lstrip().startswith(b"%PDF"):
        raise RuntimeError("Nieprawidlowy plik PDF (brak naglowka %PDF).")

    chunks: list[str] = []
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        reader = None
    else:
        try:
            reader = PdfReader(BytesIO(payload))
        except Exception:
            reader = None

    if reader is not None:
        for page in reader.pages:
            try:
                extracted = str(page.extract_text() or "")
            except Exception:
                extracted = ""
            if extracted.strip():
                chunks.append(extracted)

    text = "\n".join(chunks).strip()
    extraction_method = "text" if text else "none"
    ocr_confidence = 0.0

    # Fallback OCR for scanned PDFs with no embedded text.
    if len(text) < 60:
        ocr_text, ocr_confidence = _extract_pdf_text_with_ocr(payload)
        if ocr_text:
            if text:
                text = f"{text}\n{ocr_text}".strip()
                extraction_method = "mixed"
            else:
                text = ocr_text
                extraction_method = "ocr"

    resolved_source = source_path if source_path is not None else Path(source_name or "invoice.pdf")
    parsed = parse_invoice_text(text, source_path=resolved_source)

    # For text-based PDFs: try pdfplumber table extraction; use it when it finds more items.
    if extraction_method == "text" and len(text) > 60:
        plumber_items = _parse_pdfplumber_table_items(payload)
        if len(plumber_items) > len(parsed.items):
            from dataclasses import replace as _replace
            p_net = sum(i.total_price_net for i in plumber_items)
            p_gross = sum(i.total_price_gross for i in plumber_items)
            p_vat = sum(i.vat_amount for i in plumber_items)
            parsed = _replace(
                parsed,
                items=tuple(plumber_items),
                total_net=p_net if p_net > 0 else parsed.total_net,
                total_gross=p_gross if p_gross > 0 else parsed.total_gross,
                total_vat=p_vat if p_vat > 0 else parsed.total_vat,
                amount_due=p_gross if p_gross > 0 else (parsed.amount_due if parsed.amount_due > 0 else p_net),
            )

    def _should_try_ai_fallback(base: InvoiceParseResult, method: str, ocr_conf: float) -> bool:
        extraction = str(method or "").strip().lower()
        if extraction not in {"ocr", "mixed"}:
            return False
        items_count = len(tuple(base.items or ()))
        missing_core = not str(base.invoice_number or "").strip() or not str(base.supplier or "").strip()
        weak_totals = float(base.total_gross or 0.0) <= 0 and float(base.amount_due or 0.0) <= 0
        low_confidence = float(ocr_conf or 0.0) < 0.95
        poor_result = items_count <= 1 or missing_core or weak_totals
        return poor_result or (low_confidence and items_count <= 3)

    ai_error = ""
    if _should_try_ai_fallback(parsed, extraction_method, ocr_confidence):
        try:
            from src.services.invoice_ai_fallback_service import try_parse_invoice_text_with_ai

            ai_parsed, ai_error = try_parse_invoice_text_with_ai(
                text=text,
                source_path=resolved_source,
                base_result=InvoiceParseResult(
                    source_path=parsed.source_path,
                    invoice_number=parsed.invoice_number,
                    invoice_date=parsed.invoice_date,
                    supplier=parsed.supplier,
                    text_length=parsed.text_length,
                    items=parsed.items,
                    price_basis=parsed.price_basis,
                    total_net=parsed.total_net,
                    total_vat=parsed.total_vat,
                    total_gross=parsed.total_gross,
                    amount_due=parsed.amount_due,
                    currency=parsed.currency,
                    buyer_nip=parsed.buyer_nip,
                    is_msi_project_invoice=parsed.is_msi_project_invoice,
                    extraction_method=extraction_method,
                    ocr_confidence=max(0.0, float(ocr_confidence)),
                    supplier_template=str(getattr(parsed, "supplier_template", "") or "").strip(),
                    ai_fallback_used=False,
                    ai_confidence=0.0,
                    ai_model="",
                    ai_error="",
                ),
            )
            if ai_parsed is not None:
                parsed = ai_parsed
                extraction_method = str(ai_parsed.extraction_method or extraction_method or "ai")
                ocr_confidence = max(float(ocr_confidence or 0.0), float(ai_parsed.ocr_confidence or 0.0))
            elif any(token in str(ai_error or "").lower() for token in ("wylaczony", "openai_api_key")):
                ai_error = ""
        except Exception as exc:
            ai_error = f"{exc}"

    return InvoiceParseResult(
        source_path=parsed.source_path,
        invoice_number=parsed.invoice_number,
        invoice_date=parsed.invoice_date,
        supplier=parsed.supplier,
        text_length=parsed.text_length,
        items=parsed.items,
        price_basis=parsed.price_basis,
        total_net=parsed.total_net,
        total_vat=parsed.total_vat,
        total_gross=parsed.total_gross,
        amount_due=parsed.amount_due,
        currency=parsed.currency,
        buyer_nip=parsed.buyer_nip,
        is_msi_project_invoice=parsed.is_msi_project_invoice,
        extraction_method=extraction_method,
        ocr_confidence=max(0.0, float(ocr_confidence)),
        supplier_template=str(getattr(parsed, "supplier_template", "") or "").strip(),
        ai_fallback_used=bool(getattr(parsed, "ai_fallback_used", False)),
        ai_confidence=max(0.0, float(getattr(parsed, "ai_confidence", 0.0) or 0.0)),
        ai_model=str(getattr(parsed, "ai_model", "") or "").strip(),
        ai_error=str(getattr(parsed, "ai_error", "") or "").strip() or str(ai_error or "").strip(),
    )


