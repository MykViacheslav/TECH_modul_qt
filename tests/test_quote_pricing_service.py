from __future__ import annotations

from pathlib import Path

from src.services.quote_pricing_service import QuotePricingService
from src.storage.quote_pricing_store_json import QuotePricingStoreJson


def test_quote_pricing_service_applies_rules_and_policy() -> None:
    service = QuotePricingService()
    adjusted = service.apply_rules(
        base_total=1000.0,
        technical_total=800.0,
        rules={"processing_percent": 10.0, "assembly_percent": 5.0, "transport_flat": 50.0},
    )
    assert adjusted == 1170.0
    sale = service.compute_sale(adjusted, margin_percent=20.0, policy_multiplier=0.9)
    assert round(sale, 2) == 1263.60


def test_quote_pricing_store_roundtrip(tmp_path: Path) -> None:
    store = QuotePricingStoreJson(path=tmp_path / "quote_pricing.json")
    store.save(
        {
            "active_policy": "dealer",
            "policy_multipliers": {"base": 1.0, "dealer": 0.91, "promo": 0.87, "internal": 0.7},
            "rules": {"processing_percent": 12.0, "assembly_percent": 4.0, "transport_flat": 123.0},
            "active_role": "sales",
        }
    )
    payload = store.load()
    assert payload["active_policy"] == "dealer"
    assert float(payload["policy_multipliers"]["dealer"]) == 0.91
    assert float(payload["rules"]["transport_flat"]) == 123.0
    assert payload["active_role"] == "sales"
