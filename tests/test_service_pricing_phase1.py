from __future__ import annotations

from src.services.service_pricing_phase1 import (
    SERVICE_PRICING_PAYLOAD_SCHEMA_VERSION,
    price_service_item,
)
from src.storage.service_pricing_tariff_store_json import ServicePricingTariffStoreJson


def _tariffs() -> dict:
    return ServicePricingTariffStoreJson.defaults()


def test_front_cnc_lacquer_requires_model_material_and_thickness() -> None:
    result = price_service_item(
        {
            "service_mode": "service-front-cnc-lacquer",
            "length_mm": 2200,
            "width_mm": 800,
            "quantity": 1,
            "lacquer": True,
            "lacquer_sides": 2,
        },
        tariffs=_tariffs(),
    )
    assert result["schema_version"] == SERVICE_PRICING_PAYLOAD_SCHEMA_VERSION
    assert result["pricing_status"] == "manual_review"
    reasons = set(result["manual_review_reasons"])
    assert "missing_front_model_code" in reasons
    assert "missing_base_material_id" in reasons
    assert "missing_base_thickness_mm" in reasons


def test_unknown_cnc_operations_never_silent_zero() -> None:
    result = price_service_item(
        {
            "service_mode": "service-cut",
            "length_mm": 1000,
            "width_mm": 500,
            "quantity": 1,
            "technology_summary": {
                "drill_count_total": 0,
                "groove_count": 0,
                "milling_count": 0,
                "tool_count_unique": 0,
                "cnc_complexity_score": 0,
                "operation_count_total": 1,
                "unknown_operation_count": 2,
            },
        },
        tariffs=_tariffs(),
    )
    assert result["pricing_status"] == "manual_review"
    assert "unknown_cnc_operations" in result["manual_review_reasons"]


def test_cut_edge_requires_edge_material_when_side_selected() -> None:
    result = price_service_item(
        {
            "service_mode": "service-cut-edge",
            "length_mm": 1200,
            "width_mm": 600,
            "quantity": 1,
            "edge_mode": "default",
            "edge_top": True,
            "edge_bottom": False,
            "edge_left": False,
            "edge_right": False,
        },
        tariffs=_tariffs(),
    )
    assert result["pricing_status"] == "manual_review"
    assert "missing_edge_default_material_id" in result["manual_review_reasons"]


def test_cut_edge_ready_with_default_edge_material() -> None:
    result = price_service_item(
        {
            "service_mode": "service-cut-edge",
            "length_mm": 1200,
            "width_mm": 600,
            "quantity": 2,
            "edge_mode": "default",
            "edge_default_material_id": "edge-abs-1",
            "edge_top": True,
            "edge_bottom": True,
            "edge_left": False,
            "edge_right": False,
        },
        tariffs=_tariffs(),
    )
    assert result["pricing_status"] == "ready"
    assert float(result["buckets"]["cnc_service_cost"]) >= 0.0
    assert float(result["buckets"]["finishing_cost"]) > 0.0
    assert float(result["buckets"]["net_total"]) > 0.0


def test_cut_edge_without_selected_sides_is_ready_and_counts_as_cut_only() -> None:
    result = price_service_item(
        {
            "service_mode": "service-cut-edge",
            "length_mm": 1200,
            "width_mm": 600,
            "quantity": 2,
            "edge_mode": "default",
            "edge_default_material_id": "",
            "edge_top": False,
            "edge_bottom": False,
            "edge_left": False,
            "edge_right": False,
        },
        tariffs=_tariffs(),
    )
    assert result["pricing_status"] == "ready"
    assert any(flag["code"] == "missing_edge_sides" for flag in result["validation_flags"])
    assert float(result["buckets"]["finishing_cost"]) == 0.0
    assert float(result["buckets"]["net_total"]) > 0.0


def test_imported_cnc_summary_populates_cnc_bucket() -> None:
    result = price_service_item(
        {
            "service_mode": "service-cut",
            "length_mm": 2000,
            "width_mm": 800,
            "quantity": 1,
            "technology_summary": {
                "drill_count_total": 12,
                "drill_diameters_mm": [3, 5, 10],
                "drill_depths_mm": [10, 12, 20],
                "groove_count": 2,
                "groove_total_length_mm": 1800,
                "groove_depths_mm": [8.5],
                "milling_count": 1,
                "milling_total_path_length_mm": 2200,
                "milling_arc_count": 3,
                "tool_count_unique": 4,
                "cnc_complexity_score": 42,
                "operation_count_total": 15,
                "unknown_operation_count": 0,
            },
        },
        tariffs=_tariffs(),
    )
    assert result["pricing_status"] == "ready"
    assert float(result["buckets"]["cnc_service_cost"]) > 0.0
    assert any(flag["code"].startswith("complexity_") for flag in result["validation_flags"])


def test_extra_layers_increase_extra_bucket() -> None:
    base_payload = {
        "service_mode": "service-veneer",
        "base_material_id": "mdf-19",
        "base_material_name": "MDF",
        "base_thickness_mm": 19,
        "length_mm": 1800,
        "width_mm": 600,
        "quantity": 1,
        "veneer_sides": 1,
    }
    no_layers = price_service_item(base_payload, tariffs=_tariffs())
    with_layers = price_service_item(
        {
            **base_payload,
            "extra_layers": [
                {
                    "material_id": "v1",
                    "role": "veneer_layer",
                    "thickness_mm": 0.6,
                    "coverage_mode": "both_sides",
                    "quantity_factor": 1,
                },
                {
                    "material_id": "m2",
                    "role": "glued_mdf",
                    "thickness_mm": 3,
                    "coverage_mode": "full",
                    "quantity_factor": 1,
                },
            ],
        },
        tariffs=_tariffs(),
    )
    assert with_layers["pricing_status"] == "ready"
    assert float(with_layers["buckets"]["extra_cost"]) > float(no_layers["buckets"]["extra_cost"])


def test_estimated_milling_length_is_flagged() -> None:
    result = price_service_item(
        {
            "service_mode": "service-cut",
            "length_mm": 1000,
            "width_mm": 500,
            "quantity": 1,
            "technology_summary": {
                "milling_count": 2,
                "milling_total_path_length_mm": 0,
                "milling_length_estimated_mm": 950,
                "operation_count_total": 2,
            },
        },
        tariffs=_tariffs(),
    )
    assert float(result["buckets"]["cnc_service_cost"]) > 0.0
    assert any(flag["code"] == "estimated_milling_length" for flag in result["validation_flags"])
