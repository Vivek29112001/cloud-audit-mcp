# from __future__ import annotations

# from fastapi import (
#     APIRouter,
#     Depends,
#     HTTPException,
# )
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.ai.query_router import AWSQueryRouter

# from app.api.schemas.aws import (
#     AWSNaturalLanguageQueryRequest,
#     AWSVerifyRequest,
#     AWSVerifyResponse,
# )

# from app.api.schemas.scan import (
#     PersistedAWSScanResponse,
# )

# from app.auth.dependencies import (
#     get_current_user,
# )

# from app.db.models.user import User

# from app.db.session import (
#     get_db,
# )

# from app.providers.aws.connection import (
#     AWSConnectionService,
# )

# from app.providers.aws.credentials import (
#     AWSCredentials,
# )

# from app.providers.aws.scanner import (
#     AWSScanOrchestrator,
# )

# from app.providers.aws.session_store import (
#     aws_credential_sessions,
# )

# from app.repositories.aws_connection_repository import (
#     AWSConnectionRepository,
# )

# from app.repositories.aws_scan_repository import (
#     AWSScanRepository,
# )

# from app.services.aws_scan_context_service import (
#     AWSScanContextService,
# )

# from app.services.aws_scan_persistence_service import (
#     AWSScanPersistenceService,
# )


# # ============================================================
# # ROUTER
# # ============================================================

# router = APIRouter(
#     prefix="/api/aws",
#     tags=["AWS"],
# )


# # ============================================================
# # SERVICES
# # ============================================================

# connection_service = (
#     AWSConnectionService()
# )

# scanner = (
#     AWSScanOrchestrator()
# )

# scan_persistence_service = (
#     AWSScanPersistenceService()
# )

# scan_context_service = (
#     AWSScanContextService()
# )

# query_router = (
#     AWSQueryRouter()
# )


# # ============================================================
# # REPOSITORIES
# # ============================================================

# connection_repository = (
#     AWSConnectionRepository()
# )

# scan_repository = (
#     AWSScanRepository()
# )


# # ============================================================
# # VERIFY AWS ACCOUNT
# # ============================================================

# @router.post(
#     "/verify",
#     response_model=AWSVerifyResponse,
# )
# async def verify_aws_account(
#     request: AWSVerifyRequest,

#     current_user: User = Depends(
#         get_current_user
#     ),
# ):
#     """
#     Verify AWS credentials through the official AWS MCP server.

#     This endpoint does NOT run the complete discovery scan.

#     On successful verification:
#     - AWS identity is returned.
#     - Credentials are stored only in temporary backend memory.
#     - Credentials are NOT written to SQLite.
#     """

#     credentials = AWSCredentials(
#         access_key_id=(
#             request.access_key_id
#         ),

#         secret_access_key=(
#             request.secret_access_key
#         ),

#         session_token=(
#             request.session_token
#         ),

#         default_region=(
#             request.default_region
#             or "us-east-1"
#         ),
#     )

#     try:
#         identity = (
#             await connection_service
#             .verify_credentials(
#                 credentials
#             )
#         )

#     except Exception as exc:
#         raise HTTPException(
#             status_code=401,
#             detail=(
#                 "Unable to verify AWS credentials: "
#                 f"{exc}"
#             ),
#         ) from exc

#     # --------------------------------------------------------
#     # Store credentials ONLY in backend runtime memory
#     # --------------------------------------------------------

#     await aws_credential_sessions.set(
#         user_id=current_user.id,
#         credentials=credentials,
#     )

#     return AWSVerifyResponse(
#         provider=identity.provider,
#         account_id=identity.account_id,
#         arn=identity.arn,
#         user_id=identity.user_id,
#         connection_status=(
#             identity.connection_status
#         ),
#     )


# # ============================================================
# # RUN AWS DISCOVERY SCAN
# # ============================================================

# @router.post(
#     "/scan",
#     response_model=PersistedAWSScanResponse,
# )
# async def scan_aws_account(
#     request: AWSVerifyRequest,

#     db: AsyncSession = Depends(
#         get_db
#     ),

#     current_user: User = Depends(
#         get_current_user
#     ),
# ):
#     """
#     Run the complete lightweight AWS discovery scan.

#     Flow:

#         AWS credentials
#             ↓
#         Official AWS MCP
#             ↓
#         Account identity
#             ↓
#         Region discovery
#             ↓
#         Availability Zones
#             ↓
#         Resource / service discovery
#             ↓
#         Persist discovery result in SQLite

#     AWS credentials themselves are never persisted.
#     """

#     # --------------------------------------------------------
#     # 1. Build credentials
#     # --------------------------------------------------------

#     credentials = AWSCredentials(
#         access_key_id=(
#             request.access_key_id
#         ),

#         secret_access_key=(
#             request.secret_access_key
#         ),

#         session_token=(
#             request.session_token
#         ),

#         default_region=(
#             request.default_region
#             or "us-east-1"
#         ),
#     )

#     # --------------------------------------------------------
#     # 2. Run Phase 1 scanner
#     # --------------------------------------------------------

#     result = await scanner.scan(
#         credentials
#     )

#     # --------------------------------------------------------
#     # 3. Handle failed scan
#     # --------------------------------------------------------

#     if result.status != "COMPLETED":
#         raise HTTPException(
#             status_code=502,
#             detail={
#                 "message":
#                     "AWS discovery scan failed.",

#                 "scan_id":
#                     result.scan_id,

#                 "warnings":
#                     list(
#                         result.warnings
#                     ),

#                 "timings":
#                     dict(
#                         result.timings
#                     ),
#             },
#         )

#     # --------------------------------------------------------
#     # 4. Persist scan/account metadata
#     # --------------------------------------------------------

#     persisted_scan = (
#         await scan_persistence_service
#         .save_scan(
#             db,
#             user=current_user,
#             scan_result=result,
#         )
#     )

#     # --------------------------------------------------------
#     # 5. Refresh temporary credential session
#     # --------------------------------------------------------

#     await aws_credential_sessions.set(
#         user_id=current_user.id,
#         credentials=credentials,
#     )

#     # --------------------------------------------------------
#     # 6. Return persisted scan
#     # --------------------------------------------------------

#     return PersistedAWSScanResponse(
#         scan_id=(
#             result.scan_id
#         ),

#         database_id=(
#             persisted_scan.id
#         ),

#         aws_connection_id=(
#             persisted_scan
#             .aws_connection_id
#         ),

#         status=(
#             result.status
#         ),

#         account=(
#             result.account.model_dump(
#                 mode="json"
#             )
#             if result.account
#             else {}
#         ),

#         summary=(
#             result.summary.model_dump(
#                 mode="json"
#             )
#             if result.summary
#             else {}
#         ),

#         regions=(
#             result.regions.model_dump(
#                 mode="json"
#             )
#             if result.regions
#             else {}
#         ),

#         zones=(
#             result.zones.model_dump(
#                 mode="json"
#             )
#             if result.zones
#             else {}
#         ),

#         resources=(
#             result.resources.model_dump(
#                 mode="json"
#             )
#             if result.resources
#             else {}
#         ),

#         billing=(
#             result.billing.model_dump(
#                 mode="json"
#             )
#             if result.billing
#             else {}
#         ),

#         classification=(
#             result.classification.model_dump(
#                 mode="json"
#             )
#             if result.classification
#             else {}
#         ),

#         warnings=list(
#             result.warnings
#         ),

#         timings=dict(
#             result.timings
#         ),
#     )


# # ============================================================
# # AWS CONNECTIONS
# # ============================================================

# @router.get(
#     "/connections"
# )
# async def get_aws_connections(
#     db: AsyncSession = Depends(
#         get_db
#     ),

#     current_user: User = Depends(
#         get_current_user
#     ),
# ):
#     """
#     Return AWS account metadata previously discovered
#     by the authenticated user.

#     No credentials are returned.
#     """

#     connections = (
#         await connection_repository
#         .find_all_by_user(
#             db,
#             user_id=current_user.id,
#         )
#     )

#     return [
#         {
#             "id":
#                 connection.id,

#             "provider":
#                 connection.provider,

#             "account_id":
#                 connection.account_id,

#             "account_arn":
#                 connection.account_arn,

#             "display_name":
#                 connection.display_name,

#             "last_connected_at":
#                 connection.last_connected_at,

#             "created_at":
#                 connection.created_at,
#         }

#         for connection
#         in connections
#     ]


# # ============================================================
# # SCANS FOR ONE AWS CONNECTION
# # ============================================================

# @router.get(
#     "/connections/{connection_id}/scans"
# )
# async def get_connection_scans(
#     connection_id: int,

#     db: AsyncSession = Depends(
#         get_db
#     ),

#     current_user: User = Depends(
#         get_current_user
#     ),
# ):
#     """
#     Return discovery scans for one AWS account/connection.
#     """

#     scans = (
#         await scan_repository
#         .find_by_connection(
#             db,

#             user_id=(
#                 current_user.id
#             ),

#             aws_connection_id=(
#                 connection_id
#             ),
#         )
#     )

#     return [
#         {
#             "database_id":
#                 scan.id,

#             "scan_id":
#                 scan.scan_id,

#             "aws_connection_id":
#                 scan.aws_connection_id,

#             "status":
#                 scan.status,

#             "account":
#                 scan.account_json,

#             "summary":
#                 scan.summary_json,

#             "warnings":
#                 scan.warnings_json,

#             "timings":
#                 scan.timings_json,

#             "started_at":
#                 scan.started_at,

#             "completed_at":
#                 scan.completed_at,
#         }

#         for scan
#         in scans
#     ]


# # ============================================================
# # ALL SCANS FOR CURRENT USER
# # ============================================================

# @router.get(
#     "/scans"
# )
# async def get_scan_history(
#     db: AsyncSession = Depends(
#         get_db
#     ),

#     current_user: User = Depends(
#         get_current_user
#     ),
# ):
#     """
#     Return all persisted discovery scans for
#     the authenticated user.
#     """

#     scans = (
#         await scan_repository
#         .find_all_by_user(
#             db,
#             user_id=current_user.id,
#         )
#     )

#     return [
#         {
#             "database_id":
#                 scan.id,

#             "scan_id":
#                 scan.scan_id,

#             "aws_connection_id":
#                 scan.aws_connection_id,

#             "status":
#                 scan.status,

#             "account":
#                 scan.account_json,

#             "summary":
#                 scan.summary_json,

#             "warnings":
#                 scan.warnings_json,

#             "timings":
#                 scan.timings_json,

#             "started_at":
#                 scan.started_at,

#             "completed_at":
#                 scan.completed_at,
#         }

#         for scan
#         in scans
#     ]


# # ============================================================
# # GET ONE SCAN
# # ============================================================

# @router.get(
#     "/scans/{scan_id}"
# )
# async def get_scan(
#     scan_id: str,

#     db: AsyncSession = Depends(
#         get_db
#     ),

#     current_user: User = Depends(
#         get_current_user
#     ),
# ):
#     """
#     Return the complete persisted discovery result.
#     """

#     scan = (
#         await scan_repository
#         .find_by_scan_id(
#             db,
#             scan_id=scan_id,
#             user_id=current_user.id,
#         )
#     )

#     if scan is None:
#         raise HTTPException(
#             status_code=404,
#             detail="AWS scan not found.",
#         )

#     return {
#         "database_id":
#             scan.id,

#         "scan_id":
#             scan.scan_id,

#         "aws_connection_id":
#             scan.aws_connection_id,

#         "status":
#             scan.status,

#         "account":
#             scan.account_json,

#         "summary":
#             scan.summary_json,

#         "regions":
#             scan.regions_json,

#         "zones":
#             scan.zones_json,

#         "resources":
#             scan.resources_json,

#         "billing":
#             scan.billing_json,

#         "classification":
#             scan.classification_json,

#         "warnings":
#             scan.warnings_json,

#         "timings":
#             scan.timings_json,

#         "started_at":
#             scan.started_at,

#         "completed_at":
#             scan.completed_at,
#     }


# # ============================================================
# # DIRECT NLP QUERY
# # ============================================================

# @router.post(
#     "/query"
# )
# async def query_aws(
#     request: AWSNaturalLanguageQueryRequest,

#     db: AsyncSession = Depends(
#         get_db
#     ),

#     current_user: User = Depends(
#         get_current_user
#     ),
# ):
#     """
#     Execute a direct NLP AWS query.

#     Request contains only:

#         scan_id
#         question

#     The persisted scan is loaded from SQLite.
#     AWS credentials are loaded from temporary memory.
#     """

#     # --------------------------------------------------------
#     # 1. Load scan context
#     # --------------------------------------------------------

#     scan_context = (
#         await scan_context_service
#         .load_scan_context(
#             db,
#             user=current_user,
#             scan_id=request.scan_id,
#         )
#     )

#     # --------------------------------------------------------
#     # 2. Get transient AWS credentials
#     # --------------------------------------------------------

#     credentials = (
#         await aws_credential_sessions
#         .get(
#             user_id=current_user.id
#         )
#     )

#     if credentials is None:
#         raise HTTPException(
#             status_code=409,
#             detail=(
#                 "AWS connection has expired "
#                 "or is not active. "
#                 "Please verify the AWS account again."
#             ),
#         )

#     # --------------------------------------------------------
#     # 3. Execute query
#     # --------------------------------------------------------

#     result = (
#         await query_router.execute(
#             question=(
#                 request.question
#             ),

#             credentials=(
#                 credentials
#             ),

#             scan_result=(
#                 scan_context
#             ),
#         )
#     )

#     return result


# # ============================================================
# # AWS SESSION STATUS
# # ============================================================

# @router.get(
#     "/session/status"
# )
# async def get_aws_session_status(
#     current_user: User = Depends(
#         get_current_user
#     ),
# ):
#     """
#     Return whether the backend currently has valid
#     transient AWS credentials for the user.

#     Credentials themselves are never exposed.
#     """

#     credentials = (
#         await aws_credential_sessions
#         .get(
#             user_id=current_user.id
#         )
#     )

#     return {
#         "connected":
#             credentials is not None
#     }


# # ============================================================
# # DISCONNECT AWS
# # ============================================================

# @router.delete(
#     "/session"
# )
# async def disconnect_aws(
#     current_user: User = Depends(
#         get_current_user
#     ),
# ):
#     """
#     Remove transient AWS credentials from backend memory.

#     Persisted scans, connections and chat history remain.
#     """

#     await aws_credential_sessions.remove(
#         user_id=current_user.id
#     )

#     return {
#         "status":
#             "DISCONNECTED",

#         "message":
#             "AWS live session disconnected.",
#     }



from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.query_router import AWSQueryRouter
from app.api.schemas.aws import AWSNaturalLanguageQueryRequest, AWSVerifyRequest, AWSVerifyResponse
from app.api.schemas.scan import PersistedAWSScanResponse
from app.auth.dependencies import get_current_user
from app.db.models.aws_scan import AWSScan
from app.db.models.user import User
from app.db.session import get_db
from app.providers.aws.connection import AWSConnectionService
from app.providers.aws.credentials import AWSCredentials
from app.providers.aws.scanner import AWSScanOrchestrator
from app.providers.aws.session_store import aws_credential_sessions
from app.repositories.aws_connection_repository import AWSConnectionRepository
from app.repositories.aws_scan_repository import AWSScanRepository
from app.services.aws_scan_context_service import AWSScanContextService
from app.services.aws_scan_persistence_service import AWSScanPersistenceService


router = APIRouter(prefix="/api/aws", tags=["AWS"])
connection_service = AWSConnectionService()
scanner = AWSScanOrchestrator()
scan_persistence_service = AWSScanPersistenceService()
scan_context_service = AWSScanContextService()
query_router = AWSQueryRouter()
connection_repository = AWSConnectionRepository()
scan_repository = AWSScanRepository()


def _serialize_scan(scan: AWSScan) -> dict:
    return {
        "database_id": scan.id,
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


async def _run_and_persist_scan(
    *,
    credentials: AWSCredentials,
    db: AsyncSession,
    current_user: User,
) -> PersistedAWSScanResponse:
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

    persisted_scan = await scan_persistence_service.save_scan(
        db,
        user=current_user,
        scan_result=result,
    )

    await aws_credential_sessions.set(
        user_id=current_user.id,
        credentials=credentials,
    )

    return PersistedAWSScanResponse(
        scan_id=result.scan_id,
        database_id=persisted_scan.id,
        aws_connection_id=persisted_scan.aws_connection_id,
        status=result.status,
        is_active=True,
        activated_at=persisted_scan.activated_at,
        started_at=result.started_at,
        completed_at=result.completed_at,
        account=result.account.model_dump(mode="json") if result.account else {},
        summary=result.summary.model_dump(mode="json") if result.summary else {},
        regions=result.regions.model_dump(mode="json") if result.regions else {},
        zones=result.zones.model_dump(mode="json") if result.zones else {},
        resources=result.resources.model_dump(mode="json") if result.resources else {},
        billing=result.billing.model_dump(mode="json") if result.billing else {},
        classification=(
            result.classification.model_dump(mode="json") if result.classification else {}
        ),
        warnings=list(result.warnings),
        timings=dict(result.timings),
    )


@router.post("/verify", response_model=AWSVerifyResponse)
async def verify_aws_account(
    request: AWSVerifyRequest,
    current_user: User = Depends(get_current_user),
):
    """Verify credentials and retain them only in the transient backend session."""
    credentials = AWSCredentials(
        access_key_id=request.access_key_id,
        secret_access_key=request.secret_access_key,
        session_token=request.session_token,
        default_region=request.default_region or "us-east-1",
    )

    try:
        identity = await connection_service.verify_credentials(credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail=f"Unable to verify AWS credentials: {exc}",
        ) from exc

    await aws_credential_sessions.set(user_id=current_user.id, credentials=credentials)

    return AWSVerifyResponse(
        provider=identity.provider,
        account_id=identity.account_id,
        arn=identity.arn,
        user_id=identity.user_id,
        connection_status=identity.connection_status,
    )


@router.post("/scan", response_model=PersistedAWSScanResponse)
async def scan_aws_account(
    request: AWSVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Backward-compatible discovery endpoint accepting credentials in the request."""
    credentials = AWSCredentials(
        access_key_id=request.access_key_id,
        secret_access_key=request.secret_access_key,
        session_token=request.session_token,
        default_region=request.default_region or "us-east-1",
    )
    return await _run_and_persist_scan(
        credentials=credentials,
        db=db,
        current_user=current_user,
    )


@router.post("/scan/refresh", response_model=PersistedAWSScanResponse)
async def refresh_aws_scan(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Explicit manual refresh. It creates a NEW immutable snapshot and makes it active.
    No discovery scan is triggered automatically by login/page load.
    """
    credentials = await aws_credential_sessions.get(user_id=current_user.id)
    if credentials is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "AWS live session is not active. Reconnect the AWS account before "
                "refreshing discovery. The saved snapshot remains available."
            ),
        )

    return await _run_and_persist_scan(
        credentials=credentials,
        db=db,
        current_user=current_user,
    )


@router.get("/connections")
async def get_aws_connections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connections = await connection_repository.find_all_by_user(
        db, user_id=current_user.id
    )
    return [
        {
            "id": connection.id,
            "provider": connection.provider,
            "account_id": connection.account_id,
            "account_arn": connection.account_arn,
            "display_name": connection.display_name,
            "last_connected_at": connection.last_connected_at,
            "created_at": connection.created_at,
        }
        for connection in connections
    ]


@router.get("/connections/{connection_id}/scans")
async def get_connection_scans(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scans = await scan_repository.find_by_connection(
        db,
        user_id=current_user.id,
        aws_connection_id=connection_id,
    )
    return [_serialize_scan(scan) for scan in scans]


@router.get("/scans")
async def get_scan_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scans = await scan_repository.find_all_by_user(db, user_id=current_user.id)
    return [_serialize_scan(scan) for scan in scans]


@router.get("/scans/active")
async def get_active_scan(
    account_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restore the user's persisted active snapshot without running AWS discovery."""
    scan = await scan_repository.find_active_by_user(
        db,
        user_id=current_user.id,
        account_id=account_id,
    )
    if scan is None:
        raise HTTPException(status_code=404, detail="No active AWS scan found.")
    return _serialize_scan(scan)


@router.put("/scans/{scan_id}/activate")
async def activate_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually select a historical immutable scan as the active snapshot."""
    scan = await scan_repository.find_by_scan_id(
        db,
        scan_id=scan_id,
        user_id=current_user.id,
    )
    if scan is None:
        raise HTTPException(status_code=404, detail="AWS scan not found.")
    if scan.status != "COMPLETED":
        raise HTTPException(status_code=409, detail="Only completed scans can be activated.")

    await scan_repository.activate(db, scan=scan)
    await db.commit()
    await db.refresh(scan)
    return _serialize_scan(scan)


@router.get("/scans/{scan_id}")
async def get_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = await scan_repository.find_by_scan_id(
        db,
        scan_id=scan_id,
        user_id=current_user.id,
    )
    if scan is None:
        raise HTTPException(status_code=404, detail="AWS scan not found.")
    return _serialize_scan(scan)


@router.post("/query")
async def query_aws(
    request: AWSNaturalLanguageQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan_context = await scan_context_service.load_scan_context(
        db,
        user=current_user,
        scan_id=request.scan_id,
    )

    # Credentials are optional here. Snapshot questions must continue to work
    # after the transient AWS live session expires.
    credentials = await aws_credential_sessions.get(user_id=current_user.id)

    return await query_router.execute(
        question=request.question,
        credentials=credentials,
        scan_result=scan_context,
    )


@router.get("/session/status")
async def get_aws_session_status(
    current_user: User = Depends(get_current_user),
):
    credentials = await aws_credential_sessions.get(user_id=current_user.id)
    return {
        "connected": credentials is not None,
        "credential_storage": "TRANSIENT_MEMORY",
        "persists_across_server_restart": False,
        "snapshot_access_requires_live_credentials": False,
    }


@router.delete("/session")
async def disconnect_aws(
    current_user: User = Depends(get_current_user),
):
    await aws_credential_sessions.remove(user_id=current_user.id)
    return {
        "status": "DISCONNECTED",
        "message": "AWS live session disconnected. Persisted scans and chats remain available.",
    }


