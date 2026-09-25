from __future__ import annotations
from datetime import date, timedelta
from typing import Any
from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.mcp_client import AWSMCPClient
from app.providers.aws.mcp_scripts.billing import build_billing_discovery_script
from app.providers.aws.models import AWSBillingComponent, AWSBillingDiscoveryResult, AWSBillingRegionCost, AWSBillingServiceCost
from app.providers.aws.result_parser import extract_mcp_result


class AWSBillingDiscoveryService:
    async def discover_billing(self, credentials: AWSCredentials | None = None, *, mcp: AWSMCPClient | None = None) -> AWSBillingDiscoveryResult:
        start_date, end_date = self._current_billing_window()
        if mcp is None:
            if credentials is None: raise ValueError("credentials or MCP session required")
            async with AWSMCPClient(credentials) as session:
                return await self.discover_billing(mcp=session)
        try:
            parsed = extract_mcp_result(await mcp.run_aws_script(build_billing_discovery_script(start_date=start_date, end_date=end_date)))
            payload = self._find_payload(parsed)
            if payload is None: raise ValueError("Cost Explorer returned no structured payload")
            services = [AWSBillingServiceCost(billing_service=str(i.get("Service") or "").strip(), amount=self._float(i.get("Amount")), unit=str(i.get("Unit") or "USD")) for i in payload.get("ServiceCosts", []) if str(i.get("Service") or "").strip()]
            components = [AWSBillingComponent(billing_service=str(i.get("Service") or "").strip(), usage_type=str(i.get("UsageType") or "").strip(), amount=self._float(i.get("Amount")), unit=str(i.get("Unit") or "USD")) for i in payload.get("Components", []) if str(i.get("Service") or "").strip() and str(i.get("UsageType") or "").strip()]
            regions = [AWSBillingRegionCost(region=str(i.get("Region") or "").strip(), amount=self._float(i.get("Amount")), unit=str(i.get("Unit") or "USD")) for i in payload.get("RegionCosts", []) if str(i.get("Region") or "").strip()]
            services.sort(key=lambda x:(-x.amount,x.billing_service)); components.sort(key=lambda x:(-x.amount,x.billing_service,x.usage_type)); regions.sort(key=lambda x:(-x.amount,x.region))
            currency = next((x.unit for x in services if x.unit), "USD")
            return AWSBillingDiscoveryResult(available=True, period_start=start_date, period_end_exclusive=end_date, currency=currency, total_cost=sum(x.amount for x in services), service_costs=services, components=components, region_costs=regions)
        except Exception as exc:
            return AWSBillingDiscoveryResult(available=False, period_start=start_date, period_end_exclusive=end_date, warnings=[f"Billing discovery unavailable: {exc}"])

    @staticmethod
    def _current_billing_window() -> tuple[str,str]:
        today=date.today(); first=today.replace(day=1)
        if today>first: return first.isoformat(), today.isoformat()
        prev=first-timedelta(days=1); return prev.replace(day=1).isoformat(), first.isoformat()
    @classmethod
    def _find_payload(cls,v:Any):
        if isinstance(v,dict):
            if "ServiceCosts" in v and "RegionCosts" in v:return v
            for c in v.values():
                f=cls._find_payload(c)
                if f is not None:return f
        if isinstance(v,list):
            for c in v:
                f=cls._find_payload(c)
                if f is not None:return f
        return None
    @staticmethod
    def _float(v):
        try:return float(v or 0)
        except (TypeError,ValueError):return 0.0
