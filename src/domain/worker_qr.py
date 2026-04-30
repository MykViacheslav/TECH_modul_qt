from __future__ import annotations

from dataclasses import dataclass


QR_PREFIX = "TECH_MODUL_WORKER"


def normalize_worker_id(worker_id: str) -> str:
    return str(worker_id or "").strip().upper()


def normalize_worker_name(worker_name: str) -> str:
    return str(worker_name or "").strip()


def build_worker_qr_payload(worker_id: str, worker_name: str = "", bot_username: str = "") -> str:
    worker_id_norm = normalize_worker_id(worker_id)
    worker_name_norm = normalize_worker_name(worker_name)
    
    # If bot_username is provided, create a Telegram Deep Link
    if bot_username:
        # Format: https://t.me/bot?start=workerID
        clean_bot = str(bot_username).strip().lstrip("@")
        return f"https://t.me/{clean_bot}?start=W{worker_id_norm}"

    if worker_id_norm:
        if worker_name_norm:
            return f"{QR_PREFIX}|ID={worker_id_norm}|NAME={worker_name_norm}"
        return f"{QR_PREFIX}|ID={worker_id_norm}"
    if worker_name_norm:
        return f"{QR_PREFIX}|NAME={worker_name_norm}"
    return QR_PREFIX


def extract_worker_identifier(payload: str) -> tuple[str, str]:
    """
    Return (worker_id, worker_name) extracted from a QR payload.
    Accepts both the structured TECH_MODUL payload and plain fallback values.
    """
    text = str(payload or "").strip()
    if not text:
        return ("", "")

    if text.upper().startswith(QR_PREFIX):
        parts = [part.strip() for part in text.split("|") if part.strip()]
        worker_id = ""
        worker_name = ""
        for part in parts[1:]:
            upper = part.upper()
            if upper.startswith("ID="):
                worker_id = normalize_worker_id(part.split("=", 1)[1])
            elif upper.startswith("NAME="):
                worker_name = normalize_worker_name(part.split("=", 1)[1])
        return (worker_id, worker_name)

    if "|" in text:
        left, right = text.split("|", 1)
        return (normalize_worker_id(left), normalize_worker_name(right))

    return (normalize_worker_id(text), "")
