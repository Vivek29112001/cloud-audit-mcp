from __future__ import annotations

import json
from typing import Any

from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.mcp_client import AWSMCPClient
from app.providers.aws.query.read_only_validator import (
    AWSReadOnlyOperationValidator,
)
from app.providers.aws.result_parser import extract_mcp_result

from app.providers.aws.query.result_parser import (
    find_generic_query_result,
)


# class AWSGenericQueryExecutor:
#     """
#     Generic read-only AWS query executor.

#     Important architecture rule:
#     - This application does NOT call boto3 directly.
#     - The generated Python script is sent to the official AWS Managed MCP
#       Server through AWSMCPClient.run_aws_script().
#     - call_boto3(...) therefore executes inside the AWS MCP sandbox.

#     The executor supports common AWS pagination styles and returns a stable
#     envelope so the multi-region query layer and Groq answer formatter do not
#     need to understand MCP response wrappers.
#     """

#     MAX_PAGES = 100

#     def __init__(self) -> None:
#         self._validator = AWSReadOnlyOperationValidator()

#     @property
#     def validator(self) -> AWSReadOnlyOperationValidator:
#         """Expose the read-only validator without reaching into private state."""
#         return self._validator

#     async def execute(
#         self,
#         *,
#         credentials: AWSCredentials,
#         service: str,
#         operation: str,
#         region: str,
#         params: dict[str, Any] | None = None,
#     ) -> dict[str, Any]:
#         service = service.strip().lower()
#         operation = operation.strip()
#         region = region.strip()

#         self._validator.validate(
#             service=service,
#             operation=operation,
#         )

#         safe_params = params or {}

#         script = self._build_script(
#             service=service,
#             operation=operation,
#             region=region,
#             params=safe_params,
#             max_pages=self.MAX_PAGES,
#         )

#         client = AWSMCPClient(credentials)

#         response = await client.run_aws_script(script)
#         parsed = extract_mcp_result(response)

#         query_result = self._find_query_result(parsed)

#         if not query_result:
#             raise RuntimeError(
#                 "AWS MCP returned a response, but the generic AWS query "
#                 "result could not be extracted."
#             )

#         return query_result

#     @staticmethod
#     def _find_query_result(value: Any) -> dict[str, Any] | None:
#         """
#         Find the result envelope produced by _build_script() inside an MCP
#         CallToolResult, structured-content wrapper, or nested JSON response.
#         """
#         if isinstance(value, dict):
#             if (
#                 "service" in value
#                 and "operation" in value
#                 and "region" in value
#                 and "pages" in value
#                 and "page_count" in value
#             ):
#                 return value

#             for child in value.values():
#                 found = AWSGenericQueryExecutor._find_query_result(child)
#                 if found:
#                     return found

#         elif isinstance(value, list):
#             for child in value:
#                 found = AWSGenericQueryExecutor._find_query_result(child)
#                 if found:
#                     return found

#         return None

#     @staticmethod
#     def _build_script(
#         *,
#         service: str,
#         operation: str,
#         region: str,
#         params: dict[str, Any],
#         max_pages: int,
#     ) -> str:
#         """
#         Build a Python script for execution INSIDE the official AWS MCP Server.

#         Pagination support intentionally focuses on common AWS read APIs:
#         - NextToken -> NextToken
#         - nextToken -> nextToken
#         - Marker / NextMarker -> Marker
#         - LastEvaluatedTableName -> ExclusiveStartTableName
#         - LastEvaluatedKey -> ExclusiveStartKey
#         - LastEvaluatedStreamArn -> ExclusiveStartStreamArn

#         APIs with unusual multi-field pagination can later be handled by a
#         specialized workflow without creating per-service query classes for
#         ordinary read operations.
#         """
#         return f'''
# service_name = {json.dumps(service)}
# operation_name = {json.dumps(operation)}
# region_name = {json.dumps(region)}
# base_params = {json.dumps(params)}
# max_pages = {int(max_pages)}

# pages = []
# page_number = 0
# pagination_truncated = False
# continuation = None

# # request token field -> response token field
# pagination_pairs = [
#     ("NextToken", "NextToken"),
#     ("nextToken", "nextToken"),
#     ("Marker", "Marker"),
#     ("Marker", "NextMarker"),
#     ("ExclusiveStartTableName", "LastEvaluatedTableName"),
#     ("ExclusiveStartKey", "LastEvaluatedKey"),
#     ("ExclusiveStartStreamArn", "LastEvaluatedStreamArn"),
# ]

# request_token_name = None
# request_token_value = None

# while True:
#     page_number += 1

#     request_params = dict(base_params)

#     if request_token_name and request_token_value is not None:
#         request_params[request_token_name] = request_token_value

#     response = await call_boto3(
#         service_name=service_name,
#         operation_name=operation_name,
#         region_name=region_name,
#         params=request_params,
#     )

#     pages.append(response)

#     next_request_name = None
#     next_request_value = None
#     response_token_name = None

#     for candidate_request_name, candidate_response_name in pagination_pairs:
#         candidate_value = response.get(candidate_response_name)

#         if candidate_value not in (None, "", [], {{}}):
#             next_request_name = candidate_request_name
#             next_request_value = candidate_value
#             response_token_name = candidate_response_name
#             break

#     # IAM-style APIs normally indicate whether Marker is meaningful using
#     # IsTruncated. Avoid reusing a stale Marker when the response is complete.
#     if (
#         next_request_name == "Marker"
#         and "IsTruncated" in response
#         and not response.get("IsTruncated")
#     ):
#         next_request_name = None
#         next_request_value = None
#         response_token_name = None

#     if next_request_name is None:
#         break

#     continuation = {{
#         "request_token": next_request_name,
#         "response_token": response_token_name,
#         "value": next_request_value,
#     }}

#     if page_number >= max_pages:
#         pagination_truncated = True
#         break

#     request_token_name = next_request_name
#     request_token_value = next_request_value

# result = {{
#     "service": service_name,
#     "operation": operation_name,
#     "region": region_name,
#     "page_count": len(pages),
#     "pagination_truncated": pagination_truncated,
#     "continuation": continuation if pagination_truncated else None,
#     "pages": pages,
# }}

# result
# '''


class AWSGenericQueryExecutor:

    def __init__(self) -> None:
        self._validator = (
            AWSReadOnlyOperationValidator()
        )

    # async def execute(
    #     self,
    #     *,
    #     service: str,
    #     operation: str,
    #     region: str,
    #     params: dict[str, Any] | None = None,

    #     credentials: AWSCredentials | None = None,

    #     # NEW
    #     mcp: AWSMCPClient | None = None,
    # ) -> Any:

    #     service = service.strip().lower()
    #     operation = operation.strip()

    #     self._validator.validate(
    #         service=service,
    #         operation=operation,
    #     )

    #     safe_params = params or {}

    #     #
    #     # Standalone compatibility
    #     #
    #     if mcp is None:

    #         if credentials is None:
    #             raise ValueError(
    #                 "Either credentials or an open "
    #                 "AWSMCPClient session is required."
    #             )

    #         async with AWSMCPClient(
    #             credentials
    #         ) as session:

    #             return await self.execute(
    #                 service=service,
    #                 operation=operation,
    #                 region=region,
    #                 params=safe_params,
    #                 mcp=session,
    #             )

    #     #
    #     # Reuse already-open MCP session
    #     #

    #     script = self._build_script(
    #         service=service,
    #         operation=operation,
    #         region=region,
    #         params=safe_params,
    #     )

    #     response = await mcp.run_aws_script(
    #         script
    #     )

    #     parsed = extract_mcp_result(
    #         response
    #     )

    #     query_result = (
    #         find_generic_query_result(
    #             parsed
    #         )
    #     )

    #     if not query_result:
    #         raise RuntimeError(
    #             "AWS MCP returned a response, "
    #             "but the generic query result "
    #             "could not be extracted."
    #         )

    #     return query_result
    
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

        service = (
            service
            .strip()
            .lower()
        )

        operation = (
            operation
            .strip()
        )

        self._validator.validate(
            service=service,
            operation=operation,
        )

        safe_params = (
            params or {}
        )

        #
        # Backward-compatible standalone mode
        #
        if mcp is None:

            if credentials is None:

                raise ValueError(
                    "Either credentials or "
                    "an open AWSMCPClient "
                    "session is required."
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
        # MCP SESSION ALREADY OPEN
        #

        script = self._build_script(
            service=service,
            operation=operation,
            region=region,
            params=safe_params,
        )

        response = (
            await mcp.run_aws_script(
                script
            )
        )

        parsed = extract_mcp_result(
            response
        )

        query_result = (
            find_generic_query_result(
                parsed
            )
        )

        if not query_result:

            raise RuntimeError(
                "AWS MCP returned a response, "
                "but the generic AWS query "
                "result could not be extracted."
            )

        return query_result