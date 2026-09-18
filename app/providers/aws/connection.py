from __future__ import annotations

import logging

from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.exceptions import (
    AWSMCPExecutionError,
    InvalidAWSCredentialsError,
)
from app.providers.aws.mcp_client import AWSMCPClient
from app.providers.aws.models import AWSIdentity
from app.providers.aws.result_parser import (
    extract_mcp_result,
    find_dict_with_keys,
)
from app.providers.aws.mcp_scripts.identity import (
    build_identity_script,
)


logger = logging.getLogger(__name__)


class AWSConnectionService:

    async def verify_credentials(
        self,
        credentials: AWSCredentials | None = None,
        *,
        mcp: AWSMCPClient | None = None,
    ) -> AWSIdentity:
        """
        Verify AWS identity through the official AWS MCP Server.

        Preferred discovery usage:
            verify_credentials(mcp=existing_session)

        Existing standalone usage is still supported:
            verify_credentials(credentials)
        """

        if mcp is None:
            if credentials is None:
                raise ValueError(
                    "Either credentials or an open AWSMCPClient "
                    "session is required."
                )

            async with AWSMCPClient(
                credentials
            ) as session:
                return await self.verify_credentials(
                    mcp=session
                )

        script = build_identity_script()

        try:
            response = await mcp.run_aws_script(
                script
            )

        except Exception as exc:
            logger.exception(
                "AWS MCP verification failed"
            )

            message = str(exc)

            credential_errors = (
                "InvalidClientTokenId",
                "UnrecognizedClientException",
                "SignatureDoesNotMatch",
                "InvalidSignatureException",
                "ExpiredToken",
            )

            if any(
                error in message
                for error in credential_errors
            ):
                raise InvalidAWSCredentialsError(
                    "AWS rejected the provided credentials."
                ) from exc

            raise AWSMCPExecutionError(
                f"AWS MCP execution failed: {message}"
            ) from exc

        parsed = extract_mcp_result(
            response
        )

        identity = find_dict_with_keys(
            parsed,
            {
                "Account",
                "Arn",
                "UserId",
            },
        )

        if not identity:
            raise AWSMCPExecutionError(
                "AWS MCP returned a response, but "
                "GetCallerIdentity information could not be found."
            )

        return AWSIdentity(
            account_id=str(
                identity["Account"]
            ),
            arn=str(
                identity["Arn"]
            ),
            user_id=str(
                identity["UserId"]
            ),
        )
