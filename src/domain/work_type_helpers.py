from __future__ import annotations

import unicodedata

from src.domain.worker_models import WorkerDef


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_work_type_label(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    key = " ".join(_strip_accents(raw).lower().split())
    mapping = {
        "produkcja": "Produkcja",
        "montaz": "Montaż",
        "praca na miejscu": "Praca na miejscu",
        "lakiernia": "Lakiernia",
        "delegacja / wyjazd": "Delegacja / wyjazd",
        "projekt / wycena": "Projekt / wycena",
        "zakup materialow": "Zakup materiałów",
        "bhp / szkolenie": "BHP / szkolenie",
        "inne": "Inne",
    }
    return mapping.get(key, raw)


def infer_work_type_from_role(role: str) -> str:
    raw = _strip_accents(role).lower()
    raw = " ".join(raw.split())
    if not raw:
        return "Produkcja"
    if "lakier" in raw:
        return "Lakiernia"
    if "montaz" in raw:
        return "Montaż"
    if "deleg" in raw:
        return "Delegacja / wyjazd"
    if "bhp" in raw:
        return "BHP / szkolenie"
    if "zakup" in raw or "magaz" in raw:
        return "Zakup materiałów"
    if "sprzed" in raw or "prezes" in raw or "biuro" in raw:
        return "Praca na miejscu"
    if "konstruk" in raw or "projekt" in raw:
        return "Projekt / wycena"
    if "kierownik" in raw:
        return "Praca na miejscu"
    if "stolar" in raw or "produkc" in raw:
        return "Produkcja"
    return "Produkcja"


def infer_work_type_for_worker(worker: WorkerDef | None) -> str:
    if worker is None:
        return "Produkcja"
    role = str(getattr(worker, "role", "") or "").strip()
    return infer_work_type_from_role(role)
