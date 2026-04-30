from __future__ import annotations


class QuotePricingService:
    @staticmethod
    def apply_rules(base_total: float, technical_total: float, rules: dict[str, float]) -> float:
        processing_percent = float(rules.get("processing_percent", 0.0) or 0.0)
        assembly_percent = float(rules.get("assembly_percent", 0.0) or 0.0)
        transport_flat = float(rules.get("transport_flat", 0.0) or 0.0)
        processing_cost = float(technical_total) * (processing_percent / 100.0)
        assembly_cost = float(technical_total) * (assembly_percent / 100.0)
        return float(base_total) + processing_cost + assembly_cost + transport_flat

    @staticmethod
    def compute_sale(
        adjusted_base_total: float,
        margin_percent: float,
        policy_multiplier: float,
        architect_commission_percent: float = 0.0,
    ) -> dict[str, float]:
        margin_multiplier = 1.0 + (float(margin_percent) / 100.0)
        base_sale = float(adjusted_base_total) * margin_multiplier * float(policy_multiplier)
        
        commission_amount = base_sale * (float(architect_commission_percent) / 100.0)
        final_sale = base_sale + commission_amount
        
        return {
            "base_sale": round(base_sale, 2),
            "commission": round(commission_amount, 2),
            "final_sale": round(final_sale, 2)
        }
