from __future__ import annotations

import json
from typing import Any

from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.mcp_client import AWSMCPClient
from app.providers.aws.query.read_only_validator import (
    AWSReadOnlyOperationValidator,
)
from app.providers.aws.query.result_parser import (
    find_generic_query_result,
)
from app.providers.aws.result_parser import (
    extract_mcp_result,
)


class AWSGenericQueryExecutor:

    def __init__(self) -> None:
        self._validator = AWSReadOnlyOperationValidator()

    async def execute(
        self,
        *,
        service: str,
        operation: str,
        region: str,
        params: dict[str, Any] | None = None,
        credentials: AWSCredentials | None = None,
        mcp: AWSMCPClient | None = None,
    ) -> Any:
        """
        Execute one read-only AWS API operation through the
        official AWS Managed MCP Server.

        Preferred usage:
            execute(..., mcp=existing_session)

        Standalone compatibility:
            execute(..., credentials=credentials)

        The existing MCP session is reused when supplied.
        """

        service = service.strip().lower()
        operation = operation.strip()

        self._validator.validate(
            service=service,
            operation=operation,
        )

        safe_params = params or {}

        #
        # Standalone compatibility mode.
        #
        # If the caller has not supplied an already-open MCP
        # session, create one temporary session for this query.
        #
        if mcp is None:

            if credentials is None:
                raise ValueError(
                    "Either credentials or an open "
                    "AWSMCPClient session is required."
                )

            async with AWSMCPClient(
                credentials
            ) as session:

                return await self.execute(
                    service=service,
                    operation=operation,
                    region=region,
                    params=safe_params,
                    mcp=session,
                )

        #
        # Reuse the already-open MCP session.
        #

        script = self._build_script(
            service=service,
            operation=operation,
            region=region,
            params=safe_params,
        )

        response = await mcp.run_aws_script(
            script
        )

        parsed = extract_mcp_result(
            response
        )

        query_result = find_generic_query_result(
            parsed
        )

        if not query_result:
            raise RuntimeError(
                "AWS MCP returned a response, "
                "but the generic AWS query result "
                "could not be extracted."
            )

        return query_result

    @staticmethod
    def _build_script(
        *,
        service: str,
        operation: str,
        region: str,
        params: dict[str, Any],
    ) -> str:
        """
        Build the Python script that is executed inside the
        official AWS Managed MCP Server.

        Important:
        - This code is NOT executed locally.
        - call_boto3() exists inside the AWS MCP execution environment.
        - Supports common AWS pagination patterns.
        """

        service_json = json.dumps(
            service
        )

        operation_json = json.dumps(
            operation
        )

        region_json = json.dumps(
            region
        )

        params_json = json.dumps(
            params
        )

        return f"""
service_name = {service_json}
operation_name = {operation_json}
region_name = {region_json}
base_params = {params_json}

pages = []

next_token = None
marker = None
next_marker = None

page_number = 0
pagination_truncated = False


while True:

    page_number += 1

    request_params = dict(
        base_params
    )

    #
    # --------------------------------------------------
    # Common AWS pagination request tokens
    # --------------------------------------------------
    #

    if next_token:

        request_params[
            "NextToken"
        ] = next_token

    elif marker:

        request_params[
            "Marker"
        ] = marker

    #
    # --------------------------------------------------
    # Execute AWS API operation
    # --------------------------------------------------
    #

    response = await call_boto3(
        service_name=service_name,
        operation_name=operation_name,
        region_name=region_name,
        params=request_params
    )

    pages.append(
        response
    )

    #
    # --------------------------------------------------
    # Reset pagination state
    # --------------------------------------------------
    #

    next_token = None
    marker = None
    next_marker = None

    #
    # --------------------------------------------------
    # NextToken pagination
    #
    # Used by many AWS APIs:
    #
    # DescribeInstances
    # ListFunctions
    # ListClusters
    # etc.
    # --------------------------------------------------
    #

    next_token = response.get(
        "NextToken"
    )

    #
    # --------------------------------------------------
    # Marker pagination
    #
    # Used by services such as IAM and some older APIs.
    # --------------------------------------------------
    #

    if not next_token:

        next_marker = response.get(
            "NextMarker"
        )

        if next_marker:

            marker = next_marker

        elif response.get(
            "IsTruncated"
        ):

            marker = response.get(
                "Marker"
            )

        elif response.get(
            "Marker"
        ):

            marker = response.get(
                "Marker"
            )

    #
    # --------------------------------------------------
    # No more pages
    # --------------------------------------------------
    #

    if not next_token and not marker:
        break

    #
    # --------------------------------------------------
    # Safety limit
    #
    # Prevent an unexpected AWS pagination response from
    # creating an infinite MCP execution.
    # --------------------------------------------------
    #

    if page_number >= 100:

        pagination_truncated = True

        break


result = {{
    "service": service_name,
    "operation": operation_name,
    "region": region_name,
    "page_count": len(pages),
    "pagination_truncated": pagination_truncated,
    "pages": pages
}}

result
"""