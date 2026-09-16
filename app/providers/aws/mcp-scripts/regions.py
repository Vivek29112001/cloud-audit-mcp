from __future__ import annotations


def build_region_discovery_script() -> str:
    """
    Build the Python script executed inside the official
    AWS Managed MCP Server.

    This script discovers all AWS Regions and their
    account opt-in status.
    """

    return """
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
        "OptInStatus": region.get("OptInStatus")
    })

result = {
    "Regions": regions
}

result
"""