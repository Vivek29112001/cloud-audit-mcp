# from __future__ import annotations

# from typing import Any

# from mcp import Client, StdioServerParameters

# from app.core.config import settings
# from app.providers.aws.credentials import AWSCredentials


# class AWSMCPClient:
#     """
#     The ONLY gateway between our application and AWS.

#     No application service/collector should use:
#         - boto3
#         - AWS CLI
#         - direct AWS REST calls

#     All AWS operations are executed through the
#     official AWS Managed MCP Server.

#     The client supports two execution modes:

#     1. Reusable session:
#        async with AWSMCPClient(credentials) as mcp:
#            await mcp.run_aws_script(...)

#        This is preferred for discovery because the proxy/MCP
#        connection and run_script tool discovery happen only once.

#     2. One-shot compatibility mode:
#        client = AWSMCPClient(credentials)
#        await client.run_aws_script(...)

#        This keeps existing on-demand/query code working.
#     """

#     def __init__(
#         self,
#         credentials: AWSCredentials,
#         *,
#         read_only: bool | None = None,
#     ) -> None:
#         self._credentials = credentials
#         self._read_only = settings.mcp_read_only if read_only is None else read_only
#         self._client: Client | None = None
#         self._run_script_tool_name: str | None = None
#         self._run_script_field: str | None = None

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
#             str(settings.mcp_timeout),
#             "--tool-timeout",
#             str(settings.mcp_tool_timeout),
#         ]

#         if self._read_only:
#             args.append("--read-only")

#         return StdioServerParameters(
#             command="uvx",
#             args=args,
#             env=self._credentials.to_environment(),
#         )

#     @property
#     def is_open(self) -> bool:
#         return self._client is not None

#     async def __aenter__(
#         self,
#     ) -> "AWSMCPClient":
#         if self._client is not None:
#             return self

#         params = self._server_parameters()
#         client = Client(params)

#         try:
#             await client.__aenter__()
#             self._client = client
#             await self._resolve_run_script_tool()
#             return self

#         except Exception:
#             try:
#                 await client.__aexit__(
#                     None,
#                     None,
#                     None,
#                 )
#             except Exception:
#                 pass

#             self._client = None
#             self._run_script_tool_name = None
#             self._run_script_field = None
#             raise

#     async def __aexit__(
#         self,
#         exc_type,
#         exc,
#         tb,
#     ) -> None:
#         client = self._client

#         self._client = None
#         self._run_script_tool_name = None
#         self._run_script_field = None

#         if client is not None:
#             await client.__aexit__(
#                 exc_type,
#                 exc,
#                 tb,
#             )

#     async def _resolve_run_script_tool(
#         self,
#     ) -> None:
#         if self._client is None:
#             raise RuntimeError(
#                 "AWS MCP session is not open."
#             )

#         tools_result = await self._client.list_tools()

#         run_script_tool = next(
#             (
#                 tool
#                 for tool in tools_result.tools
#                 if tool.name.endswith(
#                     "run_script"
#                 )
#             ),
#             None,
#         )

#         if not run_script_tool:
#             available = [
#                 tool.name
#                 for tool in tools_result.tools
#             ]

#             raise RuntimeError(
#                 "Official AWS MCP Server does not expose "
#                 f"run_script. Available tools: {available}"
#             )

#         schema = (
#             run_script_tool.input_schema
#             or {}
#         )

#         properties = schema.get(
#             "properties",
#             {},
#         )

#         script_field = next(
#             (
#                 name
#                 for name in (
#                     "script",
#                     "code",
#                     "python_script",
#                     "source",
#                 )
#                 if name in properties
#             ),
#             None,
#         )

#         if not script_field:
#             raise RuntimeError(
#                 "Unable to determine run_script input field."
#             )

#         self._run_script_tool_name = (
#             run_script_tool.name
#         )
#         self._run_script_field = (
#             script_field
#         )

#     async def list_tools(
#         self,
#     ) -> list[Any]:
#         if self._client is not None:
#             result = await self._client.list_tools()
#             return list(result.tools)

#         async with self:
#             if self._client is None:
#                 raise RuntimeError(
#                     "AWS MCP session could not be opened."
#                 )

#             result = await self._client.list_tools()
#             return list(result.tools)

#     async def _find_tool(
#         self,
#         suffix: str,
#     ) -> Any:
#         tools = await self.list_tools()

#         for tool in tools:
#             if tool.name.endswith(suffix):
#                 return tool

#         available = [
#             tool.name
#             for tool in tools
#         ]

#         raise RuntimeError(
#             f"AWS MCP tool '{suffix}' "
#             f"was not found. "
#             f"Available tools: {available}"
#         )

#     async def run_aws_script(
#         self,
#         script: str,
#     ) -> Any:
#         """
#         Execute Python inside the OFFICIAL AWS MCP Server.

#         The supplied script is NOT executed locally.

#         When the client is already inside an async context,
#         the existing MCP session is reused. Otherwise a short-lived
#         one-shot session is opened for backward compatibility.
#         """

#         if self._client is None:
#             async with self:
#                 return await self.run_aws_script(
#                     script
#                 )

#         if (
#             not self._run_script_tool_name
#             or not self._run_script_field
#         ):
#             await self._resolve_run_script_tool()

#         return await self._client.call_tool(
#             self._run_script_tool_name,
#             {
#                 self._run_script_field: script,
#             },
#         )



from __future__ import annotations

import logging
from typing import Any

from mcp import Client, StdioServerParameters

from app.core.config import settings
from app.providers.aws.credentials import AWSCredentials


logger = logging.getLogger(__name__)


class AWSMCPRunScriptUnavailableError(RuntimeError):
    """Managed AWS MCP did not expose the run_script tool."""


class AWSMCPClient:
    """
    Gateway between DhanushGuard and the AWS Managed MCP Server.

    Important:
    The application uses the managed server's ``run_script`` tool for identity,
    discovery, billing and live read-only queries. The proxy's ``--read-only``
    flag filters tools based on MCP ``readOnlyHint`` metadata and can therefore
    hide ``run_script`` entirely. This client automatically retries WITHOUT the
    proxy tool filter when that happens.

    Safety for user-driven live queries remains enforced by:
      * AWSReadOnlyOperationValidator
      * the audit IAM policy / cross-account role policy
      * controlled server-side scripts

    ``read_only`` therefore means "try the proxy read-only tool filter first";
    it is not the application's primary authorization boundary.
    """

    def __init__(
        self,
        credentials: AWSCredentials,
        *,
        read_only: bool | None = None,
    ) -> None:
        self._credentials = credentials
        self._requested_read_only = (
            settings.mcp_read_only if read_only is None else read_only
        )
        self._effective_read_only = self._requested_read_only
        self._client: Client | None = None
        self._run_script_tool_name: str | None = None
        self._run_script_field: str | None = None

    def _server_parameters(
        self,
        *,
        read_only: bool | None = None,
    ) -> StdioServerParameters:
        effective_read_only = (
            self._requested_read_only if read_only is None else read_only
        )

        args = [
            settings.aws_mcp_proxy_package,
            settings.aws_mcp_endpoint,
            "--region",
            settings.aws_mcp_endpoint_region,
            "--metadata",
            f"AWS_REGION={self._credentials.default_region}",
            "--retries",
            "2",
            "--timeout",
            str(settings.mcp_timeout),
            "--tool-timeout",
            str(settings.mcp_tool_timeout),
        ]

        if effective_read_only:
            args.append("--read-only")

        return StdioServerParameters(
            command="uvx",
            args=args,
            env=self._credentials.to_environment(),
        )

    @property
    def is_open(self) -> bool:
        return self._client is not None

    @property
    def effective_read_only(self) -> bool:
        return self._effective_read_only

    async def __aenter__(self) -> "AWSMCPClient":
        if self._client is not None:
            return self

        # First honor the configured proxy mode. If run_script is filtered by
        # --read-only, transparently reconnect without that TOOL FILTER. This
        # does not grant AWS permissions; IAM still decides what APIs can run.
        try:
            await self._open(read_only=self._requested_read_only)
            return self
        except AWSMCPRunScriptUnavailableError:
            if not self._requested_read_only:
                raise

            logger.warning(
                "AWS MCP run_script is unavailable with proxy --read-only; "
                "retrying without the proxy tool filter. AWS IAM and the "
                "application read-only validator remain the security boundary."
            )
            await self._close(None, None, None)
            await self._open(read_only=False)
            return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._close(exc_type, exc, tb)

    async def _open(self, *, read_only: bool) -> None:
        params = self._server_parameters(read_only=read_only)
        client = Client(params)

        try:
            await client.__aenter__()
            self._client = client
            self._effective_read_only = read_only
            await self._resolve_run_script_tool()
        except Exception:
            try:
                await client.__aexit__(None, None, None)
            except Exception:
                pass
            self._client = None
            self._run_script_tool_name = None
            self._run_script_field = None
            raise

    async def _close(self, exc_type, exc, tb) -> None:
        client = self._client
        self._client = None
        self._run_script_tool_name = None
        self._run_script_field = None

        if client is not None:
            await client.__aexit__(exc_type, exc, tb)

    async def _resolve_run_script_tool(self) -> None:
        if self._client is None:
            raise RuntimeError("AWS MCP session is not open.")

        tools_result = await self._client.list_tools()
        run_script_tool = next(
            (tool for tool in tools_result.tools if tool.name.endswith("run_script")),
            None,
        )

        if not run_script_tool:
            available = [tool.name for tool in tools_result.tools]
            mode = "with --read-only" if self._effective_read_only else "without --read-only"
            raise AWSMCPRunScriptUnavailableError(
                "AWS Managed MCP Server does not expose run_script "
                f"{mode}. Available tools: {available}"
            )

        schema = run_script_tool.input_schema or {}
        properties = schema.get("properties", {})
        script_field = next(
            (
                name
                for name in ("script", "code", "python_script", "source")
                if name in properties
            ),
            None,
        )

        if not script_field:
            raise RuntimeError("Unable to determine run_script input field.")

        self._run_script_tool_name = run_script_tool.name
        self._run_script_field = script_field

    async def list_tools(self) -> list[Any]:
        if self._client is not None:
            result = await self._client.list_tools()
            return list(result.tools)

        async with self:
            if self._client is None:
                raise RuntimeError("AWS MCP session could not be opened.")
            result = await self._client.list_tools()
            return list(result.tools)

    async def _find_tool(self, suffix: str) -> Any:
        tools = await self.list_tools()
        for tool in tools:
            if tool.name.endswith(suffix):
                return tool

        available = [tool.name for tool in tools]
        raise RuntimeError(
            f"AWS MCP tool '{suffix}' was not found. Available tools: {available}"
        )

    async def run_aws_script(self, script: str) -> Any:
        """Execute Python inside the AWS Managed MCP Server sandbox."""
        if self._client is None:
            async with self:
                return await self.run_aws_script(script)

        if not self._run_script_tool_name or not self._run_script_field:
            await self._resolve_run_script_tool()

        return await self._client.call_tool(
            self._run_script_tool_name,
            {self._run_script_field: script},
        )
