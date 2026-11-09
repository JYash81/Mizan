"""Deterministic, decimal-precision cost calculation service."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.modules.cost.pricing_catalog import PricingCatalogService
from app.modules.cost.schemas.cost import (
    CostBreakdownItem,
    CostEstimateRequest,
    CostEstimateResponse,
    CostScenarioComparisonResponse,
    CostScenarioItem,
)


class CostEstimatorService:
    """Calculates infrastructure cost estimates using Decimal arithmetic to prevent binary floating-point errors."""

    def __init__(self, catalog_service: PricingCatalogService | None = None) -> None:
        self.catalog_service = catalog_service or PricingCatalogService()

    def calculate_cost(self, db: Session, req: CostEstimateRequest) -> CostEstimateResponse:
        """Calculate transparent cost estimate with billing-unit rounding and component breakdown."""
        now = datetime.now(UTC)
        entry = self.catalog_service.get_entry(
            db,
            provider_name=req.provider_name,
            instance_type=req.instance_type,
            region=req.region,
        )

        warnings: list[str] = []

        # Case 1: Missing pricing record (Strict Invariant: Never default missing price to 0.0)
        if not entry:
            return CostEstimateResponse(
                total_estimated_cost="UNKNOWN",
                currency=req.currency,
                status="PRICE_UNAVAILABLE",
                provider_name=req.provider_name,
                instance_type=req.instance_type,
                region=req.region,
                duration_hours=req.duration_hours,
                duration_source=req.duration_source,
                billable_hours=req.duration_hours,
                billing_unit_seconds=3600,
                pricing_catalog_version="UNKNOWN",
                pricing_provenance=None,
                price_is_verified=False,
                cost_breakdown=[],
                warnings=[
                    f"No verified or reference pricing record found for '{req.provider_name}/{req.instance_type}' in region '{req.region}'. Estimate cannot be calculated.",
                ],
                estimated_at=now,
            )

        # Check for stale or unverified pricing
        if not entry.is_verified:
            warnings.append(
                f"Pricing rate has provenance '{entry.provenance.value}' and is not independently verified."
            )

        # Case 2: Free / Local workstation execution ($0.00 spend)
        hourly_rate_dec = Decimal(entry.hourly_rate)
        if req.provider_name == "local" or hourly_rate_dec == Decimal("0.0000"):
            return CostEstimateResponse(
                total_estimated_cost="0.00",
                currency=req.currency,
                status="ZERO_SPEND_LOCAL",
                provider_name=req.provider_name,
                instance_type=req.instance_type,
                region=req.region,
                duration_hours=req.duration_hours,
                duration_source=req.duration_source,
                billable_hours=req.duration_hours,
                billing_unit_seconds=entry.billing_unit_seconds,
                pricing_catalog_version=entry.catalog_version,
                pricing_provenance=entry.provenance,
                price_is_verified=entry.is_verified,
                cost_breakdown=[
                    CostBreakdownItem(
                        component_name="Local Workstation Compute",
                        quantity=req.duration_hours,
                        unit="Hours",
                        rate="0.00",
                        subtotal="0.00",
                        notes="Local workstation execution under Free-Only Policy: $0.00 additional cloud/provider spend.",
                    )
                ],
                warnings=[
                    "Local workstation execution under Free-Only Policy: $0.00 additional provider spend. Does not account for local electricity or hardware amortization.",
                ],
                estimated_at=now,
            )

        # Case 3: Paid/Cloud Compute Estimation
        billing_unit = max(1, entry.billing_unit_seconds)
        duration_seconds = req.duration_hours * 3600.0
        billable_units = math.ceil(duration_seconds / billing_unit)
        billable_hours_dec = (Decimal(billable_units * billing_unit) / Decimal(3600)).quantize(
            Decimal("0.0001")
        )

        compute_cost = (hourly_rate_dec * billable_hours_dec).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        breakdown: list[CostBreakdownItem] = [
            CostBreakdownItem(
                component_name=f"Compute ({entry.instance_type})",
                quantity=float(billable_hours_dec),
                unit=f"Hours ({billing_unit}s billing unit)",
                rate=str(hourly_rate_dec),
                subtotal=str(compute_cost),
                notes=f"Raw duration {req.duration_hours}h rounded to {billable_hours_dec} billable hours.",
            )
        ]

        # Storage calculation
        storage_cost = Decimal("0.00")
        if req.storage_gb > 0:
            st_rate_str = entry.storage_monthly_rate_per_gb or "0.02"
            st_rate_dec = Decimal(st_rate_str)
            st_hours = Decimal(str(req.storage_duration_hours or req.duration_hours))
            # Average month = 730 hours
            storage_cost = (
                st_rate_dec * Decimal(str(req.storage_gb)) * (st_hours / Decimal(730))
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            breakdown.append(
                CostBreakdownItem(
                    component_name="Workload Artifact Storage",
                    quantity=req.storage_gb,
                    unit="GB-Hours",
                    rate=f"{st_rate_str} / GB-month",
                    subtotal=str(storage_cost),
                    notes=f"Storage duration {st_hours}h across {req.storage_gb} GB.",
                )
            )

        total_cost = compute_cost + storage_cost

        # Range estimation (+/- 20% uncertainty range on duration)
        min_hours_dec = (billable_hours_dec * Decimal("0.85")).quantize(Decimal("0.0001"))
        max_hours_dec = (billable_hours_dec * Decimal("1.25")).quantize(Decimal("0.0001"))
        min_cost = ((hourly_rate_dec * min_hours_dec) + storage_cost).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        max_cost = ((hourly_rate_dec * max_hours_dec) + (storage_cost * Decimal("1.25"))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return CostEstimateResponse(
            total_estimated_cost=str(total_cost),
            currency=entry.currency,
            status="AVAILABLE",
            provider_name=entry.provider_name,
            instance_type=entry.instance_type,
            region=entry.region,
            duration_hours=req.duration_hours,
            duration_source=req.duration_source,
            billable_hours=float(billable_hours_dec),
            billing_unit_seconds=billing_unit,
            pricing_catalog_version=entry.catalog_version,
            pricing_provenance=entry.provenance,
            price_is_verified=entry.is_verified,
            cost_breakdown=breakdown,
            min_estimated_cost=str(min_cost),
            max_estimated_cost=str(max_cost),
            warnings=warnings,
            estimated_at=now,
        )

    def compare_scenarios(
        self, db: Session, duration_hours: float = 2.0, storage_gb: float = 10.0
    ) -> CostScenarioComparisonResponse:
        """Compare infrastructure costs across the 4 approved hardware reference profiles."""
        scenarios = [
            (
                "Local Workstation",
                "LOCAL_CPU_I5_8GB",
                "local",
                "LOCAL_CPU_I5_8GB",
                "local",
                "$0.00 additional cloud spend. Constrained by 8 GB RAM.",
            ),
            (
                "Cloud Small CPU",
                "REFERENCE_CPU_2VCPU_4GB",
                "reference_cloud",
                "REFERENCE_CPU_2VCPU_4GB",
                "us-east-1",
                "Reference generic CPU cloud tier. Low cost, slow inference.",
            ),
            (
                "NVIDIA T4 16GB",
                "NVIDIA_T4_16GB",
                "reference_cloud",
                "NVIDIA_T4_16GB",
                "us-east-1",
                "Vendor reference GPU. Fast inference for models up to 13B parameters.",
            ),
            (
                "NVIDIA A100 40GB",
                "NVIDIA_A100_40GB",
                "reference_cloud",
                "NVIDIA_A100_40GB",
                "us-east-1",
                "High throughput datacenter GPU. Suitable for fine-tuning and large models.",
            ),
        ]

        items: list[CostScenarioItem] = []
        for name, hw_key, provider, inst, reg, notes in scenarios:
            req = CostEstimateRequest(
                provider_name=provider,
                instance_type=inst,
                region=reg,
                duration_hours=duration_hours,
                storage_gb=storage_gb,
            )
            est = self.calculate_cost(db, req)
            prov = est.pricing_provenance.value if est.pricing_provenance else "UNVERIFIED"
            items.append(
                CostScenarioItem(
                    scenario_name=name,
                    hardware_profile_key=hw_key,
                    provider_name=provider,
                    instance_type=inst,
                    estimated_duration_hours=duration_hours,
                    estimated_total_cost=est.total_estimated_cost,
                    currency=est.currency,
                    pricing_provenance=prov,
                    feasibility_notes=notes,
                )
            )

        return CostScenarioComparisonResponse(
            workload_description=f"Comparison for {duration_hours} hours execution and {storage_gb} GB storage",
            scenarios=items,
        )
