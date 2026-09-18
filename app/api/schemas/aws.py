from typing import Any

from pydantic import BaseModel, Field, SecretStr


class AWSVerifyRequest(BaseModel):
    access_key_id: str = Field(
        min_length=16,
        max_length=128,
    )

    secret_access_key: SecretStr

    session_token: SecretStr | None = None


class AWSVerifyResponse(BaseModel):
    provider: str
    account_id: str
    arn: str
    user_id: str
    connection_status: str


class AWSRegionResponse(BaseModel):
    region_name: str
    endpoint: str | None = None
    opt_in_status: str | None = None
    enabled: bool


class AWSRegionDiscoveryResponse(BaseModel):
    total_regions: int
    enabled_regions: int
    disabled_regions: int
    regions: list[AWSRegionResponse]


class AWSAvailabilityZoneResponse(BaseModel):
    zone_name: str
    zone_id: str | None = None
    region_name: str

    state: str | None = None
    zone_type: str | None = None
    opt_in_status: str | None = None


class AWSZoneDiscoveryResponse(BaseModel):
    total_zones: int
    zones: list[AWSAvailabilityZoneResponse]


# ============================================================
# RESOURCE DISCOVERY
# ============================================================

class AWSResourceDiscoveryRequest(
    AWSVerifyRequest
):
    """
    Request used for resource discovery.

    Credentials come from AWSVerifyRequest.

    enabled_regions must come from our previous
    dynamic AWS Region discovery step.
    """

    enabled_regions: list[str] = Field(
        min_length=1,
    )


class AWSResourceResponse(BaseModel):
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


class AWSDetectedServiceResponse(
    BaseModel
):
    service: str

    resource_count: int

    regions: list[str] = Field(
        default_factory=list
    )


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
    
    
    
    
class AWSResourceDiscoveryResponse(BaseModel):
    total_resources: int
    used_regions: list[str]
    detected_services: list[AWSDetectedServiceResponse]
    resources: list[AWSResourceResponse]
    warnings: list[str]


class AWSDetectedServiceRequest(BaseModel):
    service: str
    resource_count: int
    regions: list[str]


class AWSDeepScanRequest(AWSVerifyRequest):
    detected_services: list[AWSDetectedServiceRequest]


class AWSDeepScanResponse(BaseModel):
    services: dict[str, Any]
    warnings: list[str]

class AWSZoneDiscoveryRequest(AWSVerifyRequest):
    enabled_regions: list[str]


class AWSNaturalLanguageQueryRequest(
    AWSVerifyRequest
):
    question: str

    scan_result: dict