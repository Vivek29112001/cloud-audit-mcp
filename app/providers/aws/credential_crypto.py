from __future__ import annotations

import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr

from app.core.config import settings
from app.providers.aws.credentials import AWSCredentials


class AWSCredentialEncryptionError(RuntimeError):
    pass


class AWSCredentialCipher:
    """Encrypt/decrypt persistent POC access-key credentials at rest."""

    def __init__(self) -> None:
        configured = (settings.aws_credential_encryption_key or "").strip()
        if configured:
            key = configured.encode("utf-8")
        else:
            if settings.app_env.lower() == "production":
                raise AWSCredentialEncryptionError(
                    "AWS_CREDENTIAL_ENCRYPTION_KEY is required in production."
                )
            # Stable development fallback only. Production must use a dedicated key.
            digest = hashlib.sha256(
                ("dhanushguard-aws-credentials:" + settings.jwt_secret_key).encode("utf-8")
            ).digest()
            key = base64.urlsafe_b64encode(digest)
        try:
            self._fernet = Fernet(key)
        except Exception as exc:
            raise AWSCredentialEncryptionError(
                "AWS_CREDENTIAL_ENCRYPTION_KEY must be a valid Fernet key."
            ) from exc

    def encrypt(self, credentials: AWSCredentials) -> str:
        payload = {
            "access_key_id": credentials.access_key_id,
            "secret_access_key": credentials.secret_access_key.get_secret_value(),
            "session_token": (
                credentials.session_token.get_secret_value()
                if credentials.session_token
                else None
            ),
            "default_region": credentials.default_region,
        }
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return self._fernet.encrypt(raw).decode("utf-8")

    def decrypt(self, ciphertext: str) -> AWSCredentials:
        try:
            raw = self._fernet.decrypt(ciphertext.encode("utf-8"))
            payload = json.loads(raw.decode("utf-8"))
        except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
            raise AWSCredentialEncryptionError(
                "Stored AWS credentials could not be decrypted."
            ) from exc
        return AWSCredentials(
            access_key_id=payload["access_key_id"],
            secret_access_key=SecretStr(payload["secret_access_key"]),
            session_token=(
                SecretStr(payload["session_token"])
                if payload.get("session_token")
                else None
            ),
            default_region=payload.get("default_region") or "us-east-1",
            source="PERSISTED_ENCRYPTED_KEYS",
        )
