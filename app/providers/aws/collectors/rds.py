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
from app.providers.aws.mcp_scripts.rds_inventory import (
    build_rds_inventory_script,
)
from app.providers.aws.result_parser import (
    extract_mcp_result,
)


class RDSMCPCollector(
    AWSMCPCollector
):

    @property
    def service_name(self) -> str:
        return "rds"

    async def collect(
        self,
        credentials: AWSCredentials,
        regions: list[str],
    ) -> dict[str, Any]:

        client = AWSMCPClient(
            credentials
        )

        result = {
            "instances": [],
            "clusters": [],
            "warnings": [],
        }

        for region in regions:

            try:
                script = (
                    build_rds_inventory_script(
                        region
                    )
                )

                response = (
                    await client
                    .run_aws_script(
                        script
                    )
                )

                parsed = extract_mcp_result(
                    response
                )

                regional = (
                    self._find_result(
                        parsed
                    )
                )

                if not regional:

                    result[
                        "warnings"
                    ].append(
                        "No usable RDS MCP "
                        f"result for {region}."
                    )

                    continue

                result[
                    "instances"
                ].extend(
                    regional.get(
                        "instances",
                        [],
                    )
                )

                result[
                    "clusters"
                ].extend(
                    regional.get(
                        "clusters",
                        [],
                    )
                )

                result[
                    "warnings"
                ].extend(
                    regional.get(
                        "warnings",
                        [],
                    )
                )

            except Exception as exc:

                result[
                    "warnings"
                ].append(
                    f"RDS scan failed for "
                    f"{region}: {exc}"
                )

        return result

    @staticmethod
    def _find_result(
        value: Any,
    ) -> dict[str, Any] | None:

        if isinstance(
            value,
            dict,
        ):

            if (
                "instances" in value
                and
                "clusters" in value
            ):
                return value

            for child in value.values():

                found = (
                    RDSMCPCollector
                    ._find_result(
                        child
                    )
                )

                if found:
                    return found

        elif isinstance(
            value,
            list,
        ):

            for child in value:

                found = (
                    RDSMCPCollector
                    ._find_result(
                        child
                    )
                )

                if found:
                    return found

        return None