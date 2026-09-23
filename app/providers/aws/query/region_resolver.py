from __future__ import annotations

from typing import Any


class AWSQueryRegionResolver:

    def resolve(
        self,
        *,
        service: str,
        requested_region: str | None,
        service_entry: dict[str, Any] | None,
        fallback_region: str,
    ) -> list[str]:
        """
        Resolve query Regions without a hard-coded global-service list.

        Order of evidence:
        1. Region explicitly requested by the user/NLP plan.
        2. Regions observed for the service in Resource Explorer.
        3. The verified connection's default Region as a control-plane fallback.

        Global AWS SDK services can still resolve their global endpoint when a
        Region is supplied to the SDK client; therefore no IAM/Route53/etc.
        lookup table is required here.
        """
        if requested_region:
            return [requested_region]

        if service_entry:
            regions = [
                region
                for region in service_entry.get("regions", [])
                if region and region != "global"
            ]
            if regions:
                return sorted(set(regions))

        return [fallback_region] if fallback_region else []
