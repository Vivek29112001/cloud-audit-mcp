# from functools import lru_cache
# from pathlib import Path

# from pydantic import model_validator
# from pydantic_settings import BaseSettings, SettingsConfigDict

# BASE_DIR = Path(__file__).resolve().parent.parent.parent


# class Settings(BaseSettings):
#     app_name: str = "INAT AWS Auditor"
#     app_env: str = "development"

#     aws_mcp_endpoint: str = "https://aws-mcp.us-east-1.api.aws/mcp"
#     aws_mcp_endpoint_region: str = "us-east-1"

#     mcp_read_only: bool = True
#     mcp_timeout: int = 180
#     mcp_tool_timeout: int = 300

#     groq_api_key: str | None = None
#     groq_intent_model: str = "openai/gpt-oss-20b"

#     database_url: str = "sqlite+aiosqlite:///./data/aws_auditor.db"

#     jwt_secret_key: str
#     jwt_algorithm: str = "HS256"
#     jwt_access_token_expire_minutes: int = 1440

#     # ------------------------------------------------------------------
#     # Automatic AWS authentication
#     # ------------------------------------------------------------------
#     # Dedicated encryption key for persisted client access keys. Use a
#     # Fernet key in production. Development can derive a stable local key
#     # from JWT_SECRET_KEY when this value is absent.
#     aws_credential_encryption_key: str | None = None

#     # DhanushGuard/Cybercube source AWS identity used to assume client roles.
#     # These are SERVER credentials, not client credentials. In production,
#     # inject them through the workload secret/identity mechanism.
#     dhanush_source_aws_access_key_id: str | None = None
#     dhanush_source_aws_secret_access_key: str | None = None
#     dhanush_source_aws_session_token: str | None = None
#     dhanush_source_aws_region: str = "us-east-1"

#     # Refresh temporary STS credentials this many seconds before expiration.
#     aws_sts_refresh_skew_seconds: int = 300
#     aws_sts_duration_seconds: int = 3600

#     model_config = SettingsConfigDict(
#         env_file=".env",
#         env_file_encoding="utf-8",
#         extra="ignore",
#     )

#     @model_validator(mode="after")
#     def _resolve_sqlite_path(self) -> "Settings":
#         # Anchor relative sqlite paths to the project root so they resolve
#         # consistently regardless of the process's current working directory.
#         prefix = "sqlite+aiosqlite:///./"
#         if self.database_url.startswith(prefix):
#             relative_path = self.database_url[len(prefix):]
#             absolute_path = (BASE_DIR / relative_path).resolve()
#             absolute_path.parent.mkdir(parents=True, exist_ok=True)
#             self.database_url = f"sqlite+aiosqlite:///{absolute_path.as_posix()}"
#         return self


# @lru_cache
# def get_settings() -> Settings:
#     return Settings()


# settings = get_settings()




from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "INAT AWS Auditor"
    app_env: str = "development"

    aws_mcp_endpoint: str = "https://aws-mcp.us-east-1.api.aws/mcp"
    aws_mcp_endpoint_region: str = "us-east-1"
    # AWS recommends the version-pinned CLI distribution for uvx/stdio use.
    aws_mcp_proxy_package: str = "mcp-proxy-for-aws-cli@1.7.0"

    # May be kept true. AWSMCPClient automatically retries without the proxy
    # tool filter when run_script is filtered out. IAM + operation validation
    # remain the real read-only security boundary for audit queries.
    mcp_read_only: bool = True
    mcp_timeout: int = 180
    mcp_tool_timeout: int = 300

    groq_api_key: str | None = None
    groq_intent_model: str = "openai/gpt-oss-20b"

    database_url: str = "sqlite+aiosqlite:///./data/aws_auditor.db"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440

    # ------------------------------------------------------------------
    # Automatic AWS authentication
    # ------------------------------------------------------------------
    # Dedicated encryption key for persisted client access keys. Use a
    # Fernet key in production. Development can derive a stable local key
    # from JWT_SECRET_KEY when this value is absent.
    aws_credential_encryption_key: str | None = None

    # DhanushGuard/Cybercube source AWS identity used to assume client roles.
    # These are SERVER credentials, not client credentials. In production,
    # inject them through the workload secret/identity mechanism.
    dhanush_source_aws_access_key_id: str | None = None
    dhanush_source_aws_secret_access_key: str | None = None
    dhanush_source_aws_session_token: str | None = None
    dhanush_source_aws_region: str = "us-east-1"

    # Refresh temporary STS credentials this many seconds before expiration.
    aws_sts_refresh_skew_seconds: int = 300
    aws_sts_duration_seconds: int = 3600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
