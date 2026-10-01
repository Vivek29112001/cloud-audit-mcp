# from __future__ import annotations
# from datetime import date, timedelta
# from typing import Any
# from app.providers.aws.credentials import AWSCredentials
# from app.providers.aws.mcp_client import AWSMCPClient
# from app.providers.aws.mcp_scripts.billing import build_billing_discovery_script
# from app.providers.aws.models import AWSBillingComponent, AWSBillingDiscoveryResult, AWSBillingRegionCost, AWSBillingServiceCost
# from app.providers.aws.result_parser import extract_mcp_result


# class AWSBillingDiscoveryService:
#     async def discover_billing(self, credentials: AWSCredentials | None = None, *, mcp: AWSMCPClient | None = None) -> AWSBillingDiscoveryResult:
#         start_date, end_date = self._current_billing_window()
#         if mcp is None:
#             if credentials is None: raise ValueError("credentials or MCP session required")
#             async with AWSMCPClient(credentials) as session:
#                 return await self.discover_billing(mcp=session)
#         try:
#             parsed = extract_mcp_result(await mcp.run_aws_script(build_billing_discovery_script(start_date=start_date, end_date=end_date)))
#             payload = self._find_payload(parsed)
#             if payload is None: raise ValueError("Cost Explorer returned no structured payload")
#             services = [AWSBillingServiceCost(billing_service=str(i.get("Service") or "").strip(), amount=self._float(i.get("Amount")), unit=str(i.get("Unit") or "USD")) for i in payload.get("ServiceCosts", []) if str(i.get("Service") or "").strip()]
#             components = [AWSBillingComponent(billing_service=str(i.get("Service") or "").strip(), usage_type=str(i.get("UsageType") or "").strip(), amount=self._float(i.get("Amount")), unit=str(i.get("Unit") or "USD")) for i in payload.get("Components", []) if str(i.get("Service") or "").strip() and str(i.get("UsageType") or "").strip()]
#             regions = [AWSBillingRegionCost(region=str(i.get("Region") or "").strip(), amount=self._float(i.get("Amount")), unit=str(i.get("Unit") or "USD")) for i in payload.get("RegionCosts", []) if str(i.get("Region") or "").strip()]
#             services.sort(key=lambda x:(-x.amount,x.billing_service)); components.sort(key=lambda x:(-x.amount,x.billing_service,x.usage_type)); regions.sort(key=lambda x:(-x.amount,x.region))
#             currency = next((x.unit for x in services if x.unit), "USD")
#             return AWSBillingDiscoveryResult(available=True, period_start=start_date, period_end_exclusive=end_date, currency=currency, total_cost=sum(x.amount for x in services), service_costs=services, components=components, region_costs=regions)
#         except Exception as exc:
#             return AWSBillingDiscoveryResult(available=False, period_start=start_date, period_end_exclusive=end_date, warnings=[f"Billing discovery unavailable: {exc}"])

#     @staticmethod
#     def _current_billing_window() -> tuple[str,str]:
#         today=date.today(); first=today.replace(day=1)
#         if today>first: return first.isoformat(), today.isoformat()
#         prev=first-timedelta(days=1); return prev.replace(day=1).isoformat(), first.isoformat()
#     @classmethod
#     def _find_payload(cls,v:Any):
#         if isinstance(v,dict):
#             if "ServiceCosts" in v and "RegionCosts" in v:return v
#             for c in v.values():
#                 f=cls._find_payload(c)
#                 if f is not None:return f
#         if isinstance(v,list):
#             for c in v:
#                 f=cls._find_payload(c)
#                 if f is not None:return f
#         return None
#     @staticmethod
#     def _float(v):
#         try:return float(v or 0)
#         except (TypeError,ValueError):return 0.0


from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from app.providers.aws.billing_mcp_client import AWSBillingMCPClient
from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.models import (
    AWSBillingComponent,
    AWSBillingDiscoveryResult,
    AWSBillingRegionCost,
    AWSBillingServiceCost,
)
from app.providers.aws.result_parser import extract_mcp_result


class AWSBillingDiscoveryService:
    """Collect billing evidence directly from AWS Billing & Cost Management MCP."""

    async def discover_billing(
        self,
        credentials: AWSCredentials,
    ) -> AWSBillingDiscoveryResult:
        start_date, end_date = self._current_billing_window()

        try:
            async with AWSBillingMCPClient(credentials) as billing_mcp:
                service_result = await billing_mcp.get_cost_and_usage(
                    start_date=start_date,
                    end_date=end_date,
                    group_by=[{"Type": "DIMENSION", "Key": "SERVICE"}],
                )
                component_result = await billing_mcp.get_cost_and_usage(
                    start_date=start_date,
                    end_date=end_date,
                    group_by=[
                        {"Type": "DIMENSION", "Key": "SERVICE"},
                        {"Type": "DIMENSION", "Key": "USAGE_TYPE"},
                    ],
                )
                region_result = await billing_mcp.get_cost_and_usage(
                    start_date=start_date,
                    end_date=end_date,
                    group_by=[{"Type": "DIMENSION", "Key": "REGION"}],
                )

            services = self._service_costs(service_result)
            components = self._components(component_result)
            regions = self._region_costs(region_result)

            # A successful Cost Explorer SERVICE query must contain billing
            # groups. Treat an unparseable/empty MCP envelope as unavailable,
            # not as a genuine USD 0.00 account.
            if not services:
                raise RuntimeError(
                    "Billing MCP returned no SERVICE billing groups. "
                    "The tool call succeeded but its response could not be "
                    "interpreted as Cost Explorer data."
                )

            services.sort(key=lambda x: (-x.amount, x.billing_service))
            components.sort(
                key=lambda x: (-x.amount, x.billing_service, x.usage_type)
            )
            regions.sort(key=lambda x: (-x.amount, x.region))

            currency = next((item.unit for item in services if item.unit), "USD")
            return AWSBillingDiscoveryResult(
                available=True,
                period_start=start_date,
                period_end_exclusive=end_date,
                metric="UnblendedCost",
                currency=currency,
                total_cost=sum(item.amount for item in services),
                service_costs=services,
                components=components,
                region_costs=regions,
            )
        except BaseException as exc:
            # ExceptionGroup/TaskGroup errors otherwise collapse to the useless
            # message "unhandled errors in a TaskGroup". Preserve nested cause.
            detail = AWSBillingMCPClient.format_exception(exc)
            return AWSBillingDiscoveryResult(
                available=False,
                period_start=start_date,
                period_end_exclusive=end_date,
                warnings=[f"Billing discovery unavailable: {detail}"],
            )

    @classmethod
    def _service_costs(cls, result: Any) -> list[AWSBillingServiceCost]:
        totals: dict[str, float] = defaultdict(float)
        units: dict[str, str] = {}
        for group in cls._groups(result):
            keys = group.get("Keys") or group.get("keys") or []
            if not keys:
                continue
            service = str(keys[0] or "").strip()
            if not service:
                continue
            amount, unit = cls._metric(group)
            totals[service] += amount
            units[service] = unit
        return [
            AWSBillingServiceCost(
                billing_service=service,
                amount=amount,
                unit=units.get(service, "USD"),
            )
            for service, amount in totals.items()
        ]

    @classmethod
    def _components(cls, result: Any) -> list[AWSBillingComponent]:
        totals: dict[tuple[str, str], float] = defaultdict(float)
        units: dict[tuple[str, str], str] = {}
        for group in cls._groups(result):
            keys = group.get("Keys") or group.get("keys") or []
            if len(keys) < 2:
                continue
            service = str(keys[0] or "").strip()
            usage_type = str(keys[1] or "").strip()
            if not service or not usage_type:
                continue
            pair = (service, usage_type)
            amount, unit = cls._metric(group)
            totals[pair] += amount
            units[pair] = unit
        return [
            AWSBillingComponent(
                billing_service=service,
                usage_type=usage_type,
                amount=amount,
                unit=units.get((service, usage_type), "USD"),
            )
            for (service, usage_type), amount in totals.items()
        ]

    @classmethod
    def _region_costs(cls, result: Any) -> list[AWSBillingRegionCost]:
        totals: dict[str, float] = defaultdict(float)
        units: dict[str, str] = {}
        for group in cls._groups(result):
            keys = group.get("Keys") or group.get("keys") or []
            if not keys:
                continue
            region = str(keys[0] or "").strip()
            if not region:
                continue
            amount, unit = cls._metric(group)
            totals[region] += amount
            units[region] = unit
        return [
            AWSBillingRegionCost(
                region=region,
                amount=amount,
                unit=units.get(region, "USD"),
            )
            for region, amount in totals.items()
        ]

    @classmethod
    def _groups(cls, result: Any) -> list[dict[str, Any]]:
        parsed = extract_mcp_result(result)
        periods = cls._find_results_by_time(parsed)
        groups: list[dict[str, Any]] = []
        for period in periods:
            raw_groups = period.get("Groups") or period.get("groups") or []
            if isinstance(raw_groups, list):
                groups.extend(item for item in raw_groups if isinstance(item, dict))
        return groups

    @classmethod
    def _find_results_by_time(cls, value: Any) -> list[dict[str, Any]]:
        if isinstance(value, dict):
            for key in ("ResultsByTime", "results_by_time"):
                rows = value.get(key)
                if isinstance(rows, list):
                    return [item for item in rows if isinstance(item, dict)]
            for child in value.values():
                found = cls._find_results_by_time(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = cls._find_results_by_time(child)
                if found:
                    return found
        return []

    @classmethod
    def _metric(cls, group: dict[str, Any]) -> tuple[float, str]:
        metrics = group.get("Metrics") or group.get("metrics") or {}
        metric = (
            metrics.get("UnblendedCost")
            or metrics.get("UNBLENDED_COST")
            or metrics.get("unblended_cost")
            or {}
        )
        if not isinstance(metric, dict):
            return 0.0, "USD"
        amount = cls._float(metric.get("Amount", metric.get("amount")))
        unit = str(metric.get("Unit", metric.get("unit", "USD")) or "USD")
        return amount, unit

    @staticmethod
    def _current_billing_window() -> tuple[str, str]:
        today = date.today()
        first = today.replace(day=1)
        if today > first:
            return first.isoformat(), today.isoformat()
        previous_month_last_day = first - timedelta(days=1)
        return previous_month_last_day.replace(day=1).isoformat(), first.isoformat()

    @staticmethod
    def _float(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0


