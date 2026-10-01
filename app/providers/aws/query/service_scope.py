# from __future__ import annotations

# from enum import Enum


# class AWSServiceScope(str, Enum):
#     REGIONAL = "REGIONAL"
#     GLOBAL = "GLOBAL"


# GLOBAL_SERVICES = {
#     "iam",
#     "organizations",
#     "route53",
#     "cloudfront",
# }


# def get_service_scope(
#     service: str,
# ) -> AWSServiceScope:

#     if service.lower() in GLOBAL_SERVICES:
#         return AWSServiceScope.GLOBAL

#     return AWSServiceScope.REGIONAL



from __future__ import annotations

from enum import Enum
from typing import Any, Iterable


class AWSServiceScope(str, Enum):
    REGIONAL = "REGIONAL"
    GLOBAL = "GLOBAL"
    UNKNOWN = "UNKNOWN"


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().lower()


def _extract_service(resource: dict[str, Any]) -> str:
    """
    Extract the service namespace dynamically from discovered resource data.

    Priority:
    1. resource['service']
    2. resource['service_namespace']
    3. ARN namespace
    """

    service = _normalize(
        resource.get("service")
        or resource.get("service_namespace")
    )

    if service:
        return service

    arn = _normalize(resource.get("arn"))

    if arn.startswith("arn:"):
        parts = arn.split(":", 5)
        if len(parts) >= 3:
            return _normalize(parts[2])

    return ""


def _extract_region(resource: dict[str, Any]) -> str:
    """Extract the region from discovered AWS resource metadata."""

    return _normalize(
        resource.get("region")
        or resource.get("aws_region")
        or resource.get("Region")
    )


def get_service_scope(
    service: str,
    resources: Iterable[dict[str, Any]] | None = None,
) -> AWSServiceScope:
    """
    Determine service scope from actual discovered resource evidence.

    No hardcoded AWS global-service list is used.

    REGIONAL:
        At least one discovered resource for the service has a real region.

    GLOBAL:
        Resources for the service exist, but all have empty/global region data.

    UNKNOWN:
        There is no discovered resource evidence for the service.
    """

    normalized_service = _normalize(service)

    if not normalized_service:
        return AWSServiceScope.UNKNOWN

    if resources is None:
        return AWSServiceScope.UNKNOWN

    matched_resources: list[dict[str, Any]] = []

    for resource in resources:
        if not isinstance(resource, dict):
            continue

        if _extract_service(resource) != normalized_service:
            continue

        matched_resources.append(resource)

    if not matched_resources:
        return AWSServiceScope.UNKNOWN

    actual_regions: set[str] = set()

    for resource in matched_resources:
        region = _extract_region(resource)

        if not region:
            continue

        if region in {"global", "aws-global"}:
            continue

        actual_regions.add(region)

    if actual_regions:
        return AWSServiceScope.REGIONAL

    return AWSServiceScope.GLOBAL


