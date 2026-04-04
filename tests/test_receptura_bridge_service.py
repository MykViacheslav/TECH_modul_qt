from __future__ import annotations

from src.services.receptura_bridge_service import (
    build_catalog_material_from_receptura,
    build_quick_quote_entry_from_receptura,
    catalog_material_key_from_receptura_id,
)


def test_build_quick_quote_entry_from_receptura_uses_values_and_ids() -> None:
    entry = build_quick_quote_entry_from_receptura(
        {
            "id": "R0042",
            "name": "Plyta 18 biala",
            "unit": "m2",
            "quantity": 2.5,
            "price_net": 48.0,
            "vat_percent": 23.0,
        },
        existing_ids={"QREC_R0042_20260330_120000"},
    )

    assert str(entry.get("id", "")).startswith("QREC_R0042_")
    assert entry.get("client") == "RECEPTURA"
    assert entry.get("price") == "120.00 zl"
    assert entry.get("vat") == "23%"
    sections = entry.get("sections", [])
    assert isinstance(sections, list) and len(sections) == 1
    assert sections[0].get("id") == "R0042"


def test_build_catalog_material_from_receptura_maps_fields() -> None:
    row = build_catalog_material_from_receptura(
        {
            "id": "R0007",
            "name": "Front MDF 19 mm",
            "material_type": "front",
            "unit": "m2",
            "price_net": 85.5,
            "notes": "Lakier mat",
        }
    )

    assert row["key"] == catalog_material_key_from_receptura_id("R0007")
    assert row["name_pl"] == "Front MDF 19 mm"
    assert row["manufacturer"] == "Receptura"
    assert row["material_group"] == "front_board"
    assert abs(float(row["thickness_mm"]) - 19.0) < 0.01
    assert abs(float(row["price_pln_per_m2"]) - 85.5) < 0.01
