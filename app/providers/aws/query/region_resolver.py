from __future__ import annotations

from typing import Any

from app.providers.aws.query.service_scope import (
    AWSServiceScope,
    get_service_scope,
)


class AWSQueryRegionResolver:

    def resolve(
        self,
        *,
        service: str,
        requested_region: str | None,
        service_entry: dict[str, Any] | None,
    ) -> list[str]:

        scope = get_service_scope(
            service
        )

        if scope == AWSServiceScope.GLOBAL:
            return [
                "us-east-1"
            ]

        if requested_region:
            return [
                requested_region
            ]

        if not service_entry:
            return []

        regions = [
            region
            for region
            in service_entry.get(
                "regions",
                []
            )
            if region
            and region != "global"
        ]

        return sorted(
            set(regions)
        )