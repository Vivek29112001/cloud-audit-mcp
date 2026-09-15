from __future__ import annotations

import json
from typing import Any


def extract_mcp_result(result: Any) -> Any:
    """
    Extract useful structured data from an MCP CallToolResult.

    Supports:
    - structured_content
    - text content containing JSON
    - raw model dictionaries
    """

    structured = getattr(
        result,
        "structured_content",
        None,
    )

    if structured:
        return structured

    content = getattr(
        result,
        "content",
        None,
    )

    if not content:
        return result

    text_values: list[str] = []

    for item in content:
        text = getattr(item, "text", None)

        if text:
            text_values.append(text)

    if not text_values:
        return result

    text = "\n".join(text_values)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def find_dict_with_keys(
    value: Any,
    required_keys: set[str],
) -> dict[str, Any] | None:
    """
    Recursively searches the MCP response for a dictionary
    containing all required keys.
    """

    if isinstance(value, dict):
        if required_keys.issubset(value.keys()):
            return value

        for child in value.values():
            found = find_dict_with_keys(
                child,
                required_keys,
            )

            if found:
                return found

    elif isinstance(value, list):
        for child in value:
            found = find_dict_with_keys(
                child,
                required_keys,
            )

            if found:
                return found

    return None