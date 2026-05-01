from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.storage.service_pricing_tariff_store_json import ServicePricingTariffStoreJson


SERVICE_PRICING_PAYLOAD_SCHEMA_VERSION = "service_pricing_payload_v1"


SERVICE_MODES = {
    "service-cut",
    "service-cut-edge",
    "service-front-cnc-lacquer",
    "service-veneer",
    "service-bent-elements",
}


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _i(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _s(value: Any) -> str:
    return str(value or "").strip()


def _round2(value: float) -> float:
    return round(float(value or 0.0), 2)


def _normalize_list_of_numbers(values: Any) -> List[float]:
    if not isinstance(values, list):
        return []
    out: List[float] = []
    for item in values:
        try:
            out.append(float(item))
        except Exception:
            continue
    return out


def _complexity_multiplier(tariffs: Dict[str, Any], score: float) -> Tuple[float, str]:
    bands = (((tariffs.get("complexity") or {}).get("bands") or []))
    for band in bands:
        try:
            if score <= float(band.get("max_score", 0)):
                return float(band.get("multiplier", 1.0) or 1.0), str(band.get("code", "low") or "low")
        except Exception:
            continue
    return 1.0, "low"


def _normalize_extra_layers(raw_layers: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not isinstance(raw_layers, list):
        return out
    for row in raw_layers:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "material_id": _s(row.get("material_id")),
                "role": _s(row.get("role")) or "overlay",
                "thickness_mm": _f(row.get("thickness_mm"), 0.0),
                "coverage_mode": _s(row.get("coverage_mode")) or "full",
                "quantity_factor": max(0.0, _f(row.get("quantity_factor"), 1.0)),
                "notes": _s(row.get("notes")),
            }
        )
    return out


def normalize_service_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    mode = _s(raw.get("service_mode") or raw.get("serviceMode"))
    tech = raw.get("technology_summary") if isinstance(raw.get("technology_summary"), dict) else {}
    thickness = _f(raw.get("base_thickness_mm") or raw.get("thickness_mm"), 0.0)
    length = max(0.0, _f(raw.get("length_mm"), 0.0))
    width = max(0.0, _f(raw.get("width_mm"), 0.0))
    qty = max(1, _i(raw.get("quantity"), 1))
    edge_sides = {
        "top": bool(raw.get("edge_top", False)),
        "bottom": bool(raw.get("edge_bottom", False)),
        "left": bool(raw.get("edge_left", False)),
        "right": bool(raw.get("edge_right", False)),
    }

    normalized = {
        "schema_version": SERVICE_PRICING_PAYLOAD_SCHEMA_VERSION,
        "service_mode": mode,
        "service_subtype": _s(raw.get("service_subtype")),
        "part_name": _s(raw.get("part_name")),
        "part_type": _s(raw.get("part_type")),
        "length_mm": length,
        "width_mm": width,
        "base_thickness_mm": thickness,
        "quantity": qty,
        "base_material_id": _s(raw.get("base_material_id") or raw.get("baseMaterialId")),
        "base_material_name": _s(raw.get("base_material_name") or raw.get("baseMaterialName")),
        "base_material_price_m2": _f(raw.get("base_material_price_m2"), 0.0),
        "front_model_code": _s(raw.get("front_model_code")),
        "front_model_name": _s(raw.get("front_model_name")),
        "edge_mode": _s(raw.get("edge_mode")) or "default",
        "edge_default_material_id": _s(raw.get("edge_default_material_id")),
        "edge_top_material_id": _s(raw.get("edge_top_material_id")),
        "edge_bottom_material_id": _s(raw.get("edge_bottom_material_id")),
        "edge_left_material_id": _s(raw.get("edge_left_material_id")),
        "edge_right_material_id": _s(raw.get("edge_right_material_id")),
        "edge_sides": edge_sides,
        "cnc_pattern": _s(raw.get("cnc_pattern") or raw.get("cncPattern")) or "line",
        "lacquer": bool(raw.get("lacquer", False)),
        "lacquer_sides": 2 if _i(raw.get("lacquer_sides"), 1) == 2 else 1,
        "veneer_sides": 2 if _i(raw.get("veneer_sides"), 1) == 2 else 1,
        "veneer_lacquer": bool(raw.get("veneer_lacquer", False)),
        "bent_shape": _s(raw.get("bent_shape")) or "arc",
        "bent_radius_mm": max(0.0, _f(raw.get("bent_radius_mm"), 0.0)),
        "bent_complexity": str(max(1, min(3, _i(raw.get("bent_complexity"), 1)))),
        "extra_layers": _normalize_extra_layers(raw.get("extra_layers")),
        "technology_summary": {
            "drill_count_total": max(0, _i(tech.get("drill_count_total"), 0)),
            "drill_diameters_mm": _normalize_list_of_numbers(tech.get("drill_diameters_mm")),
            "drill_depths_mm": _normalize_list_of_numbers(tech.get("drill_depths_mm")),
            "groove_count": max(0, _i(tech.get("groove_count"), 0)),
            "groove_total_length_mm": max(0.0, _f(tech.get("groove_total_length_mm"), 0.0)),
            "groove_depths_mm": _normalize_list_of_numbers(tech.get("groove_depths_mm")),
            "milling_count": max(0, _i(tech.get("milling_count"), 0)),
            "milling_total_path_length_mm": max(0.0, _f(tech.get("milling_total_path_length_mm"), 0.0)),
            "milling_length_estimated_mm": max(0.0, _f(tech.get("milling_length_estimated_mm"), 0.0)),
            "milling_arc_count": max(0, _i(tech.get("milling_arc_count"), 0)),
            "tool_count_unique": max(0, _i(tech.get("tool_count_unique"), 0)),
            "cnc_complexity_score": max(0.0, _f(tech.get("cnc_complexity_score"), 0.0)),
            "operation_count_total": max(0, _i(tech.get("operation_count_total"), 0)),
            "unknown_operation_count": max(
                0,
                _i(raw.get("unknown_operation_count"), _i(tech.get("unknown_operation_count"), 0)),
            ),
        },
        "operation_tariff": raw.get("operation_tariff"),
    }
    return normalized


def _validate(normalized: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]], List[str]]:
    flags: List[Dict[str, Any]] = []
    reasons: List[str] = []
    mode = _s(normalized.get("service_mode"))

    if mode not in SERVICE_MODES:
        flags.append(
            {
                "code": "unsupported_service_mode",
                "severity": "error",
                "message": "Nieobslugiwany tryb uslugi dla kalkulacji fazy 1.",
            }
        )
        reasons.append("unsupported_service_mode")

    requires_material_thickness = {
        "service-front-cnc-lacquer",
        "service-veneer",
        "service-bent-elements",
    }
    if mode in requires_material_thickness:
        if not _s(normalized.get("base_material_id")):
            flags.append(
                {
                    "code": "missing_base_material_id",
                    "severity": "error",
                    "message": "Brak base_material_id (wymagane dla tego trybu).",
                }
            )
            reasons.append("missing_base_material_id")
        if _f(normalized.get("base_thickness_mm"), 0.0) <= 0:
            flags.append(
                {
                    "code": "missing_base_thickness_mm",
                    "severity": "error",
                    "message": "Brak base_thickness_mm (wymagane dla tego trybu).",
                }
            )
            reasons.append("missing_base_thickness_mm")

    if mode == "service-front-cnc-lacquer" and not _s(normalized.get("front_model_code")):
        flags.append(
            {
                "code": "missing_front_model_code",
                "severity": "error",
                "message": "Brak front_model_code (wymagane dla frezowania frontu + lakieru).",
            }
        )
        reasons.append("missing_front_model_code")

    if mode == "service-cut-edge":
        edge_sides = normalized.get("edge_sides") or {}
        selected_side_count = sum(1 for side in ("top", "bottom", "left", "right") if bool(edge_sides.get(side)))
        if selected_side_count <= 0:
            flags.append(
                {
                    "code": "missing_edge_sides",
                    "severity": "warning",
                    "message": "Nie wybrano stron oklejania - liczony tylko rozkroj.",
                }
            )
        edge_mode = _s(normalized.get("edge_mode")) or "default"
        if selected_side_count > 0:
            if edge_mode == "default":
                if not _s(normalized.get("edge_default_material_id")):
                    flags.append(
                        {
                            "code": "missing_edge_default_material_id",
                            "severity": "error",
                            "message": "Brak edge_default_material_id dla wybranego oklejania.",
                        }
                    )
                    reasons.append("missing_edge_default_material_id")
            else:
                for side in ("top", "bottom", "left", "right"):
                    if bool(edge_sides.get(side)) and not _s(normalized.get(f"edge_{side}_material_id")):
                        flags.append(
                            {
                                "code": f"missing_edge_{side}_material_id",
                                "severity": "error",
                                "message": f"Brak materialu oklejania dla strony: {side}.",
                            }
                        )
                        reasons.append(f"missing_edge_{side}_material_id")

    tech = normalized.get("technology_summary") or {}
    if _i(tech.get("unknown_operation_count"), 0) > 0:
        flags.append(
            {
                "code": "unknown_cnc_operations",
                "severity": "error",
                "message": "Wykryto nieznane operacje CNC - wymagana recenzja reczna.",
            }
        )
        reasons.append("unknown_cnc_operations")

    status = "manual_review" if reasons else "ready"
    return status, flags, reasons


def _material_bucket(normalized: Dict[str, Any], tariffs: Dict[str, Any]) -> float:
    area_m2 = (normalized["length_mm"] * normalized["width_mm"] * normalized["quantity"]) / 1_000_000.0
    base_price = _f((normalized.get("base_material_price_m2") or 0.0), 0.0)
    if base_price <= 0:
        base_price = _f(((tariffs.get("materials") or {}).get("default_base_price_per_m2")), 0.0)

    thickness_mm = int(round(_f(normalized.get("base_thickness_mm"), 0.0)))
    thickness_map = ((tariffs.get("materials") or {}).get("thickness_multipliers") or {})
    thickness_multiplier = _f(thickness_map.get(str(thickness_mm), 1.0), 1.0)
    return max(0.0, area_m2 * base_price * thickness_multiplier)


def _cnc_bucket_from_summary(normalized: Dict[str, Any], tariffs: Dict[str, Any], flags: List[Dict[str, Any]]) -> float:
    tech = normalized.get("technology_summary") or {}
    drilling = tariffs.get("drilling") or {}
    grooves = tariffs.get("grooves") or {}
    milling = tariffs.get("milling") or {}
    tooling = tariffs.get("tooling") or {}

    drill_count = _i(tech.get("drill_count_total"), 0)
    drill_cost = drill_count * _f(drilling.get("base_per_hole"), 0.0)

    small_max = _f(((drilling.get("diameter_breakpoints_mm") or {}).get("small_max")), 4.0)
    medium_max = _f(((drilling.get("diameter_breakpoints_mm") or {}).get("medium_max")), 8.0)
    band_surcharge = drilling.get("diameter_band_surcharge") or {}
    diameters = _normalize_list_of_numbers(tech.get("drill_diameters_mm"))
    for diameter in diameters:
        if diameter <= small_max:
            drill_cost += _f(band_surcharge.get("small"), 0.0)
        elif diameter <= medium_max:
            drill_cost += _f(band_surcharge.get("medium"), 0.0)
        else:
            drill_cost += _f(band_surcharge.get("large"), 0.0)

    depth_info = drilling.get("depth_surcharge_per_hole") or {}
    deep_from = _f(depth_info.get("deep_from_mm"), 16.0)
    deep_surcharge = _f(depth_info.get("deep_surcharge"), 0.0)
    depths = _normalize_list_of_numbers(tech.get("drill_depths_mm"))
    deep_depths = len([d for d in depths if d >= deep_from])
    if deep_depths > 0 and drill_count > 0:
        drill_cost += deep_surcharge * drill_count

    groove_count = _i(tech.get("groove_count"), 0)
    groove_len_m = _f(tech.get("groove_total_length_mm"), 0.0) / 1000.0
    groove_cost = groove_count * _f(grooves.get("setup_per_groove"), 0.0) + groove_len_m * _f(
        grooves.get("per_meter"), 0.0
    )
    groove_depths = _normalize_list_of_numbers(tech.get("groove_depths_mm"))
    if groove_depths:
        avg_depth = sum(groove_depths) / max(1, len(groove_depths))
        depth_factor = grooves.get("depth_factor") or {}
        if avg_depth >= _f(depth_factor.get("deep_from_mm"), 8.0):
            groove_cost *= _f(depth_factor.get("deep_multiplier"), 1.0)

    milling_count = _i(tech.get("milling_count"), 0)
    milling_len_mm = _f(tech.get("milling_total_path_length_mm"), 0.0)
    estimated = False
    if milling_len_mm <= 0:
        milling_len_mm = _f(tech.get("milling_length_estimated_mm"), 0.0)
        estimated = milling_len_mm > 0
    milling_len_m = milling_len_mm / 1000.0
    milling_cost = milling_count * _f(milling.get("setup_per_path"), 0.0) + milling_len_m * _f(
        milling.get("per_meter"), 0.0
    )
    milling_cost += _i(tech.get("milling_arc_count"), 0) * _f(milling.get("per_arc"), 0.0)
    if estimated and milling_len_m > 0:
        milling_cost *= _f(milling.get("estimated_length_multiplier"), 1.0)
        flags.append(
            {
                "code": "estimated_milling_length",
                "severity": "warning",
                "message": "Dlugosc frezowania jest estymowana.",
            }
        )

    tool_unique = _i(tech.get("tool_count_unique"), 0)
    baseline_tools = _i(tooling.get("baseline_tools"), 1)
    additional_tools = max(0, tool_unique - baseline_tools)
    tool_cost = additional_tools * _f(tooling.get("per_additional_tool"), 0.0)

    cnc_base = drill_cost + groove_cost + milling_cost + tool_cost
    multiplier, complexity_code = _complexity_multiplier(tariffs, _f(tech.get("cnc_complexity_score"), 0.0))
    if complexity_code != "low":
        flags.append(
            {
                "code": f"complexity_{complexity_code}",
                "severity": "info",
                "message": f"Zastosowano mnoznik zlozonosci: {complexity_code}.",
            }
        )
    return max(0.0, cnc_base * multiplier)


def _manual_mode_buckets(normalized: Dict[str, Any], tariffs: Dict[str, Any]) -> Tuple[float, float]:
    mode = _s(normalized.get("service_mode"))
    modes = (tariffs.get("manual_modes") or {})
    area_m2 = (normalized["length_mm"] * normalized["width_mm"] * normalized["quantity"]) / 1_000_000.0
    perimeter_m = ((normalized["length_mm"] + normalized["width_mm"]) * 2.0 * normalized["quantity"]) / 1000.0
    side_count = sum(1 for side in ("top", "bottom", "left", "right") if normalized["edge_sides"].get(side))
    edge_mb = (perimeter_m * side_count) / 4.0

    cnc_fallback = 0.0
    finishing_cost = 0.0

    if mode == "service-cut":
        cnc_fallback = area_m2 * _f((modes.get(mode) or {}).get("cut_per_m2"), 0.0)
    elif mode == "service-cut-edge":
        cfg = modes.get(mode) or {}
        cnc_fallback = area_m2 * _f(cfg.get("cut_per_m2"), 0.0)
        finishing_cost += edge_mb * _f(cfg.get("edge_per_mb"), 0.0)
    elif mode == "service-front-cnc-lacquer":
        cfg = modes.get(mode) or {}
        pattern = _s(normalized.get("cnc_pattern")) or "line"
        cnc_per_m2 = _f(((cfg.get("cnc_per_m2") or {}).get(pattern)), _f((cfg.get("cnc_per_m2") or {}).get("line"), 0.0))
        cnc_fallback = area_m2 * cnc_per_m2 + _f(cfg.get("front_model_setup"), 0.0)
        if bool(normalized.get("lacquer")):
            lacquer_cfg = cfg.get("lacquer_per_m2") or {}
            lacquer_rate = _f(lacquer_cfg.get("two_sides"), 0.0) if _i(normalized.get("lacquer_sides"), 1) == 2 else _f(
                lacquer_cfg.get("one_side"), 0.0
            )
            finishing_cost += area_m2 * lacquer_rate
    elif mode == "service-veneer":
        cfg = modes.get(mode) or {}
        veneer_sides = 2 if _i(normalized.get("veneer_sides"), 1) == 2 else 1
        finishing_cost += area_m2 * veneer_sides * _f(cfg.get("veneer_per_m2_side"), 0.0)
        if bool(normalized.get("veneer_lacquer")):
            lacquer_cfg = cfg.get("veneer_lacquer_per_m2") or {}
            finishing_cost += area_m2 * (
                _f(lacquer_cfg.get("two_sides"), 0.0) if veneer_sides == 2 else _f(lacquer_cfg.get("one_side"), 0.0)
            )
        finishing_cost += edge_mb * _f(cfg.get("edge_per_mb"), 0.0)
    elif mode == "service-bent-elements":
        cfg = modes.get(mode) or {}
        shape = _s(normalized.get("bent_shape")) or "arc"
        complexity = _s(normalized.get("bent_complexity")) or "1"
        shape_rate = _f((cfg.get("shape_per_m2") or {}).get(shape), _f((cfg.get("shape_per_m2") or {}).get("arc"), 0.0))
        complexity_mult = _f((cfg.get("complexity_multiplier") or {}).get(complexity), 1.0)
        finishing_cost += area_m2 * shape_rate * complexity_mult
        if 0 < _f(normalized.get("bent_radius_mm"), 0.0) < _f(cfg.get("small_radius_threshold_mm"), 0.0):
            finishing_cost += normalized["quantity"] * _f(cfg.get("small_radius_surcharge_per_item"), 0.0)

    return max(0.0, cnc_fallback), max(0.0, finishing_cost)


def _extra_bucket(normalized: Dict[str, Any], tariffs: Dict[str, Any]) -> float:
    role_rates = (((tariffs.get("layers") or {}).get("role_surcharge_per_m2") or {}))
    area_m2 = (normalized["length_mm"] * normalized["width_mm"] * normalized["quantity"]) / 1_000_000.0
    total = 0.0
    for layer in normalized.get("extra_layers", []):
        role = _s(layer.get("role")) or "overlay"
        factor = max(0.0, _f(layer.get("quantity_factor"), 1.0))
        thickness = _f(layer.get("thickness_mm"), 0.0)
        coverage_mode = _s(layer.get("coverage_mode")) or "full"
        coverage_mult = 2.0 if coverage_mode == "both_sides" else 1.0
        total += area_m2 * coverage_mult * factor * _f(role_rates.get(role), 0.0)
        if thickness > 0:
            total += area_m2 * factor * (thickness / 100.0)
    return max(0.0, total)


def _operation_bucket(normalized: dict[str, Any]) -> float:
    tariff = normalized.get("operation_tariff")
    if not isinstance(tariff, dict):
        return 0.0

    rate = _f(tariff.get("sell_rate_net"), 0.0)
    unit = _s(tariff.get("unit")).lower()
    min_charge = _f(tariff.get("min_charge_net"), 0.0)

    length_mm = normalized["length_mm"]
    width_mm = normalized["width_mm"]
    qty = normalized["quantity"]

    area_m2 = (length_mm * width_mm * qty) / 1_000_000.0
    edge_sides = normalized.get("edge_sides") or {}
    edge_mb = 0.0
    if edge_sides.get("top"):
        edge_mb += (width_mm * qty) / 1000.0
    if edge_sides.get("bottom"):
        edge_mb += (width_mm * qty) / 1000.0
    if edge_sides.get("left"):
        edge_mb += (length_mm * qty) / 1000.0
    if edge_sides.get("right"):
        edge_mb += (length_mm * qty) / 1000.0

    cost = 0.0
    if unit == "mb":
        cost = edge_mb * rate
    elif unit == "m2":
        cost = area_m2 * rate
    elif unit == "szt":
        cost = qty * rate

    return max(cost, min_charge) if cost > 0 or min_charge > 0 else 0.0


def _summary_text(normalized: dict[str, Any], buckets: dict[str, float], status: str) -> str:
    mode = _s(normalized.get("service_mode")) or "unknown"
    material = _s(normalized.get("base_material_name")) or _s(normalized.get("base_material_id")) or "-"
    tech = normalized.get("technology_summary") or {}
    tech_bits = (
        f"D{_i(tech.get('drill_count_total'), 0)} "
        f"G{_i(tech.get('groove_count'), 0)} "
        f"M{_i(tech.get('milling_count'), 0)} "
        f"T{_i(tech.get('tool_count_unique'), 0)} "
        f"C={_f(tech.get('cnc_complexity_score'), 0.0):.0f}"
    )
    op_name = _s((normalized.get("operation_tariff") or {}).get("name"))
    op_info = f" | {op_name}" if op_name else ""

    return (
        f"{mode}{op_info} | {material} {_f(normalized.get('base_thickness_mm'), 0.0):.0f}mm | {tech_bits} | "
        f"mat {buckets['material_cost']:.2f} + cnc {buckets['cnc_service_cost']:.2f} + "
        f"fin {buckets['finishing_cost']:.2f} + op {buckets['operation_cost']:.2f} + ext {buckets['extra_cost']:.2f} = "
        f"{buckets['net_total']:.2f} ({status})"
    )


def price_service_item(raw_item: dict[str, Any], tariffs: dict[str, Any] | None = None) -> dict[str, Any]:
    store = ServicePricingTariffStoreJson()
    tariffs_payload = tariffs if isinstance(tariffs, dict) else store.load()
    normalized = normalize_service_item(raw_item if isinstance(raw_item, dict) else {})

    status, flags, reasons = _validate(normalized)

    material_cost = _material_bucket(normalized, tariffs_payload)
    cnc_cost_from_import = _cnc_bucket_from_summary(normalized, tariffs_payload, flags)
    manual_cnc_fallback, manual_finishing = _manual_mode_buckets(normalized, tariffs_payload)
    cnc_service_cost = cnc_cost_from_import if cnc_cost_from_import > 0 else manual_cnc_fallback
    finishing_cost = manual_finishing
    extra_cost = _extra_bucket(normalized, tariffs_payload)
    operation_cost = _operation_bucket(normalized)

    buckets = {
        "material_cost": _round2(material_cost),
        "cnc_service_cost": _round2(cnc_service_cost),
        "finishing_cost": _round2(finishing_cost),
        "extra_cost": _round2(extra_cost),
        "operation_cost": _round2(operation_cost),
    }
    buckets["net_total"] = _round2(
        buckets["material_cost"] + buckets["cnc_service_cost"] + buckets["finishing_cost"] + buckets["extra_cost"] + buckets["operation_cost"]
    )

    summary = _summary_text(normalized, buckets, status)


    return {
        "schema_version": SERVICE_PRICING_PAYLOAD_SCHEMA_VERSION,
        "tariff_schema_version": _s(tariffs_payload.get("schema_version")),
        "normalized_item": normalized,
        "buckets": buckets,
        "pricing_status": status,
        "validation_flags": flags,
        "manual_review_reasons": reasons,
        "summary_text": summary,
    }
