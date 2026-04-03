from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.storage.invoice_store_json import InvoiceStoreJson
from src.storage.material_store_json import MaterialStoreJson
from src.storage.supplier_price_store_json import SupplierPriceStoreJson


def _safe_float(value: Any) -> float:
    raw = str(value or "").strip().replace(" ", "").replace(",", ".")
    if not raw:
        return 0.0
    try:
        return float(raw)
    except Exception:
        return 0.0


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _same_unit(left: str, right: str) -> bool:
    a = str(left or "").strip().lower()
    b = str(right or "").strip().lower()
    if not a or not b:
        return True
    return a == b


def _basis(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"netto", "brutto"}:
        return text
    return "unknown"


def _looks_like_same_material(candidate_name: str, wanted_names: set[str]) -> bool:
    candidate = _norm(candidate_name)
    if not candidate or not wanted_names:
        return False
    if candidate in wanted_names:
        return True
    for wanted in wanted_names:
        if len(wanted) < 5 or len(candidate) < 5:
            continue
        if wanted in candidate or candidate in wanted:
            return True
    return False


@dataclass(frozen=True)
class SupplierOffer:
    supplier: str
    unit_price: float
    price_basis: str
    source: str
    material_id: str = ""
    material_name: str = ""
    unit: str = ""
    currency: str = "PLN"
    updated_at: str = ""
    note: str = ""

    def estimated_total(self, quantity: float) -> float:
        return max(0.0, float(quantity or 0.0)) * max(0.0, float(self.unit_price or 0.0))


@dataclass(frozen=True)
class PriceRecommendation:
    best_offer: SupplierOffer
    ranked_offers: tuple[SupplierOffer, ...]
    compare_basis: str
    warning: str
    skipped_offers: int
    potential_saving: float
    current_total: float
    best_total: float


class ShoppingPriceCompareService:
    """Compare supplier offers and recommend where to buy cheaper."""

    def __init__(
        self,
        *,
        supplier_store: SupplierPriceStoreJson | None = None,
        invoice_store: InvoiceStoreJson | None = None,
        material_store: MaterialStoreJson | None = None,
    ) -> None:
        self._supplier_store = supplier_store if supplier_store is not None else SupplierPriceStoreJson()
        self._invoice_store = invoice_store if invoice_store is not None else InvoiceStoreJson()
        self._material_store = material_store if material_store is not None else MaterialStoreJson()

    def list_offers(
        self,
        *,
        material_id: str = "",
        material_name: str = "",
        unit: str = "",
    ) -> list[SupplierOffer]:
        target_id = str(material_id or "").strip()
        target_name = str(material_name or "").strip()
        wanted_names = self._wanted_material_names(target_id, target_name)
        offers: list[SupplierOffer] = []

        # 1) Manual competitor/wholesaler offers.
        for row in self._supplier_store.list_for_material(target_id, target_name):
            price = _safe_float(row.get("unit_price", 0.0))
            if price <= 0:
                continue
            row_unit = str(row.get("unit", "") or "").strip()
            if not _same_unit(row_unit, unit):
                continue
            offers.append(
                SupplierOffer(
                    supplier=str(row.get("supplier", "") or "").strip() or "Dostawca",
                    unit_price=price,
                    price_basis=_basis(row.get("price_basis", "unknown")),
                    source=str(row.get("source", "manual") or "manual").strip().lower() or "manual",
                    material_id=str(row.get("material_id", "") or "").strip(),
                    material_name=str(row.get("material_name", "") or "").strip(),
                    unit=row_unit,
                    updated_at=str(row.get("updated_at", "") or "").strip(),
                    note=str(row.get("note", "") or "").strip(),
                )
            )

        # 2) Last known prices from material base.
        material_payload = self._material_store.load()
        rows = material_payload.get("rows", []) if isinstance(material_payload, dict) else []
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                row_id = str(row.get("id", "") or "").strip()
                row_name = str(row.get("nazwa", "") or "").strip()
                if target_id and row_id != target_id:
                    continue
                if not target_id and not _looks_like_same_material(row_name, wanted_names):
                    continue
                last_price = _safe_float(row.get("ostatnia_cena", 0.0))
                default_price = _safe_float(row.get("cena_zl", 0.0))
                chosen_price = last_price if last_price > 0 else default_price
                if chosen_price <= 0:
                    continue
                supplier = str(row.get("dostawca", "") or row.get("producent", "") or "").strip() or "Baza materialu"
                params_low = str(row.get("parametry", "") or "").strip().lower()
                basis = "unknown"
                if "cena: brutto" in params_low:
                    basis = "brutto"
                elif "cena: netto" in params_low:
                    basis = "netto"
                source = "baza_materialu_last_price" if last_price > 0 else "baza_materialu_price"
                offers.append(
                    SupplierOffer(
                        supplier=supplier,
                        unit_price=chosen_price,
                        price_basis=basis,
                        source=source,
                        material_id=row_id,
                        material_name=row_name,
                        unit=str(unit or "").strip(),
                        updated_at=str(row.get("data_zakupu", "") or row.get("data_wpisu", "") or "").strip(),
                        note=str(row.get("numer_faktury", "") or "").strip(),
                    )
                )

        # 3) Historical prices from imported invoices.
        for invoice in self._invoice_store.list_invoices():
            if not isinstance(invoice, dict):
                continue
            supplier = str(invoice.get("supplier", "") or invoice.get("sender", "") or "").strip() or "Faktura"
            inv_basis = _basis(invoice.get("price_basis", "unknown"))
            inv_date = str(invoice.get("invoice_date", "") or invoice.get("received_at", "") or "").strip()
            inv_no = str(invoice.get("invoice_number", "") or invoice.get("attachment_name", "") or "").strip()
            for item in invoice.get("items", []):
                if not isinstance(item, dict):
                    continue
                item_name = str(item.get("name", "") or "").strip()
                if not _looks_like_same_material(item_name, wanted_names):
                    continue
                item_unit = str(item.get("unit", "") or "").strip().lower()
                if not _same_unit(item_unit, unit):
                    continue
                unit_price = _safe_float(item.get("unit_price_gross", 0.0))
                item_basis = "brutto"
                if unit_price <= 0:
                    unit_price = _safe_float(item.get("unit_price", 0.0))
                    item_basis = _basis(item.get("price_basis", inv_basis))
                if unit_price <= 0:
                    unit_price = _safe_float(item.get("unit_price_net", 0.0))
                    item_basis = "netto"
                if unit_price <= 0:
                    continue
                offers.append(
                    SupplierOffer(
                        supplier=supplier,
                        unit_price=unit_price,
                        price_basis=item_basis if item_basis in {"netto", "brutto"} else inv_basis,
                        source="faktura",
                        material_id=target_id,
                        material_name=item_name,
                        unit=item_unit,
                        updated_at=inv_date[:10] if inv_date else "",
                        note=inv_no,
                    )
                )

        return self._dedupe_offers(offers)

    def recommend_for_item(
        self,
        *,
        material_id: str = "",
        material_name: str = "",
        quantity: float = 0.0,
        unit: str = "",
        preferred_basis: str = "brutto",
        current_unit_price: float = 0.0,
    ) -> PriceRecommendation | None:
        offers = self.list_offers(material_id=material_id, material_name=material_name, unit=unit)
        if not offers:
            return None

        basis_pref = _basis(preferred_basis)
        if basis_pref == "unknown":
            basis_pref = "brutto"

        preferred = [offer for offer in offers if offer.price_basis == basis_pref]
        unknown = [offer for offer in offers if offer.price_basis == "unknown"]
        other = [offer for offer in offers if offer.price_basis not in {basis_pref, "unknown"}]

        warning = ""
        compare_pool = preferred
        compare_basis = basis_pref
        skipped = len(offers) - len(preferred)

        if not compare_pool:
            if unknown:
                compare_pool = unknown
                compare_basis = "unknown"
                skipped = len(offers) - len(unknown)
                warning = (
                    f"Brak ofert w cenie {basis_pref}. Pokazano tylko oferty z nieznana baza ceny."
                )
            else:
                compare_pool = other
                compare_basis = other[0].price_basis if other else basis_pref
                skipped = len(offers) - len(compare_pool)
                warning = (
                    f"Brak ofert w cenie {basis_pref}. Pokazano oferty w bazie: {compare_basis}."
                )
        elif skipped > 0:
            warning = (
                f"Pominieto {skipped} ofert z inna baza ceny (np. netto/unknown). "
                f"Porownano tylko {basis_pref}."
            )

        ranked = sorted(compare_pool, key=lambda offer: (offer.unit_price, offer.supplier.lower()))
        best = ranked[0]
        qty = max(0.0, float(quantity or 0.0))
        best_total = best.estimated_total(qty)
        current_total = max(0.0, float(current_unit_price or 0.0)) * qty
        if current_total <= 0 and len(ranked) > 1:
            current_total = ranked[1].estimated_total(qty)
        saving = max(0.0, current_total - best_total)

        return PriceRecommendation(
            best_offer=best,
            ranked_offers=tuple(ranked),
            compare_basis=compare_basis,
            warning=warning,
            skipped_offers=max(0, skipped),
            potential_saving=saving,
            current_total=current_total,
            best_total=best_total,
        )

    def _wanted_material_names(self, material_id: str, material_name: str) -> set[str]:
        names: set[str] = set()
        norm_name = _norm(material_name)
        if norm_name:
            names.add(norm_name)

        if material_id:
            material_payload = self._material_store.load()
            rows = material_payload.get("rows", []) if isinstance(material_payload, dict) else []
            if isinstance(rows, list):
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    if str(row.get("id", "") or "").strip() != material_id:
                        continue
                    row_name = _norm(row.get("nazwa", ""))
                    if row_name:
                        names.add(row_name)
        return names

    @staticmethod
    def _dedupe_offers(offers: list[SupplierOffer]) -> list[SupplierOffer]:
        out: list[SupplierOffer] = []
        seen: set[tuple[str, str, str, str, str]] = set()
        for offer in offers:
            key = (
                offer.supplier.strip().lower(),
                f"{offer.unit_price:.4f}",
                offer.price_basis.strip().lower(),
                offer.source.strip().lower(),
                offer.note.strip().lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(offer)
        return out
