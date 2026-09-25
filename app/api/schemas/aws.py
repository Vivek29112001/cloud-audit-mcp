from __future__ import annotations

from typing import Any

from pydantic import (
    BaseModel,
    Field,
    SecretStr,
)


# ============================================================
# AWS CREDENTIAL REQUEST
# ============================================================


class AWSVerifyRequest(BaseModel):

    access_key_id: str = Field(
        min_length=16,
        max_length=128,
    )

    secret_access_key: SecretStr

    session_token: SecretStr | None = None

    default_region: str = Field(
        default="us-east-1",
        min_length=1,
        max_length=64,
    )


# ============================================================
# AWS VERIFY RESPONSE
# ============================================================


class AWSVerifyResponse(BaseModel):

    provider: str

    account_id: str

    arn: str

    user_id: str

    connection_status: str




class AWSAssumeRoleVerifyRequest(BaseModel):
    role_arn: str = Field(min_length=20, max_length=512)
    external_id: str | None = Field(default=None, max_length=256)
    default_region: str = Field(default="us-east-1", min_length=1, max_length=64)


class AWSConnectionVerifyResponse(BaseModel):
    workspace_id: int
    provider: str
    account_id: str
    arn: str
    user_id: str
    connection_status: str
    aws_connection_id: int
    auth_type: str
    auto_connect: bool
    default_region: str


# ============================================================
# REGION DISCOVERY
# ============================================================


class AWSRegionResponse(BaseModel):

    region_name: str

    endpoint: str | None = None

    opt_in_status: str | None = None

    enabled: bool


class AWSRegionDiscoveryResponse(
    BaseModel
):

    total_regions: int

    enabled_regions: int

    disabled_regions: int

    regions: list[
        AWSRegionResponse
    ]


# ============================================================
# AVAILABILITY ZONES
# ============================================================


class AWSAvailabilityZoneResponse(
    BaseModel
):

    zone_name: str

    zone_id: str | None = None

    region_name: str

    state: str | None = None

    zone_type: str | None = None

    opt_in_status: str | None = None


class AWSZoneDiscoveryResponse(
    BaseModel
):

    total_zones: int

    zones: list[
        AWSAvailabilityZoneResponse
    ]


class AWSZoneDiscoveryRequest(
    AWSVerifyRequest
):

    enabled_regions: list[str] = Field(
        min_length=1,
    )


# ============================================================
# RESOURCE DISCOVERY REQUEST
# ============================================================


class AWSResourceDiscoveryRequest(
    AWSVerifyRequest
):
    """
    Request used for lightweight resource discovery.

    Credentials come from AWSVerifyRequest.

    enabled_regions should come from the dynamic
    Region discovery stage.
    """

    enabled_regions: list[str] = Field(
        min_length=1,
    )


# ============================================================
# RESOURCE RESPONSE
# ============================================================


class AWSResourceResponse(
    BaseModel
):

    arn: str | None = None

    resource_id: str | None = None

    resource_type: str | None = None

    service: str | None = None

    region: str | None = None

    owning_account_id: str | None = None

    properties: list[
        dict[str, Any]
    ] = Field(
        default_factory=list
    )


# ============================================================
# DETECTED SERVICE
# ============================================================


class AWSDetectedServiceResponse(
    BaseModel
):

    service: str

    resource_count: int

    regions: list[str] = Field(
        default_factory=list
    )


# ============================================================
# RESOURCE DISCOVERY RESPONSE
# ============================================================


class AWSResourceDiscoveryResponse(
    BaseModel
):

    total_resources: int

    used_regions: list[str]

    detected_services: list[
        AWSDetectedServiceResponse
    ]

    resources: list[
        AWSResourceResponse
    ]

    warnings: list[str] = Field(
        default_factory=list
    )


# ============================================================
# LEGACY / OPTIONAL DEEP SCAN MODELS
# ============================================================


class AWSDetectedServiceRequest(
    BaseModel
):

    service: str

    resource_count: int

    regions: list[str]


class AWSDeepScanRequest(
    AWSVerifyRequest
):

    detected_services: list[
        AWSDetectedServiceRequest
    ]


class AWSDeepScanResponse(
    BaseModel
):

    services: dict[
        str,
        Any,
    ]

    warnings: list[str]


# ============================================================
# NLP QUERY
# ============================================================


class AWSNaturalLanguageQueryRequest(
    BaseModel
):

    scan_id: str = Field(
        min_length=1,
        max_length=128,
    )

    question: str = Field(
        min_length=1,
        max_length=4000,
    )