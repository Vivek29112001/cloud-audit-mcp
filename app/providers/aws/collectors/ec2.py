from __future__ import annotations

from typing import Any

from app.providers.aws.collectors.base import AWSMCPCollector
from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.mcp_client import AWSMCPClient
from app.providers.aws.models import AWSEC2DeepScanResult
from app.providers.aws.result_parser import (
    extract_mcp_result,
    find_dict_with_keys,
)

from app.providers.aws.mcp_scripts.ec2_inventory import build_ec2_inventory_script

class EC2MCPCollector(AWSMCPCollector):
    @property
    def service_name(self) -> str:
        return "ec2"

    async def collect(
        self,
        credentials: AWSCredentials,
        regions: list[str],
    ) -> dict[str, Any]:
        client = AWSMCPClient(credentials)

        all_data: dict[str, Any] = {
            "instances": [],
            "security_groups": [],
            "volumes": [],
            "subnets": [],
            "route_tables": [],
            "warnings": [],
        }

        for region in sorted(set(regions)):
            if not region or region == "global":
                continue

            try:
                result = await self._collect_region(
                    client=client,
                    region=region,
                )

                for key in (
                    "instances",
                    "security_groups",
                    "volumes",
                    "subnets",
                    "route_tables",
                ):
                    all_data[key].extend(result.get(key, []))

            except Exception as exc:
                all_data["warnings"].append(
                    f"EC2 deep scan failed for {region}: {exc}"
                )

        # Validate/normalize the complete output with Pydantic.
        validated = AWSEC2DeepScanResult.model_validate(all_data)
        return validated.model_dump()

    async def _collect_region(
        self,
        client: AWSMCPClient,
        region: str,
    ) -> dict[str, Any]:
        script = build_ec2_inventory_script(region)


        # response = await client.execute_aws_script(script)
        response = await client.run_aws_script(script)
        parsed = extract_mcp_result(response)

        expected = {
            "instances",
            "security_groups",
            "volumes",
            "subnets",
            "route_tables",
        }

        found = find_dict_with_keys(parsed, expected)
        if not found:
            raise RuntimeError(
                f"EC2 MCP response for {region} did not contain "
                "the expected deep-scan structure."
            )

        return found
