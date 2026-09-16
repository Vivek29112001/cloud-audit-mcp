from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.schemas.aws import (
    AWSAvailabilityZoneResponse,
    AWSDeepScanRequest,
    AWSDeepScanResponse,
    AWSDetectedServiceResponse,
    AWSRegionDiscoveryResponse,
    AWSRegionResponse,
    AWSResourceDiscoveryRequest,
    AWSResourceDiscoveryResponse,
    AWSResourceResponse,
    AWSVerifyRequest,
    AWSVerifyResponse,
    AWSZoneDiscoveryRequest,
    AWSZoneDiscoveryResponse,
)
from app.providers.aws.connection import AWSConnectionService
from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.deep_scan import AWSDeepScanService
from app.providers.aws.discovery import AWSResourceDiscoveryService
from app.providers.aws.exceptions import (
    AWSMCPExecutionError,
    InvalidAWSCredentialsError,
)
from app.providers.aws.models import AWSDetectedService
from app.providers.aws.regions import AWSRegionService
from app.providers.aws.zones import AWSZoneService

from app.providers.aws.scanner import AWSScanOrchestrator

router = APIRouter(
    prefix="/aws",
    tags=["AWS"],
)


# ============================================================
# COMMON
# ============================================================

def build_credentials(
    request: AWSVerifyRequest,
) -> AWSCredentials:

    return AWSCredentials(
        access_key_id=request.access_key_id,
        secret_access_key=request.secret_access_key,
        session_token=request.session_token,
        default_region="us-east-1",
    )


# ============================================================
# MCP DIAGNOSTICS
# ============================================================

@router.post("/mcp/diagnostics")
async def mcp_diagnostics(
    request: AWSVerifyRequest,
):

    credentials = build_credentials(
        request
    )

    client = AWSMCPClient(
        credentials
    )

    try:

        tools = await client.list_tools()

    except Exception as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=(
                f"MCP connection failed: {exc}"
            ),
        ) from exc

    return {
        "connected": True,
        "tool_count": len(tools),
        "tools": [
            tool.name
            for tool in tools
        ],
    }


# ============================================================
# VERIFY AWS ACCOUNT
# ============================================================

@router.post(
    "/verify",
    response_model=AWSVerifyResponse,
)
async def verify_aws_connection(
    request: AWSVerifyRequest,
) -> AWSVerifyResponse:

    credentials = build_credentials(
        request
    )

    service = AWSConnectionService()

    try:

        identity = (
            await service
            .verify_credentials(
                credentials
            )
        )

    except InvalidAWSCredentialsError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=str(exc),
        ) from exc

    except AWSMCPExecutionError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=str(exc),
        ) from exc

    return AWSVerifyResponse(
        provider=identity.provider,
        account_id=identity.account_id,
        arn=identity.arn,
        user_id=identity.user_id,
        connection_status=(
            identity.connection_status
        ),
    )


# ============================================================
# REGION DISCOVERY
# ============================================================

@router.post(
    "/regions",
    response_model=(
        AWSRegionDiscoveryResponse
    ),
)
async def discover_aws_regions(
    request: AWSVerifyRequest,
) -> AWSRegionDiscoveryResponse:

    credentials = build_credentials(
        request
    )

    service = AWSRegionService()

    try:

        result = (
            await service
            .discover_regions(
                credentials
            )
        )

    except AWSMCPExecutionError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=str(exc),
        ) from exc

    return AWSRegionDiscoveryResponse(
        total_regions=(
            result.total_regions
        ),
        enabled_regions=(
            result.enabled_regions
        ),
        disabled_regions=(
            result.disabled_regions
        ),
        regions=[
            AWSRegionResponse(
                region_name=(
                    region.region_name
                ),
                endpoint=region.endpoint,
                opt_in_status=(
                    region.opt_in_status
                ),
                enabled=region.enabled,
            )
            for region
            in result.regions
        ],
    )


# ============================================================
# AVAILABILITY ZONE DISCOVERY
# ============================================================

@router.post(
    "/zones",
    response_model=(
        AWSZoneDiscoveryResponse
    ),
)
async def discover_aws_zones(
    request: AWSVerifyRequest,
) -> AWSZoneDiscoveryResponse:

    credentials = build_credentials(
        request
    )

    region_service = (
        AWSRegionService()
    )

    zone_service = (
        AWSZoneService()
    )

    try:

        region_result = (
            await region_service
            .discover_regions(
                credentials
            )
        )

        enabled_regions = [
            region.region_name
            for region
            in region_result.regions
            if region.enabled
        ]

        zone_result = (
            await zone_service
            .discover_zones(
                credentials=credentials,
                enabled_regions=(
                    enabled_regions
                ),
            )
        )

    except AWSMCPExecutionError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=str(exc),
        ) from exc

    return AWSZoneDiscoveryResponse(
        total_zones=(
            zone_result.total_zones
        ),
        zones=[
            AWSAvailabilityZoneResponse(
                zone_name=zone.zone_name,
                zone_id=zone.zone_id,
                region_name=(
                    zone.region_name
                ),
                state=zone.state,
                zone_type=zone.zone_type,
                opt_in_status=(
                    zone.opt_in_status
                ),
            )
            for zone
            in zone_result.zones
        ],
    )


# ============================================================
# RESOURCE DISCOVERY
# ============================================================

@router.post(
    "/resources/discover",
    response_model=(
        AWSResourceDiscoveryResponse
    ),
)
async def discover_aws_resources(
    request: AWSResourceDiscoveryRequest,
) -> AWSResourceDiscoveryResponse:

    # AWSResourceDiscoveryRequest inherits
    # AWSVerifyRequest, so reuse our helper.
    credentials = build_credentials(
        request
    )

    service = (
        AWSResourceDiscoveryService()
    )

    try:

        result = (
            await service
            .discover_resources(
                credentials=credentials,
                enabled_regions=(
                    request.enabled_regions
                ),
            )
        )

    except AWSMCPExecutionError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=str(exc),
        ) from exc

    return AWSResourceDiscoveryResponse(
        total_resources=(
            result.total_resources
        ),

        used_regions=(
            result.used_regions
        ),

        detected_services=[
            AWSDetectedServiceResponse(
                service=item.service,
                resource_count=(
                    item.resource_count
                ),
                regions=item.regions,
            )
            for item
            in result.detected_services
        ],

        resources=[
            AWSResourceResponse(
                arn=item.arn,
                resource_id=(
                    item.resource_id
                ),
                resource_type=(
                    item.resource_type
                ),
                service=item.service,
                region=item.region,
                owning_account_id=(
                    item.owning_account_id
                ),
                properties=(
                    item.properties
                ),
            )
            for item
            in result.resources
        ],

        warnings=result.warnings,
    )
    
    
@router.post("/deep-scan", response_model=AWSDeepScanResponse)
async def deep_scan_aws(
    request: AWSDeepScanRequest,
) -> AWSDeepScanResponse:
    credentials = _credentials_from_request(request)

    detected_services = [
        AWSDetectedService(
            service=item.service,
            resource_count=item.resource_count,
            regions=item.regions,
        )
        for item in request.detected_services
    ]

    result = await AWSDeepScanService().scan(
        credentials=credentials,
        detected_services=detected_services,
    )

    return AWSDeepScanResponse(
        services=result.services,
        warnings=result.warnings,
    )
    
    
@router.post(
    "/scan"
)
async def run_aws_scan(
    request: AWSVerifyRequest,
):

    credentials = AWSCredentials(
        access_key_id=(
            request.access_key_id
        ),
        secret_access_key=(
            request.secret_access_key
        ),
        session_token=(
            request.session_token
        ),
    )

    scanner = AWSScanOrchestrator()

    result = await scanner.scan(
        credentials
    )

    return result.model_dump(
        mode="json"
    ) 
    
    
    