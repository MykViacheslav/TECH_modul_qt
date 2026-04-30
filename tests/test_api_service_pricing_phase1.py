from __future__ import annotations

import json
from pathlib import Path

from src.api import main_api
from src.api.data_manager import TechModulDataManager
from src.services.service_pricing_phase1 import SERVICE_PRICING_PAYLOAD_SCHEMA_VERSION


def test_service_pricing_preview_endpoint_returns_backend_result() -> None:
    payload = main_api.ServicePricingPreviewRequest(
        item={
            "service_mode": "service-front-cnc-lacquer",
            "length_mm": 2000,
            "width_mm": 700,
            "quantity": 1,
            "lacquer": True,
            "lacquer_sides": 2,
        }
    )
    result = main_api.preview_service_pricing(payload)
    assert result["status"] == "ok"
    assert result["schema_version"] == SERVICE_PRICING_PAYLOAD_SCHEMA_VERSION
    assert result["result"]["pricing_status"] == "manual_review"
    assert "missing_front_model_code" in result["result"]["manual_review_reasons"]


def test_create_order_applies_backend_service_pricing_to_spec_json(tmp_path: Path) -> None:
    manager = TechModulDataManager(db_path=str(tmp_path / "service_pricing_order.db"))
    project_id = manager.create_project("PROJECT-SP1", "Client SP1")
    previous_manager = main_api.data_manager

    spec_payload = {
        "positions": [
            {
                "id": "pos-1",
                "name": "Front usluga",
                "quantity": 1,
                "serviceMode": "service-front-cnc-lacquer",
                "servicePricingInput": {
                    "service_mode": "service-front-cnc-lacquer",
                    "service_subtype": "service-front-cnc-lacquer",
                    "base_material_id": "mdf-19",
                    "base_material_name": "MDF surowy",
                    "base_material_price_m2": 100.0,
                    "base_thickness_mm": 19,
                    "front_model_code": "F-001",
                    "length_mm": 2100,
                    "width_mm": 700,
                    "quantity": 1,
                    "lacquer": True,
                    "lacquer_sides": 2,
                    "technology_summary": {
                        "drill_count_total": 6,
                        "groove_count": 1,
                        "groove_total_length_mm": 600,
                        "milling_count": 1,
                        "milling_total_path_length_mm": 1500,
                        "tool_count_unique": 2,
                        "cnc_complexity_score": 25,
                        "operation_count_total": 8,
                    },
                },
            }
        ]
    }

    try:
        main_api.data_manager = manager
        created = main_api.create_order(
            main_api.OrderCreate(
                project_id=project_id,
                client_name="Klient SP1",
                title="Order pricing phase1",
                status="DRAFT",
                spec_json=json.dumps(spec_payload),
            )
        )
        assert created["status"] == "success"
        order_id = int(created["id"])
        assert order_id > 0

        listed = main_api.get_orders(project_id=project_id)
        assert len(listed) >= 1
        saved = next(row for row in listed if int(row["id"]) == order_id)
        saved_spec = json.loads(saved.get("spec_json") or "{}")

        assert saved_spec["service_pricing_schema_version"] == SERVICE_PRICING_PAYLOAD_SCHEMA_VERSION
        assert saved_spec["service_pricing_backend_calculated"] is True
        assert isinstance(saved_spec.get("positions"), list)
        priced_position = saved_spec["positions"][0]
        assert isinstance(priced_position.get("servicePricing"), dict)
        service_pricing = priced_position["servicePricing"]
        assert service_pricing["schema_version"] == SERVICE_PRICING_PAYLOAD_SCHEMA_VERSION
        assert priced_position["serviceEstimatedNet"] == service_pricing["buckets"]["net_total"]
        assert str(priced_position.get("serviceSummary") or "").strip() != ""
    finally:
        main_api.data_manager = previous_manager


def test_create_order_applies_backend_service_pricing_to_unified_service_rows(tmp_path: Path) -> None:
    manager = TechModulDataManager(db_path=str(tmp_path / "service_pricing_service_rows.db"))
    project_id = manager.create_project("PROJECT-SP2", "Client SP2")
    previous_manager = main_api.data_manager

    spec_payload = {
        "service_rows": [
            {
                "id": "srv-1",
                "name": "Formatka importowana",
                "quantity": 2,
                "serviceMode": "service-cut-edge",
                "servicePricingInput": {
                    "service_mode": "service-cut-edge",
                    "service_subtype": "service-cut-edge",
                    "base_material_id": "mdf-18",
                    "base_material_name": "MDF 18",
                    "base_material_price_m2": 95.0,
                    "base_thickness_mm": 18,
                    "length_mm": 1200,
                    "width_mm": 500,
                    "quantity": 2,
                    "edge_mode": "default",
                    "edge_default_material_id": "abs-1",
                    "edge_top": True,
                    "edge_bottom": True,
                    "edge_left": False,
                    "edge_right": False,
                    "technology_summary": {
                        "drill_count_total": 4,
                        "groove_count": 0,
                        "milling_count": 1,
                        "milling_total_path_length_mm": 500,
                        "tool_count_unique": 2,
                        "cnc_complexity_score": 8,
                        "operation_count_total": 5,
                    },
                },
            }
        ]
    }

    try:
        main_api.data_manager = manager
        created = main_api.create_order(
            main_api.OrderCreate(
                project_id=project_id,
                client_name="Klient SP2",
                title="Order unified rows phase1",
                status="DRAFT",
                spec_json=json.dumps(spec_payload),
            )
        )
        order_id = int(created["id"])
        saved = next(row for row in main_api.get_orders(project_id=project_id) if int(row["id"]) == order_id)
        saved_spec = json.loads(saved.get("spec_json") or "{}")

        assert saved_spec["service_pricing_schema_version"] == SERVICE_PRICING_PAYLOAD_SCHEMA_VERSION
        assert saved_spec["service_pricing_backend_calculated"] is True
        assert isinstance(saved_spec.get("service_rows"), list)

        priced_row = saved_spec["service_rows"][0]
        assert isinstance(priced_row.get("servicePricing"), dict)
        assert priced_row["servicePricing"]["pricing_status"] == "ready"
        assert float(priced_row["servicePricing"]["buckets"]["net_total"]) > 0.0
        assert str(priced_row.get("serviceSummary") or "").strip() != ""
    finally:
        main_api.data_manager = previous_manager


def test_create_order_prices_mixed_manual_and_imported_rows(tmp_path: Path) -> None:
    manager = TechModulDataManager(db_path=str(tmp_path / "service_pricing_mixed_rows.db"))
    project_id = manager.create_project("PROJECT-SP3", "Client SP3")
    previous_manager = main_api.data_manager

    spec_payload = {
        "service_rows": [
            {
                "id": "manual-1",
                "name": "Manual front CNC",
                "quantity": 1,
                "serviceMode": "service-front-cnc-lacquer",
                "servicePricingInput": {
                    "service_mode": "service-front-cnc-lacquer",
                    "service_subtype": "service-front-cnc-lacquer",
                    "base_material_id": "mdf-22",
                    "base_material_name": "MDF 22",
                    "base_material_price_m2": 120.0,
                    "base_thickness_mm": 22,
                    "front_model_code": "FM-22-A",
                    "length_mm": 2100,
                    "width_mm": 500,
                    "quantity": 1,
                    "lacquer": True,
                    "lacquer_sides": 2,
                },
            },
            {
                "id": "imported-1",
                "name": "Imported formatka",
                "quantity": 2,
                "serviceMode": "service-cut-edge",
                "servicePricingInput": {
                    "service_mode": "service-cut-edge",
                    "service_subtype": "service-cut-edge",
                    "base_material_id": "mdf-18",
                    "base_material_name": "MDF 18",
                    "base_material_price_m2": 95.0,
                    "base_thickness_mm": 18,
                    "length_mm": 1200,
                    "width_mm": 450,
                    "quantity": 2,
                    "edge_mode": "default",
                    "edge_default_material_id": "abs-1",
                    "edge_top": True,
                    "edge_bottom": True,
                    "edge_left": False,
                    "edge_right": False,
                    "technology_summary": {
                        "drill_count_total": 2,
                        "groove_count": 1,
                        "groove_total_length_mm": 450,
                        "milling_count": 1,
                        "milling_total_path_length_mm": 700,
                        "tool_count_unique": 2,
                        "cnc_complexity_score": 7,
                        "operation_count_total": 4,
                    },
                },
            },
        ]
    }

    try:
        main_api.data_manager = manager
        created = main_api.create_order(
            main_api.OrderCreate(
                project_id=project_id,
                client_name="Klient SP3",
                title="Order mixed rows phase1",
                status="DRAFT",
                spec_json=json.dumps(spec_payload),
            )
        )
        order_id = int(created["id"])
        saved = next(row for row in main_api.get_orders(project_id=project_id) if int(row["id"]) == order_id)
        saved_spec = json.loads(saved.get("spec_json") or "{}")
        rows = saved_spec.get("service_rows") or []

        assert saved_spec["service_pricing_schema_version"] == SERVICE_PRICING_PAYLOAD_SCHEMA_VERSION
        assert len(rows) == 2
        assert all(isinstance(r.get("servicePricing"), dict) for r in rows)
        assert all(str(r.get("serviceSummary") or "").strip() for r in rows)
        assert all(float((r.get("servicePricing") or {}).get("buckets", {}).get("net_total", 0.0)) > 0.0 for r in rows)
        assert all((r.get("servicePricing") or {}).get("pricing_status") == "ready" for r in rows)
    finally:
        main_api.data_manager = previous_manager
