from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.mcp_client import AWSMCPClient
from app.providers.aws.mcp_scripts.billing import (
    build_billing_discovery_script,
)
from app.providers.aws.models import (
    AWSBillingComponent,
    AWSBillingDiscoveryResult,
    AWSBillingRegionCost,
    AWSBillingServiceCost,
)
from app.providers.aws.result_parser import extract_mcp_result


class AWSBillingDiscoveryService:
    """Discover actual AWS charges dynamically through Cost Explorer."""

    async def discover_billing(
        self,
        credentials: AWSCredentials | None = None,
        *,
        mcp: AWSMCPClient | None = None,
    ) -> AWSBillingDiscoveryResult:
        start_date, end_date = self._current_billing_window()

        if mcp is None:
            if credentials is None:
                raise ValueError(
                    "Either credentials or an open AWSMCPClient session is required."
                )
            async with AWSMCPClient(credentials) as session:
                return await self.discover_billing(mcp=session)

        script = build_billing_discovery_script(
            start_date=start_date,
            end_date=end_date,
        )

        try:
            response = await mcp.run_aws_script(script)
            parsed = extract_mcp_result(response)
            payload = self._find_payload(parsed)
            if payload is None:
                raise ValueError("Cost Explorer returned no structured billing payload.")

            service_costs = [
                AWSBillingServiceCost(
                    billing_service=str(item.get("Service") or "").strip(),
                    amount=self._as_float(item.get("Amount")),
                    unit=str(item.get("Unit") or "USD"),
                )
                for item in payload.get("ServiceCosts", [])
                if str(item.get("Service") or "").strip()
            ]

            components = [
                AWSBillingComponent(
                    billing_service=str(item.get("Service") or "").strip(),
                    usage_type=str(item.get("UsageType") or "").strip(),
                    amount=self._as_float(item.get("Amount")),
                    unit=str(item.get("Unit") or "USD"),
                )
                for item in payload.get("Components", [])
                if str(item.get("Service") or "").strip()
                and str(item.get("UsageType") or "").strip()
            ]

            region_costs = [
                AWSBillingRegionCost(
                    region=str(item.get("Region") or "").strip(),
                    amount=self._as_float(item.get("Amount")),
                    unit=str(item.get("Unit") or "USD"),
                )
                for item in payload.get("RegionCosts", [])
                if str(item.get("Region") or "").strip()
            ]

            service_costs.sort(key=lambda item: (-item.amount, item.billing_service))
            components.sort(
                key=lambda item: (-item.amount, item.billing_service, item.usage_type)
            )
            region_costs.sort(key=lambda item: (-item.amount, item.region))

            units = [item.unit for item in service_costs if item.unit]
            currency = units[0] if units else "USD"

            return AWSBillingDiscoveryResult(
                available=True,
                period_start=start_date,
                period_end_exclusive=end_date,
                metric="UnblendedCost",
                currency=currency,
                total_cost=sum(item.amount for item in service_costs),
                service_costs=service_costs,
                components=components,
                region_costs=region_costs,
            )

        except Exception as exc:
            # Billing permission is independent from infrastructure discovery.
            # Do not fail the entire audit scan when Cost Explorer is unavailable.
            return AWSBillingDiscoveryResult(
                available=False,
                period_start=start_date,
                period_end_exclusive=end_date,
                metric="UnblendedCost",
                warnings=[
                    "Billing discovery unavailable. Grant ce:GetCostAndUsage and "
                    f"ce:GetDimensionValues if billing classification is required: {exc}"
                ],
            )

    @staticmethod
    def _current_billing_window() -> tuple[str, str]:
        """
        Current calendar month, excluding today because Cost Explorer data is delayed.
        On the first day of a month, use the previous full month instead.
        """
        today = date.today()
        first_of_month = today.replace(day=1)

        if today > first_of_month:
            return first_of_month.isoformat(), today.isoformat()

        previous_month_end = first_of_month - timedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1)
        return previous_month_start.isoformat(), first_of_month.isoformat()

    @classmethod
    def _find_payload(cls, value: Any) -> dict[str, Any] | None:
        if isinstance(value, dict):
            if "ServiceCosts" in value and "RegionCosts" in value:
                return value
            for child in value.values():
                found = cls._find_payload(child)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = cls._find_payload(child)
                if found is not None:
                    return found
        return None

    @staticmethod
    def _as_float(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
