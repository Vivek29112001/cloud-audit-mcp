from fastapi import APIRouter, HTTPException, status

from app.api.schemas.aws import (
    AWSVerifyRequest,
    AWSVerifyResponse,
)
from app.providers.aws.connection import AWSConnectionService
from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.exceptions import (
    AWSMCPExecutionError,
    InvalidAWSCredentialsError,
)
from app.providers.aws.mcp_client import AWSMCPClient


router = APIRouter(
    prefix="/aws",
    tags=["AWS"],
)


@router.post("/mcp/diagnostics")
async def mcp_diagnostics(
    request: AWSVerifyRequest,
):
    credentials = AWSCredentials(
        access_key_id=request.access_key_id,
        secret_access_key=request.secret_access_key,
        session_token=request.session_token,
        default_region="ap-south-1",
    )

    client = AWSMCPClient(credentials)

    tools = await client.list_tools()

    return {
        "connected": True,
        "tool_count": len(tools),
        "tools": [
            tool.name
            for tool in tools
        ],
    }


@router.post(
    "/verify",
    response_model=AWSVerifyResponse,
)
async def verify_aws_connection(
    request: AWSVerifyRequest,
) -> AWSVerifyResponse:

    credentials = AWSCredentials(
        access_key_id=request.access_key_id,
        secret_access_key=request.secret_access_key,
        session_token=request.session_token,
         default_region="ap-south-1",
    )

    service = AWSConnectionService()

    try:
        identity = await service.verify_credentials(
            credentials
        )

    except InvalidAWSCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    except AWSMCPExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return AWSVerifyResponse(
        provider=identity.provider,
        account_id=identity.account_id,
        arn=identity.arn,
        user_id=identity.user_id,
        connection_status=identity.connection_status,
    )