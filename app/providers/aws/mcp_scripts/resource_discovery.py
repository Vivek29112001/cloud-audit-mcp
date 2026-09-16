from __future__ import annotations


def build_resource_discovery_script(
    region: str,
) -> str:
    """
    Build a Resource Explorer search script for one Region.

    The script executes inside AWS Managed MCP Server.

    Pagination is handled completely inside the MCP script.
    """

    return f"""
region = {region!r}

resources = []

next_token = None

while True:

    params = {{
        "QueryString": "",
        "MaxResults": 1000
    }}

    if next_token:
        params["NextToken"] = next_token

    response = await call_boto3(
        service_name="resource-explorer-2",
        operation_name="Search",
        region_name=region,
        params=params
    )

    for item in response.get(
        "Resources",
        []
    ):
        resources.append({{
            "Arn": item.get("Arn"),
            "Region": item.get("Region"),
            "ResourceType": item.get(
                "ResourceType"
            ),
            "Service": item.get(
                "Service"
            ),
            "OwningAccountId": item.get(
                "OwningAccountId"
            ),
            "Properties": item.get(
                "Properties",
                []
            )
        }})

    next_token = response.get(
        "NextToken"
    )

    if not next_token:
        break

result = {{
    "Resources": resources
}}

result
"""