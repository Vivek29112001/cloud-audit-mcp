from __future__ import annotations

from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.exceptions import AWSMCPExecutionError
from app.providers.aws.mcp_client import AWSMCPClient
from app.providers.aws.models import (
    AWSRegion,
    AWSRegionDiscoveryResult,
)
from app.providers.aws.result_parser import extract_mcp_result


class AWSRegionService:

    async def discover_regions(
        self,
        credentials: AWSCredentials,
    ) -> AWSRegionDiscoveryResult:

        client = AWSMCPClient(credentials)

        script = """
response = await call_boto3(
    service_name="ec2",
    operation_name="DescribeRegions",
    region_name="us-east-1",
    params={
        "AllRegions": True
    }
)

regions = []

for region in response.get("Regions", []):
    regions.append({
        "RegionName": region.get("RegionName"),
        "Endpoint": region.get("Endpoint"),
        "OptInStatus": region.get("OptInStatus"),
    })

result = {
    "Regions": regions
}

result
"""

        try:
            response = await client.execute_aws_script(
                script
            )

        except Exception as exc:
            raise AWSMCPExecutionError(
                f"Unable to discover AWS Regions: {exc}"
            ) from exc

        parsed = extract_mcp_result(response)

        regions_data = self._find_regions(parsed)

        regions: list[AWSRegion] = []

        for item in regions_data:

            region_name = item.get("RegionName")

            if not region_name:
                continue

            opt_in_status = item.get(
                "OptInStatus"
            )

            enabled = opt_in_status in {
                "opt-in-not-required",
                "opted-in",
            }

            regions.append(
                AWSRegion(
                    region_name=region_name,
                    endpoint=item.get(
                        "Endpoint"
                    ),
                    opt_in_status=opt_in_status,
                    enabled=enabled,
                )
            )

        regions.sort(
            key=lambda region: region.region_name
        )

        enabled_count = sum(
            1
            for region in regions
            if region.enabled
        )

        return AWSRegionDiscoveryResult(
            total_regions=len(regions),
            enabled_regions=enabled_count,
            disabled_regions=(
                len(regions) - enabled_count
            ),
            regions=regions,
        )

    @staticmethod
    def _find_regions(
        value: object,
    ) -> list[dict]:

        if isinstance(value, dict):

            regions = value.get("Regions")

            if isinstance(regions, list):
                return regions

            for child in value.values():

                result = (
                    AWSRegionService
                    ._find_regions(child)
                )

                if result:
                    return result

        elif isinstance(value, list):

            for child in value:

                result = (
                    AWSRegionService
                    ._find_regions(child)
                )

                if result:
                    return result

        return []