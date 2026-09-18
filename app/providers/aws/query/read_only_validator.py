from __future__ import annotations

import re


class UnsafeAWSOperationError(
    ValueError
):
    pass


class AWSReadOnlyOperationValidator:

    ALLOWED_PREFIXES = (
        "Get",
        "List",
        "Describe",
        "Search",
        "Lookup",
        "BatchGet",
        "Select",
    )

    BLOCKED_PREFIXES = (
        "Create",
        "Delete",
        "Put",
        "Update",
        "Modify",
        "Terminate",
        "Stop",
        "Start",
        "Reboot",
        "Run",
        "Invoke",
        "Attach",
        "Detach",
        "Associate",
        "Disassociate",
        "Enable",
        "Disable",
        "Register",
        "Deregister",
        "Set",
        "Tag",
        "Untag",
        "Restore",
        "Copy",
        "Import",
        "Export",
        "Send",
        "Publish",
    )

    OPERATION_PATTERN = re.compile(
        r"^[A-Za-z][A-Za-z0-9]+$"
    )

    SERVICE_PATTERN = re.compile(
        r"^[a-z0-9-]+$"
    )

    def validate(
        self,
        service: str,
        operation: str,
    ) -> None:

        if not self.SERVICE_PATTERN.fullmatch(
            service
        ):
            raise UnsafeAWSOperationError(
                f"Invalid AWS service: {service}"
            )

        if not self.OPERATION_PATTERN.fullmatch(
            operation
        ):
            raise UnsafeAWSOperationError(
                f"Invalid AWS operation: "
                f"{operation}"
            )

        if operation.startswith(
            self.BLOCKED_PREFIXES
        ):
            raise UnsafeAWSOperationError(
                f"AWS operation "
                f"{operation} is not permitted."
            )

        if not operation.startswith(
            self.ALLOWED_PREFIXES
        ):
            raise UnsafeAWSOperationError(
                f"AWS operation "
                f"{operation} is not an "
                f"approved read-only operation."
            )