from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.query_router import AWSQueryRouter
from app.api.schemas.aws import (
    AWSAssumeRoleVerifyRequest,
    AWSConnectionVerifyResponse,
    AWSNaturalLanguageQueryRequest,
    AWSVerifyRequest,
)
from app.api.schemas.scan import PersistedAWSScanResponse
from app.auth.dependencies import get_current_user
from app.db.models.aws_scan import AWSScan
from app.db.models.user import User
from app.db.session import get_db
from app.providers.aws.assume_role import AWSAssumeRoleError, AWSAssumeRoleService
from app.providers.aws.connection import AWSConnectionService
from app.providers.aws.credential_crypto import AWSCredentialCipher
from app.providers.aws.credential_provider import (
    AWSAutomaticAuthenticationError,
    aws_credential_provider,
)
from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.exceptions import AWSMCPExecutionError, InvalidAWSCredentialsError
from app.providers.aws.scanner import AWSScanOrchestrator
from app.providers.aws.session_store import aws_credential_sessions
from app.repositories.aws_connection_repository import AWSConnectionRepository
from app.repositories.aws_scan_repository import AWSScanRepository
from app.services.aws_scan_context_service import AWSScanContextService
from app.services.aws_scan_persistence_service import AWSScanPersistenceService
from app.workspace_dependencies import WorkspaceContext, get_current_workspace


router = APIRouter(prefix="/api/aws", tags=["AWS"])
connection_service = AWSConnectionService()
assume_role_service = AWSAssumeRoleService()
scanner = AWSScanOrchestrator()
scan_persistence_service = AWSScanPersistenceService()
scan_context_service = AWSScanContextService()
query_router = AWSQueryRouter()
connection_repository = AWSConnectionRepository()
scan_repository = AWSScanRepository()


def _serialize_connection(connection):
    return {
        "id": connection.id,
        "workspace_id": connection.workspace_id,
        "provider": connection.provider,
        "account_id": connection.account_id,
        "account_arn": connection.account_arn,
        "display_name": connection.display_name,
        "auth_type": connection.auth_type,
        "default_region": connection.default_region,
        "role_arn": connection.role_arn,
        "auth_status": connection.auth_status,
        "auto_connect": aws_credential_provider.auto_connect_capable(connection),
        "last_auth_error": connection.last_auth_error,
        "last_verified_at": connection.last_verified_at,
        "last_connected_at": connection.last_connected_at,
        "created_at": connection.created_at,
    }


def _serialize_scan(scan: AWSScan):
    return {
        "database_id": scan.id,
        "workspace_id": scan.workspace_id,
        "scan_id": scan.scan_id,
        "aws_connection_id": scan.aws_connection_id,
        "status": scan.status,
        "is_active": bool(scan.is_active),
        "activated_at": scan.activated_at,
        "account": scan.account_json,
        "summary": scan.summary_json,
        "regions": scan.regions_json,
        "zones": scan.zones_json,
        "resources": scan.resources_json,
        "billing": scan.billing_json,
        "classification": scan.classification_json,
        "warnings": scan.warnings_json,
        "timings": scan.timings_json,
        "started_at": scan.started_at,
        "completed_at": scan.completed_at,
    }


def _trust_principal_arn(caller_arn: str) -> str:
    prefix = "arn:aws:sts::"
    marker = ":assumed-role/"
    if caller_arn.startswith(prefix) and marker in caller_arn:
        account = caller_arn.split(":", 5)[4]
        tail = caller_arn.split(marker, 1)[1]
        role_name = tail.split("/", 1)[0]
        return f"arn:aws:iam::{account}:role/{role_name}"
    return caller_arn


async def _persist_verified(
    db: AsyncSession,
    current_user: User,
    workspace_id: int,
    identity,
    *,
    auth_type: str,
    default_region: str,
    role_arn: str | None = None,
    external_id: str | None = None,
    credential_ciphertext: str | None = None,
):
    connection = await connection_repository.upsert_auth_config(
        db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        account_id=identity.account_id,
        account_arn=identity.arn,
        auth_type=auth_type,
        default_region=default_region,
        role_arn=role_arn,
        external_id=external_id,
        credential_ciphertext=credential_ciphertext,
    )
    await db.commit()
    await db.refresh(connection)
    return connection


async def _run_and_persist_scan(
    *,
    credentials: AWSCredentials,
    db: AsyncSession,
    current_user: User,
    workspace_id: int,
):
    result = await scanner.scan(credentials)
    if result.status != "COMPLETED":
        raise HTTPException(
            status_code=502,
            detail={
                "message": "AWS discovery scan failed.",
                "scan_id": result.scan_id,
                "warnings": list(result.warnings),
                "timings": dict(result.timings),
            },
        )

    saved = await scan_persistence_service.save_scan(
        db,
        workspace_id=workspace_id,
        user=current_user,
        scan_result=result,
    )
    return PersistedAWSScanResponse(
        workspace_id=workspace_id,
        scan_id=result.scan_id,
        database_id=saved.id,
        aws_connection_id=saved.aws_connection_id,
        status=result.status,
        is_active=True,
        activated_at=saved.activated_at,
        started_at=result.started_at,
        completed_at=result.completed_at,
        account=result.account.model_dump(mode="json") if result.account else {},
        summary=result.summary.model_dump(mode="json") if result.summary else {},
        regions=result.regions.model_dump(mode="json") if result.regions else {},
        zones=result.zones.model_dump(mode="json") if result.zones else {},
        resources=result.resources.model_dump(mode="json") if result.resources else {},
        billing=result.billing.model_dump(mode="json") if result.billing else {},
        classification=(
            result.classification.model_dump(mode="json")
            if result.classification
            else {}
        ),
        warnings=list(result.warnings),
        timings=dict(result.timings),
    )


@router.post("/verify", response_model=AWSConnectionVerifyResponse)
async def verify_aws_account(
    request: AWSVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    credentials = AWSCredentials(
        access_key_id=request.access_key_id,
        secret_access_key=request.secret_access_key,
        session_token=request.session_token,
        default_region=request.default_region or "us-east-1",
        source="USER_ACCESS_KEYS",
    )
    try:
        identity = await connection_service.verify_credentials(credentials)
    except InvalidAWSCredentialsError as exc:
        raise HTTPException(
            status_code=401,
            detail=f"AWS rejected the provided credentials: {exc}",
        ) from exc
    except AWSMCPExecutionError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"AWS MCP is unavailable or misconfigured: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to verify AWS account through AWS MCP: {exc}",
        ) from exc

    encrypted = AWSCredentialCipher().encrypt(credentials)
    connection = await _persist_verified(
        db,
        current_user,
        workspace.id,
        identity,
        auth_type="PERSISTED_KEYS",
        default_region=credentials.default_region,
        credential_ciphertext=encrypted,
    )
    await aws_credential_sessions.set(
        user_id=current_user.id,
        aws_connection_id=connection.id,
        credentials=credentials,
    )
    return AWSConnectionVerifyResponse(
        workspace_id=workspace.id,
        provider=identity.provider,
        account_id=identity.account_id,
        arn=identity.arn,
        user_id=identity.user_id,
        connection_status=identity.connection_status,
        aws_connection_id=connection.id,
        auth_type=connection.auth_type,
        auto_connect=True,
        default_region=connection.default_region,
    )


@router.get("/connections/assume-role/source-identity")
async def get_assume_role_source_identity(
    current_user: User = Depends(get_current_user),
):
    try:
        identity = await connection_service.verify_credentials(
            assume_role_service.source_credentials()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                "DhanushGuard source AWS identity is not configured or could not "
                f"be verified: {exc}"
            ),
        ) from exc
    principal = _trust_principal_arn(identity.arn)
    return {
        "account_id": identity.account_id,
        "caller_arn": identity.arn,
        "trust_principal_arn": principal,
        "trust_policy_template": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": principal},
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "StringEquals": {"sts:ExternalId": "REPLACE_WITH_EXTERNAL_ID"}
                    },
                }
            ],
        },
    }


@router.post(
    "/connections/assume-role/verify",
    response_model=AWSConnectionVerifyResponse,
)
async def verify_assume_role(
    request: AWSAssumeRoleVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    try:
        credentials = await assume_role_service.assume_role(
            role_arn=request.role_arn,
            external_id=request.external_id,
            default_region=request.default_region,
            connection_id=None,
        )
        identity = await connection_service.verify_credentials(credentials)
    except InvalidAWSCredentialsError as exc:
        raise HTTPException(
            status_code=401,
            detail=f"AWS rejected the assumed-role credentials: {exc}",
        ) from exc
    except AWSAssumeRoleError as exc:
        message = str(exc)
        status_code = (
            403
            if any(
                token in message
                for token in ("AccessDenied", "not authorized", "Not authorized")
            )
            else 503
        )
        raise HTTPException(
            status_code=status_code,
            detail=f"Unable to assume client AWS role: {message}",
        ) from exc
    except AWSMCPExecutionError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"AWS MCP is unavailable or misconfigured: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to verify assumed AWS role: {exc}",
        ) from exc

    connection = await _persist_verified(
        db,
        current_user,
        workspace.id,
        identity,
        auth_type="ASSUME_ROLE",
        default_region=request.default_region,
        role_arn=request.role_arn,
        external_id=request.external_id,
    )
    return AWSConnectionVerifyResponse(
        workspace_id=workspace.id,
        provider=identity.provider,
        account_id=identity.account_id,
        arn=identity.arn,
        user_id=identity.user_id,
        connection_status=identity.connection_status,
        aws_connection_id=connection.id,
        auth_type=connection.auth_type,
        auto_connect=True,
        default_region=connection.default_region,
    )


@router.post("/scan", response_model=PersistedAWSScanResponse)
async def scan_aws_account(
    request: AWSVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    credentials = AWSCredentials(
        access_key_id=request.access_key_id,
        secret_access_key=request.secret_access_key,
        session_token=request.session_token,
        default_region=request.default_region or "us-east-1",
        source="USER_ACCESS_KEYS",
    )
    return await _run_and_persist_scan(
        credentials=credentials,
        db=db,
        current_user=current_user,
        workspace_id=workspace.id,
    )


@router.post(
    "/connections/{connection_id}/scan/refresh",
    response_model=PersistedAWSScanResponse,
)
async def refresh_connection_scan(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    try:
        credentials = await aws_credential_provider.get_credentials(
            db,
            user_id=current_user.id,
            workspace_id=workspace.id,
            aws_connection_id=connection_id,
        )
    except AWSAutomaticAuthenticationError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Automatic AWS authentication failed: {exc}",
        ) from exc
    return await _run_and_persist_scan(
        credentials=credentials,
        db=db,
        current_user=current_user,
        workspace_id=workspace.id,
    )


@router.post("/scan/refresh", response_model=PersistedAWSScanResponse)
async def refresh_active_scan(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    active = await scan_repository.find_active_by_workspace(
        db,
        workspace_id=workspace.id,
    )
    if active:
        connection_id = active.aws_connection_id
    else:
        connections = await connection_repository.find_all_by_workspace(
            db,
            workspace_id=workspace.id,
        )
        if not connections:
            raise HTTPException(
                status_code=404,
                detail="No AWS connection is configured in this workspace.",
            )
        connection_id = connections[0].id
    return await refresh_connection_scan(
        connection_id,
        db,
        current_user,
        workspace,
    )


@router.get("/connections")
async def get_connections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    rows = await connection_repository.find_all_by_workspace(
        db,
        workspace_id=workspace.id,
    )
    return [_serialize_connection(item) for item in rows]


@router.get("/connections/{connection_id}/auth/status")
async def connection_auth_status(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    connection = await connection_repository.find_by_id(
        db,
        connection_id=connection_id,
        workspace_id=workspace.id,
    )
    if not connection:
        raise HTTPException(
            status_code=404,
            detail="AWS connection not found in this workspace.",
        )
    return _serialize_connection(connection)


@router.get("/connections/{connection_id}/scans")
async def get_connection_scans(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    connection = await connection_repository.find_by_id(
        db,
        connection_id=connection_id,
        workspace_id=workspace.id,
    )
    if not connection:
        raise HTTPException(status_code=404, detail="AWS connection not found.")
    rows = await scan_repository.find_by_connection(
        db,
        workspace_id=workspace.id,
        aws_connection_id=connection_id,
    )
    return [_serialize_scan(item) for item in rows]


@router.get("/scans")
async def get_scan_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    rows = await scan_repository.find_all_by_workspace(
        db,
        workspace_id=workspace.id,
    )
    return [_serialize_scan(item) for item in rows]


@router.get("/scans/active")
async def get_active_scan(
    account_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    scan = await scan_repository.find_active_by_workspace(
        db,
        workspace_id=workspace.id,
        account_id=account_id,
    )
    if not scan:
        raise HTTPException(
            status_code=404,
            detail="No active AWS scan found in this workspace.",
        )
    return _serialize_scan(scan)


@router.put("/scans/{scan_id}/activate")
async def activate_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    scan = await scan_repository.find_by_scan_id(
        db,
        scan_id=scan_id,
        workspace_id=workspace.id,
    )
    if not scan:
        raise HTTPException(
            status_code=404,
            detail="AWS scan not found in this workspace.",
        )
    if scan.status != "COMPLETED":
        raise HTTPException(
            status_code=409,
            detail="Only completed scans can be activated.",
        )
    await scan_repository.activate(db, scan=scan)
    await db.commit()
    await db.refresh(scan)
    return _serialize_scan(scan)


@router.get("/scans/{scan_id}")
async def get_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    scan = await scan_repository.find_by_scan_id(
        db,
        scan_id=scan_id,
        workspace_id=workspace.id,
    )
    if not scan:
        raise HTTPException(
            status_code=404,
            detail="AWS scan not found in this workspace.",
        )
    return _serialize_scan(scan)


@router.post("/query")
async def query_aws(
    request: AWSNaturalLanguageQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    context = await scan_context_service.load_scan_context(
        db,
        user=current_user,
        workspace_id=workspace.id,
        scan_id=request.scan_id,
    )

    async def load_credentials():
        return await aws_credential_provider.get_credentials(
            db,
            user_id=current_user.id,
            workspace_id=workspace.id,
            aws_connection_id=context["aws_connection_id"],
        )

    return await query_router.execute(
        question=request.question,
        scan_result=context,
        credential_loader=load_credentials,
        selected_context={
            "workspace_id": workspace.id,
            "workspace_name": workspace.workspace.name,
        },
    )


@router.get("/session/status")
async def get_aws_session_status(
    connection_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    connection = None
    if connection_id:
        connection = await connection_repository.find_by_id(
            db,
            connection_id=connection_id,
            workspace_id=workspace.id,
        )
    else:
        active = await scan_repository.find_active_by_workspace(
            db,
            workspace_id=workspace.id,
        )
        if active:
            connection = await connection_repository.find_by_id(
                db,
                connection_id=active.aws_connection_id,
                workspace_id=workspace.id,
            )
        if connection is None:
            connections = await connection_repository.find_all_by_workspace(
                db,
                workspace_id=workspace.id,
            )
            connection = connections[0] if connections else None

    if not connection:
        return {
            "workspace_id": workspace.id,
            "connected": False,
            "auto_connect": False,
            "auth_type": None,
            "message": "No AWS connection configured in this workspace.",
        }

    auto_connect = aws_credential_provider.auto_connect_capable(connection)
    return {
        "workspace_id": workspace.id,
        "connected": auto_connect,
        "auto_connect": auto_connect,
        "auth_type": connection.auth_type,
        "auth_status": connection.auth_status,
        "connection_id": connection.id,
        "credential_storage": (
            "ENCRYPTED_AT_REST"
            if connection.auth_type == "PERSISTED_KEYS"
            else "STS_ASSUME_ROLE"
            if connection.auth_type == "ASSUME_ROLE"
            else "TRANSIENT_MEMORY"
        ),
        "persists_across_server_restart": connection.auth_type
        in {"PERSISTED_KEYS", "ASSUME_ROLE"},
        "snapshot_access_requires_live_credentials": False,
        "last_auth_error": connection.last_auth_error,
    }


@router.delete("/session")
async def disconnect_aws(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: WorkspaceContext = Depends(get_current_workspace),
):
    connections = await connection_repository.find_all_by_workspace(
        db,
        workspace_id=workspace.id,
    )
    for connection in connections:
        await aws_credential_sessions.remove(
            user_id=current_user.id,
            aws_connection_id=connection.id,
        )
        await aws_credential_provider.clear_cache(
            aws_connection_id=connection.id,
        )
    return {
        "workspace_id": workspace.id,
        "status": "CACHE_CLEARED",
        "message": (
            "Temporary AWS credential caches for this workspace were cleared. "
            "Saved connection configuration and snapshots remain available."
        ),
    }
