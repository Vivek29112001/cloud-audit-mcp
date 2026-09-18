from __future__ import annotations

from typing import Any


def find_generic_query_result(
    value: Any,
) -> dict[str, Any] | None:

    if isinstance(value, dict):

        if (
            "service" in value
            and
            "operation" in value
            and
            "pages" in value
        ):
            return value

        for child in value.values():

            found = (
                find_generic_query_result(
                    child
                )
            )

            if found:
                return found

    elif isinstance(value, list):

        for child in value:

            found = (
                find_generic_query_result(
                    child
                )
            )

            if found:
                return found

    return None