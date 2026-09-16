from __future__ import annotations

from typing import Any

from mcp import (
    Client,
    StdioServerParameters,
)

from app.core.config import settings

from app.providers.aws.credentials import (
    AWSCredentials,
)


class AWSMCPClient:

    def __init__(
        self,
        credentials: AWSCredentials,
    ) -> None:

        self._credentials = credentials

    # ========================================================
    # MCP SERVER CONFIGURATION
    # ========================================================

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
            str(
                settings.mcp_timeout
            ),

            "--tool-timeout",
            str(
                settings.mcp_tool_timeout
            ),
        ]

        if settings.mcp_read_only:
            args.append(
                "--read-only"
            )

        return StdioServerParameters(
            command="uvx",
            args=args,
            env=(
                self._credentials
                .to_environment()
            ),
        )

    # ========================================================
    # TOOL DISCOVERY
    # ========================================================

    async def list_tools(
        self,
    ) -> list[Any]:

        params = (
            self._server_parameters()
        )

        async with Client(
            params
        ) as client:

            result = (
                await client.list_tools()
            )

            return list(
                result.tools
            )

    async def find_tool(
        self,
        tool_suffix: str,
    ) -> Any:

        tools = await self.list_tools()

        for tool in tools:

            if tool.name.endswith(
                tool_suffix
            ):
                return tool

        available = ", ".join(
            tool.name
            for tool in tools
        )

        raise RuntimeError(
            "AWS MCP tool ending with "
            f"'{tool_suffix}' was not found. "
            f"Available tools: {available}"
        )

    # ========================================================
    # TOOL EXECUTION
    # ========================================================

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:

        params = (
            self._server_parameters()
        )

        async with Client(
            params
        ) as client:

            return await client.call_tool(
                tool_name,
                arguments,
            )

    # ========================================================
    # AWS RUN SCRIPT
    # ========================================================

    async def run_script(
        self,
        script: str,
    ) -> Any:

        tool = await self.find_tool(
            "run_script"
        )

        # MCP SDK versions may expose this as
        # inputSchema or input_schema.
        schema = (
            getattr(
                tool,
                "inputSchema",
                None,
            )
            or getattr(
                tool,
                "input_schema",
                None,
            )
            or {}
        )

        properties = schema.get(
            "properties",
            {},
        )

        candidate_names = (
            "script",
            "code",
            "python_script",
            "source",
        )

        script_argument = next(
            (
                name
                for name
                in candidate_names
                if name in properties
            ),
            None,
        )

        if not script_argument:

            raise RuntimeError(
                "Unable to determine AWS "
                "run_script input argument. "
                f"Tool schema: {schema}"
            )

        return await self.call_tool(
            tool.name,
            {
                script_argument: script,
            },
        )

    async def execute_aws_script(
        self,
        script: str,
    ) -> Any:

        return await self.run_script(
            script
        )