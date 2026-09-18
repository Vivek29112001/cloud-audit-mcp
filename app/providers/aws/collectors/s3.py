from __future__ import annotations

from typing import Any

from app.providers.aws.collectors.base import (
    AWSMCPCollector,
)
from app.providers.aws.credentials import (
    AWSCredentials,
)
from app.providers.aws.mcp_client import (
    AWSMCPClient,
)
from app.providers.aws.mcp_scripts.s3_inventory import (
    build_s3_inventory_script,
)
from app.providers.aws.result_parser import (
    extract_mcp_result,
)


class S3MCPCollector(AWSMCPCollector):

    @property
    def service_name(self) -> str:
        return "s3"

    async def collect(
        self,
        credentials: AWSCredentials,
        regions: list[str],
    ) -> dict[str, Any]:
        """
        S3 is effectively account/global discovery here.

        We do not iterate one ListBuckets call per Region.
        Bucket-specific calls use each bucket's dynamically
        discovered Region inside the AWS MCP script.
        """

        client = AWSMCPClient(
            credentials
        )

        script = (
            build_s3_inventory_script()
        )

        response = await client.run_aws_script(
            script
        )

        parsed = extract_mcp_result(
            response
        )

        result = self._find_result(
            parsed
        )

        if not result:
            return {
                "buckets": [],
                "warnings": [
                    "AWS MCP returned no usable "
                    "S3 inventory result."
                ],
            }

        return result

    @staticmethod
    def _find_result(
        value: Any,
    ) -> dict[str, Any] | None:

        if isinstance(value, dict):

            if (
                "buckets" in value
                and isinstance(
                    value["buckets"],
                    list,
                )
            ):
                return value

            for child in value.values():
                found = (
                    S3MCPCollector
                    ._find_result(child)
                )

                if found:
                    return found

        elif isinstance(value, list):

            for child in value:
                found = (
                    S3MCPCollector
                    ._find_result(child)
                )

                if found:
                    return found

        return None