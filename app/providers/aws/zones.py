from __future__ import annotations

from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.exceptions import AWSMCPExecutionError
from app.providers.aws.mcp_client import AWSMCPClient
from app.providers.aws.models import (
    AWSAvailabilityZone,
    AWSZoneDiscoveryResult,
)
from app.providers.aws.result_parser import (
    extract_mcp_result,
)

from app.providers.aws.mcp_scripts.zone import build_zone_discovery_script

class AWSZoneService:

    async def discover_zones(
        self,
        credentials: AWSCredentials,
        enabled_regions: list[str],
    ) -> AWSZoneDiscoveryResult:

        client = AWSMCPClient(credentials)

        # The Region list comes from AWS discovery.
        # It is NOT hard-coded.
        script = build_zone_discovery_script(
            enabled_regions=enabled_regions
        )

        try:

            # response = (
            #     await client
            #     .execute_aws_script(script)
            # )
            response = ( await client.run_aws_script(script) )

        except Exception as exc:

            raise AWSMCPExecutionError(
                "Unable to discover AWS "
                f"Availability Zones: {exc}"
            ) from exc

        parsed = extract_mcp_result(
            response
        )

        zones_data = self._find_zones(
            parsed
        )

        zones = [
            AWSAvailabilityZone(
                zone_name=item["ZoneName"],
                zone_id=item.get(
                    "ZoneId"
                ),
                region_name=item[
                    "RegionName"
                ],
                state=item.get(
                    "State"
                ),
                zone_type=item.get(
                    "ZoneType"
                ),
                opt_in_status=item.get(
                    "OptInStatus"
                ),
            )
            for item in zones_data
            if item.get("ZoneName")
        ]

        zones.sort(
            key=lambda zone: (
                zone.region_name,
                zone.zone_name,
            )
        )

        return AWSZoneDiscoveryResult(
            total_zones=len(zones),
            zones=zones,
        )

    @staticmethod
    def _find_zones(
        value: object,
    ) -> list[dict]:

        if isinstance(value, dict):

            zones = value.get(
                "AvailabilityZones"
            )

            if isinstance(zones, list):
                return zones

            for child in value.values():

                result = (
                    AWSZoneService
                    ._find_zones(child)
                )

                if result:
                    return result

        elif isinstance(value, list):

            for child in value:

                result = (
                    AWSZoneService
                    ._find_zones(child)
                )

                if result:
                    return result

        return []