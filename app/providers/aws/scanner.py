from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.providers.aws.connection import (
    AWSConnectionService,
)
from app.providers.aws.credentials import (
    AWSCredentials,
)
from app.providers.aws.deep_scan import (
    AWSDeepScanService,
)
from app.providers.aws.discovery import (
    AWSResourceDiscoveryService,
)
from app.providers.aws.models import (
    AWSDetectedService,
    AWSScanResult,
    AWSScanSummary,
)
from app.providers.aws.regions import (
    AWSRegionService,
)
from app.providers.aws.zones import (
    AWSZoneService,
)


class AWSScanOrchestrator:

    def __init__(self) -> None:

        self.connection_service = (
            AWSConnectionService()
        )

        self.region_service = (
            AWSRegionService()
        )

        self.zone_service = (
            AWSZoneService()
        )

        self.resource_service = (
            AWSResourceDiscoveryService()
        )

        self.deep_scan_service = (
            AWSDeepScanService()
        )

    async def scan(
        self,
        credentials: AWSCredentials,
    ) -> AWSScanResult:

        scan_id = str(uuid4())

        started_at = datetime.now(
            timezone.utc
        )

        result = AWSScanResult(
            scan_id=scan_id,
            status="RUNNING",
            started_at=started_at,
        )

        try:

            #
            # 1. ACCOUNT IDENTITY
            #

            identity = (
                await self.connection_service
                .verify_credentials(
                    credentials
                )
            )

            result.account = identity

            #
            # 2. REGION DISCOVERY
            #

            regions = (
                await self.region_service
                .discover_regions(
                    credentials
                )
            )

            result.regions = regions

            enabled_regions = [
                region.region_name
                for region in regions.regions
                if region.enabled
            ]

            #
            # 3. ZONE DISCOVERY
            #

            zones = (
                await self.zone_service
                .discover_zones(
                    credentials=credentials,
                    enabled_regions=(
                        enabled_regions
                    ),
                )
            )

            result.zones = zones

            #
            # 4. BROAD RESOURCE DISCOVERY
            #

            resources = (
                await self.resource_service
                .discover_resources(
                    credentials=credentials,
                    enabled_regions=(
                        enabled_regions
                    ),
                )
            )

            result.resources = resources

            result.warnings.extend(
                resources.warnings
            )

            #
            # 5. DEEP SERVICE COLLECTION
            #

            deep_scan = (
                await self.deep_scan_service
                .scan(
                    credentials=credentials,
                    detected_services=(
                        resources
                        .detected_services
                    ),
                )
            )

            result.deep_scan = deep_scan

            result.warnings.extend(
                deep_scan.get(
                    "warnings",
                    []
                )
            )

            #
            # 6. SUMMARY
            #

            result.summary = AWSScanSummary(
                account_id=(
                    identity.account_id
                ),

                enabled_regions=(
                    regions.enabled_regions
                ),

                disabled_regions=(
                    regions.disabled_regions
                ),

                availability_zones=(
                    zones.total_zones
                ),

                used_regions=len(
                    resources.used_regions
                ),

                detected_services=len(
                    resources
                    .detected_services
                ),

                discovered_resources=(
                    resources.total_resources
                ),

                deep_scanned_services=len(
                    deep_scan.get(
                        "services",
                        {}
                    )
                ),
            )

            result.status = "COMPLETED"

        except Exception as exc:

            result.status = "FAILED"

            result.warnings.append(
                str(exc)
            )

        finally:

            result.completed_at = (
                datetime.now(
                    timezone.utc
                )
            )

        return result