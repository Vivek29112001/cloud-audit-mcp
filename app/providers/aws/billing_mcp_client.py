from __future__ import annotations

import json
import platform
from typing import Any

from mcp import Client, StdioServerParameters

from app.core.config import settings
from app.providers.aws.credentials import AWSCredentials


class AWSBillingMCPClient:
    """Direct client for the AWS Labs Billing and Cost Management MCP Server."""

    def __init__(self, credentials: AWSCredentials) -> None:
        self._credentials = credentials
        self._client: Client | None = None
        self._tool_name: str | None = None
        self._tool_schema: dict[str, Any] = {}

    def _server_parameters(self) -> StdioServerParameters:
        env = self._credentials.to_environment()
        env["AWS_REGION"] = settings.aws_billing_mcp_region
        env["AWS_DEFAULT_REGION"] = settings.aws_billing_mcp_region
        env["FASTMCP_LOG_LEVEL"] = "ERROR"

        package = settings.aws_billing_mcp_package
        if platform.system().lower().startswith("win"):
            args = [
                "--from",
                package,
                "awslabs.billing-cost-management-mcp-server.exe",
            ]
        else:
            args = [package]

        return StdioServerParameters(command="uvx", args=args, env=env)

    async def __aenter__(self) -> "AWSBillingMCPClient":
        if self._client is not None:
            return self

        client = Client(self._server_parameters())
        try:
            await client.__aenter__()
            self._client = client
            await self._resolve_cost_tool()
            return self
        except BaseException as exc:
            # MCP stdio uses AnyIO task groups. Cleanup can itself raise an
            # ExceptionGroup and hide the original startup/list_tools error.
            cleanup_error: BaseException | None = None
            try:
                await client.__aexit__(type(exc), exc, exc.__traceback__)
            except BaseException as cleanup_exc:
                cleanup_error = cleanup_exc
            self._reset()
            message = self.format_exception(exc)
            if cleanup_error is not None:
                message += f" | MCP cleanup: {self.format_exception(cleanup_error)}"
            raise RuntimeError(f"Billing MCP connection failed: {message}") from exc

    async def __aexit__(self, exc_type, exc, tb) -> None:
        client = self._client
        self._reset()
        if client is None:
            return
        try:
            await client.__aexit__(exc_type, exc, tb)
        except BaseException as close_exc:
            # If a business/tool exception is already in flight, do not replace
            # it with the generic TaskGroup shutdown exception.
            if exc is not None:
                return
            raise RuntimeError(
                f"Billing MCP shutdown failed: {self.format_exception(close_exc)}"
            ) from close_exc

    def _reset(self) -> None:
        self._client = None
        self._tool_name = None
        self._tool_schema = {}

    async def _resolve_cost_tool(self) -> None:
        if self._client is None:
            raise RuntimeError("Billing MCP session is not open.")

        result = await self._client.list_tools()
        tools = list(result.tools)

        # Current Billing & Cost Management MCP exposes a cost-explorer wrapper.
        # Also accept a direct get_cost_and_usage tool so this client survives
        # server schema changes without a static server-version dependency.
        direct = next(
            (t for t in tools if t.name.replace("-", "_").endswith("get_cost_and_usage")),
            None,
        )
        wrapper = next(
            (
                t
                for t in tools
                if t.name == "cost-explorer"
                or t.name.endswith("cost-explorer")
                or t.name.endswith("cost_explorer")
            ),
            None,
        )
        tool = direct or wrapper
        if tool is None:
            available = [t.name for t in tools]
            raise RuntimeError(
                "AWS Billing MCP exposes neither cost-explorer nor "
                f"get_cost_and_usage. Available tools: {available}"
            )

        self._tool_name = tool.name
        self._tool_schema = (
            getattr(tool, "input_schema", None)
            or getattr(tool, "inputSchema", None)
            or {}
        )

    async def get_cost_and_usage(
        self,
        *,
        start_date: str,
        end_date: str,
        group_by: list[dict[str, str]],
        granularity: str = "MONTHLY",
        metrics: list[str] | None = None,
        max_pages: int = 100,
    ) -> Any:
        if self._client is None:
            raise RuntimeError("Billing MCP session is not open.")
        if self._tool_name is None:
            await self._resolve_cost_tool()

        # Direct get_cost_and_usage tools do not need an operation selector.
        # Wrapper-style cost-explorer tools do. Some server releases expose the
        # selector without an enum and use a different naming convention.
        # Resolve it from the runtime schema when possible; otherwise retry only
        # naming variants of the same documented operation when the wrapper
        # explicitly reports "Unknown operation".
        operation_candidates = self._operation_candidates()

        last_unknown_operation: str | None = None
        for operation in operation_candidates:
            arguments = self._build_arguments(
                start_date=start_date,
                end_date=end_date,
                group_by=group_by,
                granularity=granularity,
                metrics=metrics or ["UnblendedCost"],
                max_pages=max_pages,
                operation=operation,
            )

            try:
                result = await self._client.call_tool(self._tool_name, arguments)
            except BaseException as exc:
                raise RuntimeError(
                    f"Billing MCP tool '{self._tool_name}' failed: "
                    f"{self.format_exception(exc)}"
                ) from exc

            result_text = self._result_text(result)
            is_error = bool(
                getattr(result, "is_error", False)
                or getattr(result, "isError", False)
            )

            # A number of MCP wrappers return an error payload as successful
            # MCP content instead of setting isError=true, so inspect the
            # returned text as well.
            if self._is_unknown_operation(result_text):
                last_unknown_operation = result_text
                continue

            if is_error:
                raise RuntimeError(
                    f"Billing MCP tool '{self._tool_name}' returned an error: "
                    f"{result_text}"
                )

            return result

        raise RuntimeError(
            f"Billing MCP tool '{self._tool_name}' rejected all runtime-compatible "
            f"GetCostAndUsage operation names. Last response: "
            f"{last_unknown_operation or 'Unknown operation'}"
        )

    def _build_arguments(
        self,
        *,
        start_date: str,
        end_date: str,
        group_by: list[dict[str, str]],
        granularity: str,
        metrics: list[str],
        max_pages: int,
        operation: str | None = None,
    ) -> dict[str, Any]:
        properties = self._tool_schema.get("properties", {}) if isinstance(self._tool_schema, dict) else {}
        name = (self._tool_name or "").replace("-", "_")

        # Wrapper tool contract used by billing-cost-management-mcp-server.
        if "operation" in properties or "cost_explorer" in name:
            selected_operation = (
                operation
                or self._operation_value(properties.get("operation", {}))
            )
            args: dict[str, Any] = {
                "operation": selected_operation,
                "start_date": start_date,
                "end_date": end_date,
                "granularity": granularity,
                "metrics": metrics,
                "group_by": group_by,
            }
            if "max_pages" in properties:
                args["max_pages"] = max_pages
            return self._only_supported(args, properties)

        # Direct-tool compatibility. Some MCP implementations expose a nested
        # date_range object rather than start_date/end_date at top level.
        args = {}
        if "date_range" in properties:
            args["date_range"] = {"start_date": start_date, "end_date": end_date}
        else:
            args["start_date"] = start_date
            args["end_date"] = end_date
        args.update(
            granularity=granularity,
            metrics=metrics,
            group_by=group_by,
        )
        if "max_pages" in properties:
            args["max_pages"] = max_pages
        return self._only_supported(args, properties)

    def _operation_candidates(self) -> list[str | None]:
        properties = (
            self._tool_schema.get("properties", {})
            if isinstance(self._tool_schema, dict)
            else {}
        )
        name = (self._tool_name or "").replace("-", "_")

        # A direct tool already represents the operation.
        if "operation" not in properties and "cost_explorer" not in name:
            return [None]

        schema = properties.get("operation", {})
        enum = schema.get("enum") if isinstance(schema, dict) else None

        # Best case: use exactly what the running MCP server advertises.
        if isinstance(enum, list) and enum:
            normalized_targets = {
                "getcostandusage",
            }
            matching: list[str] = []
            for value in enum:
                if not isinstance(value, str):
                    continue
                normalized = "".join(ch for ch in value.lower() if ch.isalnum())
                if normalized in normalized_targets:
                    matching.append(value)
            if matching:
                return matching

        # Compatibility fallback for wrapper releases that expose operation as
        # a plain string without publishing an enum. These are naming variants
        # of one operation, not a static AWS service catalogue.
        return [
            "get_cost_and_usage",
            "get-cost-and-usage",
            "getCostAndUsage",
            "GetCostAndUsage",
        ]

    @staticmethod
    def _is_unknown_operation(text: str) -> bool:
        lowered = (text or "").lower()
        return (
            "unknown operation" in lowered
            or "unsupported operation" in lowered
            or "invalid operation" in lowered
        )

    @staticmethod
    def _operation_value(schema: Any) -> str:
        # Prefer the current documented snake_case operation. If the running
        # server publishes an enum containing only camelCase, honor its schema.
        if isinstance(schema, dict):
            enum = schema.get("enum")
            if isinstance(enum, list):
                if "get_cost_and_usage" in enum:
                    return "get_cost_and_usage"
                if "getCostAndUsage" in enum:
                    return "getCostAndUsage"
        return "get_cost_and_usage"

    @classmethod
    def _only_supported(
        cls,
        args: dict[str, Any],
        properties: Any,
    ) -> dict[str, Any]:
        if not isinstance(properties, dict) or not properties:
            return args

        supported: dict[str, Any] = {}
        for key, value in args.items():
            if key not in properties:
                continue
            supported[key] = cls._coerce_for_schema(
                value=value,
                schema=properties.get(key),
            )
        return supported

    @classmethod
    def _coerce_for_schema(cls, *, value: Any, schema: Any) -> Any:
        """
        Convert a Python value to the type advertised by the running MCP tool.

        The AWS Billing MCP cost-explorer wrapper currently advertises fields
        such as metrics and group_by as strings even though their logical
        values are lists. In that case we serialize structured values as JSON.

        This remains schema-driven: if another server/version advertises those
        fields as arrays, the original list is sent unchanged.
        """
        if not isinstance(schema, dict):
            return value

        schema_type = schema.get("type")

        # JSON Schema can publish multiple accepted types.
        if isinstance(schema_type, list):
            non_null_types = [item for item in schema_type if item != "null"]
            if len(non_null_types) == 1:
                schema_type = non_null_types[0]

        if schema_type == "string":
            if isinstance(value, str):
                return value
            if isinstance(value, (list, dict)):
                return json.dumps(value, separators=(",", ":"))
            if value is None:
                return value
            return str(value)

        if schema_type == "array":
            if isinstance(value, list):
                return value
            return [value]

        if schema_type == "object":
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, dict):
                        return parsed
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass
            return value

        if schema_type == "integer":
            if isinstance(value, bool):
                return int(value)
            try:
                return int(value)
            except (TypeError, ValueError):
                return value

        if schema_type == "number":
            try:
                return float(value)
            except (TypeError, ValueError):
                return value

        if schema_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized in {"true", "1", "yes"}:
                    return True
                if normalized in {"false", "0", "no"}:
                    return False
            return value

        # Handle schemas expressed through anyOf/oneOf.
        for keyword in ("anyOf", "oneOf"):
            variants = schema.get(keyword)
            if isinstance(variants, list):
                for variant in variants:
                    if not isinstance(variant, dict):
                        continue
                    variant_type = variant.get("type")
                    if variant_type and variant_type != "null":
                        return cls._coerce_for_schema(
                            value=value,
                            schema=variant,
                        )

        return value

    @classmethod
    def format_exception(cls, exc: BaseException) -> str:
        parts: list[str] = []

        def walk(error: BaseException, depth: int = 0) -> None:
            label = type(error).__name__
            message = str(error).strip()
            parts.append(f"{'  ' * depth}{label}: {message or '<no message>'}")
            children = getattr(error, "exceptions", None)
            if children:
                for child in children:
                    if isinstance(child, BaseException):
                        walk(child, depth + 1)
            cause = getattr(error, "__cause__", None)
            if cause is not None and cause is not error and not children:
                walk(cause, depth + 1)

        walk(exc)
        return " | ".join(parts)

    @staticmethod
    def _result_text(result: Any) -> str:
        values: list[str] = []
        for item in getattr(result, "content", None) or []:
            text = getattr(item, "text", None)
            if text:
                values.append(str(text))
        structured = getattr(result, "structured_content", None)
        if structured:
            try:
                values.append(json.dumps(structured, default=str))
            except Exception:
                values.append(str(structured))
        return "\n".join(values).strip() or repr(result)
