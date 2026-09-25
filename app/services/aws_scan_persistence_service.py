from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.aws_scan import AWSScan
from app.db.models.user import User
from app.providers.aws.models import AWSScanResult
from app.repositories.aws_connection_repository import AWSConnectionRepository
from app.repositories.aws_scan_repository import AWSScanRepository


class AWSScanPersistenceService:
    def __init__(self):
        self._connections = AWSConnectionRepository()
        self._scans = AWSScanRepository()

    async def save_scan(
        self,
        db: AsyncSession,
        *,
        workspace_id: int,
        user: User,
        scan_result: AWSScanResult,
    ) -> AWSScan:
        if scan_result.account is None:
            raise ValueError("Cannot persist AWS scan without account identity.")

        connection = await self._connections.find_by_workspace_and_account(
            db,
            workspace_id=workspace_id,
            account_id=scan_result.account.account_id,
        )
        if connection is None:
            connection = await self._connections.create(
                db,
                workspace_id=workspace_id,
                user_id=user.id,
                account_id=scan_result.account.account_id,
                account_arn=scan_result.account.arn,
            )
        else:
            await self._connections.update_connection_time(
                connection,
                account_arn=scan_result.account.arn,
            )

        def dump(value):
            return value.model_dump(mode="json") if value else {}

        scan = AWSScan(
            scan_id=scan_result.scan_id,
            workspace_id=workspace_id,
            user_id=user.id,
            aws_connection_id=connection.id,
            status=scan_result.status,
            started_at=scan_result.started_at,
            completed_at=scan_result.completed_at,
            account_json=dump(scan_result.account),
            summary_json=dump(scan_result.summary),
            regions_json=dump(scan_result.regions),
            zones_json=dump(scan_result.zones),
            resources_json=dump(scan_result.resources),
            billing_json=dump(scan_result.billing),
            classification_json=dump(scan_result.classification),
            warnings_json=list(scan_result.warnings),
            timings_json=dict(scan_result.timings),
        )
        saved = await self._scans.save(db, scan)
        await self._scans.activate(db, scan=saved)
        await db.commit()
        await db.refresh(saved)
        return saved
