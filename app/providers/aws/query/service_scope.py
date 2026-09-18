from __future__ import annotations

from enum import Enum


class AWSServiceScope(str, Enum):
    REGIONAL = "REGIONAL"
    GLOBAL = "GLOBAL"


GLOBAL_SERVICES = {
    "iam",
    "organizations",
    "route53",
    "cloudfront",
}


def get_service_scope(
    service: str,
) -> AWSServiceScope:

    if service.lower() in GLOBAL_SERVICES:
        return AWSServiceScope.GLOBAL

    return AWSServiceScope.REGIONAL