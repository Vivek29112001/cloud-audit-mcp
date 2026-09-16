from __future__ import annotations


def build_zone_discovery_script(
    enabled_regions: list[str],
) -> str:
    """
    Build the Python script executed inside the official
    AWS Managed MCP Server.

    Availability Zones are discovered only for Regions
    dynamically returned by the previous Region scan.
    """

    return f"""
regions = {enabled_regions!r}

all_zones = []

for region in regions:

    response = await call_boto3(
        service_name="ec2",
        operation_name="DescribeAvailabilityZones",
        region_name=region,
        params={{}}
    )

    for zone in response.get(
        "AvailabilityZones",
        []
    ):
        all_zones.append({{
            "ZoneName": zone.get("ZoneName"),
            "ZoneId": zone.get("ZoneId"),
            "RegionName": zone.get("RegionName"),
            "State": zone.get("State"),
            "ZoneType": zone.get("ZoneType"),
            "OptInStatus": zone.get(
                "OptInStatus"
            )
        }})

result = {{
    "AvailabilityZones": all_zones
}}

result
"""