from __future__ import annotations

from dataclasses import dataclass


PACKAGE_QR_PREFIX = "TECH_PACK"


@dataclass(frozen=True)
class PackageQrData:
    order_code: str = ""
    order_id: str = ""
    client: str = ""
    room: str = ""
    item: str = ""
    package_raw: str = ""
    package_index: int = 0
    package_total: int = 0
    raw_text: str = ""

    def to_dict(self) -> dict[str, str | int]:
        return {
            "order_code": self.order_code,
            "order_id": self.order_id,
            "client": self.client,
            "room": self.room,
            "item": self.item,
            "package_raw": self.package_raw,
            "package_index": self.package_index,
            "package_total": self.package_total,
            "raw_text": self.raw_text,
        }


def parse_package_qr_payload(text: str) -> PackageQrData | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    if not raw.upper().startswith(PACKAGE_QR_PREFIX):
        return None

    parts = [part.strip() for part in raw.split("|") if part.strip()]
    if not parts:
        return None

    data: dict[str, str] = {}
    for chunk in parts[1:]:
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        key_norm = str(key or "").strip().upper()
        data[key_norm] = str(value or "").strip()

    package_raw = data.get("PACK", "")
    package_index, package_total = _parse_pack_chunk(package_raw)

    return PackageQrData(
        order_code=data.get("ORDER_CODE", ""),
        order_id=data.get("ORDER_ID", ""),
        client=data.get("CLIENT", ""),
        room=data.get("ROOM", ""),
        item=data.get("ITEM", ""),
        package_raw=package_raw,
        package_index=package_index,
        package_total=package_total,
        raw_text=raw,
    )


def _parse_pack_chunk(value: str) -> tuple[int, int]:
    text = str(value or "").strip()
    if not text:
        return 0, 0
    if "/" not in text:
        return _safe_int(text), 0
    left, right = text.split("/", 1)
    return _safe_int(left), _safe_int(right)


def _safe_int(value: str) -> int:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not digits:
        return 0
    try:
        return int(digits)
    except Exception:
        return 0
