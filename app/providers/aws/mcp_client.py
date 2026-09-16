# from __future__ import annotations

# from typing import Any

# from mcp import (
#     Client,
#     StdioServerParameters,
# )

# from app.core.config import settings

# from app.providers.aws.credentials import (
#     AWSCredentials,
# )


# class AWSMCPClient:

#     def __init__(
#         self,
#         credentials: AWSCredentials,
#     ) -> None:

#         self._credentials = credentials

#     # ========================================================
#     # MCP SERVER CONFIGURATION
#     # ========================================================

#     def _server_parameters(
#         self,
#     ) -> StdioServerParameters:

#         args = [
#             "mcp-proxy-for-aws@1.6.3",

#             settings.aws_mcp_endpoint,

#             "--region",
#             settings.aws_mcp_endpoint_region,

#             "--metadata",
#             (
#                 "AWS_REGION="
#                 f"{self._credentials.default_region}"
#             ),

#             "--retries",
#             "2",

#             "--timeout",
#             str(
#                 settings.mcp_timeout
#             ),

#             "--tool-timeout",
#             str(
#                 settings.mcp_tool_timeout
#             ),
#         ]

#         if settings.mcp_read_only:
#             args.append(
#                 "--read-only"
#             )

#         return StdioServerParameters(
#             command="uvx",
#             args=args,
#             env=(
#                 self._credentials
#                 .to_environment()
#             ),
#         )

#     # ========================================================
#     # TOOL DISCOVERY
#     # ========================================================

#     async def list_tools(
#         self,
#     ) -> list[Any]:

#         params = (
#             self._server_parameters()
#         )

#         async with Client(
#             params
#         ) as client:

#             result = (
#                 await client.list_tools()
#             )

#             return list(
#                 result.tools
#             )

#     async def find_tool(
#         self,
#         tool_suffix: str,
#     ) -> Any:

#         tools = await self.list_tools()

#         for tool in tools:

#             if tool.name.endswith(
#                 tool_suffix
#             ):
#                 return tool

#         available = ", ".join(
#             tool.name
#             for tool in tools
#         )

#         raise RuntimeError(
#             "AWS MCP tool ending with "
#             f"'{tool_suffix}' was not found. "
#             f"Available tools: {available}"
#         )

#     # ========================================================
#     # TOOL EXECUTION
#     # ========================================================

#     async def call_tool(
#         self,
#         tool_name: str,
#         arguments: dict[str, Any],
#     ) -> Any:

#         params = (
#             self._server_parameters()
#         )

#         async with Client(
#             params
#         ) as client:

#             return await client.call_tool(
#                 tool_name,
#                 arguments,
#             )

#     # ========================================================
#     # AWS RUN SCRIPT
#     # ========================================================

#     async def run_script(
#         self,
#         script: str,
#     ) -> Any:

#         tool = await self.find_tool(
#             "run_script"
#         )

#         # MCP SDK versions may expose this as
#         # inputSchema or input_schema.
#         schema = (
#             getattr(
#                 tool,
#                 "inputSchema",
#                 None,
#             )
#             or getattr(
#                 tool,
#                 "input_schema",
#                 None,
#             )
#             or {}
#         )

#         properties = schema.get(
#             "properties",
#             {},
#         )

#         candidate_names = (
#             "script",
#             "code",
#             "python_script",
#             "source",
#         )

#         script_argument = next(
#             (
#                 name
#                 for name
#                 in candidate_names
#                 if name in properties
#             ),
#             None,
#         )

#         if not script_argument:

#             raise RuntimeError(
#                 "Unable to determine AWS "
#                 "run_script input argument. "
#                 f"Tool schema: {schema}"
#             )

#         return await self.call_tool(
#             tool.name,
#             {
#                 script_argument: script,
#             },
#         )

#     async def execute_aws_script(
#         self,
#         script: str,
#     ) -> Any:

#         return await self.run_script(
#             script
#         )


from __future__ import annotations

from typing import Any

from mcp import Client, StdioServerParameters

from app.core.config import settings
from app.providers.aws.credentials import AWSCredentials


class AWSMCPClient:
    """
    The ONLY gateway between our application and AWS.

    No application service/collector should use:
        - boto3
        - AWS CLI
        - direct AWS REST calls

    All AWS operations are executed through the
    official AWS Managed MCP Server.
    """

    def __init__(
        self,
        credentials: AWSCredentials,
    ) -> None:
        self._credentials = credentials

    def _server_parameters(
        self,
    ) -> StdioServerParameters:

        args = [
            "mcp-proxy-for-aws@1.6.3",
            settings.aws_mcp_endpoint,
            "--region",
            settings.aws_mcp_endpoint_region,
            "--metadata",
            (
                "AWS_REGION="
                f"{self._credentials.default_region}"
            ),
            "--retries",
            "2",
            "--timeout",
            str(settings.mcp_timeout),
            "--tool-timeout",
            str(settings.mcp_tool_timeout),
        ]

        if settings.mcp_read_only:
            args.append("--read-only")

        return StdioServerParameters(
            command="uvx",
            args=args,
            env=self._credentials.to_environment(),
        )

    async def list_tools(
        self,
    ) -> list[Any]:

        params = self._server_parameters()

        async with Client(params) as client:
            result = await client.list_tools()
            return list(result.tools)

    async def _find_tool(
        self,
        suffix: str,
    ) -> Any:

        tools = await self.list_tools()

        for tool in tools:
            if tool.name.endswith(suffix):
                return tool

        available = [
            tool.name
            for tool in tools
        ]

        raise RuntimeError(
            f"AWS MCP tool '{suffix}' "
            f"was not found. "
            f"Available tools: {available}"
        )

    async def run_aws_script(
        self,
        script: str,
    ) -> Any:
        """
        Execute Python inside the OFFICIAL AWS MCP Server.

        The supplied script is NOT executed locally.
        """

        params = self._server_parameters()

        async with Client(params) as client:

            tools = await client.list_tools()

            run_script_tool = next(
                (
                    tool
                    for tool in tools.tools
                    if tool.name.endswith(
                        "run_script"
                    )
                ),
                None,
            )

            if not run_script_tool:
                raise RuntimeError(
                    "Official AWS MCP Server "
                    "does not expose run_script."
                )

            schema = (
                run_script_tool
                .input_schema
                or {}
            )

            properties = schema.get(
                "properties",
                {},
            )

            script_field = next(
                (
                    name
                    for name in (
                        "script",
                        "code",
                        "python_script",
                        "source",
                    )
                    if name in properties
                ),
                None,
            )

            if not script_field:
                raise RuntimeError(
                    "Unable to determine "
                    "run_script input field."
                )

            return await client.call_tool(
                run_script_tool.name,
                {
                    script_field: script,
                },
            )
