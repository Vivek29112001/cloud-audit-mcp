from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from app.providers.aws.connection import (
    AWSConnectionService,
)
from app.providers.aws.credentials import (
    AWSCredentials,
)
from app.providers.aws.discovery import (
    AWSResourceDiscoveryService,
)
from app.providers.aws.mcp_client import (
    AWSMCPClient,
)
from app.providers.aws.models import (
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

    async def scan(
        self,
        credentials: AWSCredentials,
    ) -> AWSScanResult:

        result = AWSScanResult(
            scan_id=str(
                uuid4()
            ),
            status="RUNNING",
            started_at=datetime.now(
                timezone.utc
            ),
        )

        scan_started = (
            perf_counter()
        )

        timings: dict[
            str,
            int,
        ] = {}

        try:
            #
            # Open ONE reusable MCP session for the complete
            # baseline discovery pipeline.
            #
            async with AWSMCPClient(
                credentials
            ) as mcp:

                #
                # 1. ACCOUNT IDENTITY
                #
                stage_started = (
                    perf_counter()
                )

                identity = (
                    await self.connection_service
                    .verify_credentials(
                        mcp=mcp
                    )
                )

                timings[
                    "identity_ms"
                ] = self._elapsed_ms(
                    stage_started
                )

                result.account = (
                    identity
                )

                #
                # 2. REGION DISCOVERY
                #
                stage_started = (
                    perf_counter()
                )

                regions = (
                    await self.region_service
                    .discover_regions(
                        mcp=mcp
                    )
                )

                timings[
                    "regions_ms"
                ] = self._elapsed_ms(
                    stage_started
                )

                result.regions = (
                    regions
                )

                enabled_regions = [
                    region.region_name
                    for region
                    in regions.regions
                    if region.enabled
                ]

                #
                # 3. ZONE DISCOVERY
                #
                # The existing zone script receives all enabled
                # Regions in one MCP execution.
                #
                stage_started = (
                    perf_counter()
                )

                zones = (
                    await self.zone_service
                    .discover_zones(
                        enabled_regions=(
                            enabled_regions
                        ),
                        mcp=mcp,
                    )
                )

                timings[
                    "zones_ms"
                ] = self._elapsed_ms(
                    stage_started
                )

                result.zones = zones

                #
                # 4. LIGHTWEIGHT RESOURCE / SERVICE DISCOVERY
                #
                # Regional Resource Explorer calls are bounded and
                # concurrent, using this same MCP session.
                #
                stage_started = (
                    perf_counter()
                )

                resources = (
                    await self.resource_service
                    .discover_resources(
                        enabled_regions=(
                            enabled_regions
                        ),
                        mcp=mcp,
                    )
                )

                timings[
                    "resource_discovery_ms"
                ] = self._elapsed_ms(
                    stage_started
                )

                result.resources = (
                    resources
                )

                result.warnings.extend(
                    resources.warnings
                )

                #
                # 5. SUMMARY
                #
                result.summary = (
                    AWSScanSummary(
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
                    )
                )

                result.status = (
                    "COMPLETED"
                )

        except Exception as exc:
            result.status = "FAILED"

            result.warnings.append(
                str(exc)
            )

        finally:
            timings[
                "total_ms"
            ] = self._elapsed_ms(
                scan_started
            )

            result.timings = (
                timings
            )

            result.completed_at = (
                datetime.now(
                    timezone.utc
                )
            )

        return result

    @staticmethod
    def _elapsed_ms(
        started_at: float,
    ) -> int:
        return round(
            (
                perf_counter()
                - started_at
            )
            * 1000
        )
