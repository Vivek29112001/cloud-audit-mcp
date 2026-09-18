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
from app.providers.aws.mcp_scripts.iam_inventory import (
    build_iam_inventory_script,
)
from app.providers.aws.result_parser import (
    extract_mcp_result,
)


class IAMMCPCollector(
    AWSMCPCollector
):

    @property
    def service_name(self) -> str:
        return "iam"

    async def collect(
        self,
        credentials: AWSCredentials,
        regions: list[str],
    ) -> dict[str, Any]:

        # IAM is handled as an account/global
        # collector, so regions are intentionally
        # not required.

        client = AWSMCPClient(
            credentials
        )

        script = (
            build_iam_inventory_script()
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

        result = self._find_result(
            parsed
        )

        if not result:

            return {
                "account_summary": {},
                "password_policy": None,
                "users": [],
                "roles": [],
                "warnings": [
                    "AWS MCP returned no "
                    "usable IAM inventory."
                ],
            }

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
                "users" in value
                and
                "roles" in value
                and
                "account_summary"
                in value
            ):
                return value

            for child in value.values():

                found = (
                    IAMMCPCollector
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
                    IAMMCPCollector
                    ._find_result(
                        child
                    )
                )

                if found:
                    return found

        return None