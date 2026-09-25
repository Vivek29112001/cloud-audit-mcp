from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from pydantic import SecretStr

from app.core.config import settings
from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.mcp_client import AWSMCPClient
from app.providers.aws.mcp_scripts.assume_role import build_assume_role_script
from app.providers.aws.result_parser import extract_mcp_result


class AWSAssumeRoleError(RuntimeError):
    pass


class AWSAssumeRoleService:
    def source_credentials(self) -> AWSCredentials:
        if not settings.dhanush_source_aws_access_key_id:
            raise AWSAssumeRoleError(
                "DhanushGuard source AWS credentials are not configured. "
                "Set DHANUSH_SOURCE_AWS_ACCESS_KEY_ID and "
                "DHANUSH_SOURCE_AWS_SECRET_ACCESS_KEY."
            )
        if not settings.dhanush_source_aws_secret_access_key:
            raise AWSAssumeRoleError(
                "DHANUSH_SOURCE_AWS_SECRET_ACCESS_KEY is not configured."
            )
        return AWSCredentials(
            access_key_id=settings.dhanush_source_aws_access_key_id,
            secret_access_key=SecretStr(settings.dhanush_source_aws_secret_access_key),
            session_token=(
                SecretStr(settings.dhanush_source_aws_session_token)
                if settings.dhanush_source_aws_session_token
                else None
            ),
            default_region=settings.dhanush_source_aws_region,
            source="DHANUSH_SOURCE_IDENTITY",
        )

    async def assume_role(
        self,
        *,
        role_arn: str,
        external_id: str | None,
        default_region: str,
        connection_id: int | None = None,
    ) -> AWSCredentials:
        role_session_name = self._session_name(connection_id)
        script = build_assume_role_script(
            role_arn=role_arn,
            role_session_name=role_session_name,
            duration_seconds=settings.aws_sts_duration_seconds,
            external_id=external_id,
        )
        try:
            async with AWSMCPClient(self.source_credentials(), read_only=False) as mcp:
                raw = await mcp.run_aws_script(script)
        except Exception as exc:
            raise AWSAssumeRoleError(f"STS AssumeRole failed: {exc}") from exc

        payload = self._find_credentials(extract_mcp_result(raw))
        if payload is None:
            raise AWSAssumeRoleError("STS AssumeRole returned no temporary credentials.")

        access_key = str(payload.get("AccessKeyId") or "").strip()
        secret_key = str(payload.get("SecretAccessKey") or "").strip()
        token = str(payload.get("SessionToken") or "").strip()
        if not access_key or not secret_key or not token:
            raise AWSAssumeRoleError("STS AssumeRole returned incomplete credentials.")

        return AWSCredentials(
            access_key_id=access_key,
            secret_access_key=SecretStr(secret_key),
            session_token=SecretStr(token),
            default_region=default_region or "us-east-1",
            expires_at=self._parse_expiration(payload.get("Expiration")),
            source="STS_ASSUME_ROLE",
        )

    @staticmethod
    def _session_name(connection_id: int | None) -> str:
        suffix = str(connection_id or "verify")
        value = f"DhanushGuardAudit-{suffix}"
        return re.sub(r"[^A-Za-z0-9+=,.@_-]", "-", value)[:64]

    @classmethod
    def _find_credentials(cls, value: Any) -> dict[str, Any] | None:
        if isinstance(value, dict):
            if "AccessKeyId" in value and "SecretAccessKey" in value:
                return value
            for child in value.values():
                found = cls._find_credentials(child)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = cls._find_credentials(child)
                if found is not None:
                    return found
        return None

    @staticmethod
    def _parse_expiration(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        text = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
