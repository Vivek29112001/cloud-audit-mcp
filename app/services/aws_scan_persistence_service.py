# from __future__ import annotations

# from sqlalchemy.ext.asyncio import AsyncSession

# from app.db.models.aws_scan import AWSScan
# from app.db.models.user import User
# from app.providers.aws.models import AWSScanResult
# from app.repositories.aws_connection_repository import (
#     AWSConnectionRepository,
# )
# from app.repositories.aws_scan_repository import (
#     AWSScanRepository,
# )


# class AWSScanPersistenceService:

#     def __init__(self) -> None:

#         self._connections = (
#             AWSConnectionRepository()
#         )

#         self._scans = (
#             AWSScanRepository()
#         )

#     async def save_scan(
#         self,
#         db: AsyncSession,
#         *,
#         user: User,
#         scan_result: AWSScanResult,
#     ) -> AWSScan:

#         if scan_result.account is None:
#             raise ValueError(
#                 "Cannot persist AWS scan "
#                 "without account identity."
#             )

#         account_id = (
#             scan_result.account.account_id
#         )

#         account_arn = (
#             scan_result.account.arn
#         )

#         #
#         # ------------------------------------
#         # 1. Find or create AWS connection
#         # ------------------------------------
#         #

#         connection = (
#             await self._connections
#             .find_by_user_and_account(
#                 db,
#                 user_id=user.id,
#                 account_id=account_id,
#             )
#         )

#         if connection is None:

#             connection = (
#                 await self._connections
#                 .create(
#                     db,
#                     user_id=user.id,
#                     account_id=account_id,
#                     account_arn=account_arn,
#                 )
#             )

#         else:

#             await self._connections.update_connection_time(
#                 connection,
#                 account_arn=account_arn,
#             )

#         #
#         # ------------------------------------
#         # 2. Serialize scan structures
#         # ------------------------------------
#         #

#         account_json = (
#             scan_result.account.model_dump(
#                 mode="json"
#             )
#             if scan_result.account
#             else {}
#         )

#         summary_json = (
#             scan_result.summary.model_dump(
#                 mode="json"
#             )
#             if scan_result.summary
#             else {}
#         )

#         regions_json = (
#             scan_result.regions.model_dump(
#                 mode="json"
#             )
#             if scan_result.regions
#             else {}
#         )

#         zones_json = (
#             scan_result.zones.model_dump(
#                 mode="json"
#             )
#             if scan_result.zones
#             else {}
#         )

#         resources_json = (
#             scan_result.resources.model_dump(
#                 mode="json"
#             )
#             if scan_result.resources
#             else {}
#         )

#         billing_json = (
#             scan_result.billing.model_dump(
#                 mode="json"
#             )
#             if scan_result.billing
#             else {}
#         )

#         classification_json = (
#             scan_result.classification.model_dump(
#                 mode="json"
#             )
#             if scan_result.classification
#             else {}
#         )

#         #
#         # ------------------------------------
#         # 3. Create database scan
#         # ------------------------------------
#         #

#         scan = AWSScan(
#             scan_id=scan_result.scan_id,

#             user_id=user.id,

#             aws_connection_id=(
#                 connection.id
#             ),

#             status=scan_result.status,

#             started_at=(
#                 scan_result.started_at
#             ),

#             completed_at=(
#                 scan_result.completed_at
#             ),

#             account_json=account_json,

#             summary_json=summary_json,

#             regions_json=regions_json,

#             zones_json=zones_json,

#             resources_json=resources_json,

#             billing_json=billing_json,

#             classification_json=classification_json,

#             warnings_json=list(
#                 scan_result.warnings
#             ),

#             timings_json=dict(
#                 scan_result.timings
#             ),
#         )

#         saved_scan = (
#             await self._scans.save(
#                 db,
#                 scan,
#             )
#         )

#         #
#         # Commit connection + scan together.
#         #

#         await db.commit()

#         await db.refresh(
#             saved_scan
#         )

#         return saved_scan



from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.aws_scan import AWSScan
from app.db.models.user import User
from app.providers.aws.models import AWSScanResult
from app.repositories.aws_connection_repository import (
    AWSConnectionRepository,
)
from app.repositories.aws_scan_repository import (
    AWSScanRepository,
)


class AWSScanPersistenceService:

    def __init__(self) -> None:

        self._connections = (
            AWSConnectionRepository()
        )

        self._scans = (
            AWSScanRepository()
        )

    async def save_scan(
        self,
        db: AsyncSession,
        *,
        user: User,
        scan_result: AWSScanResult,
    ) -> AWSScan:

        if scan_result.account is None:
            raise ValueError(
                "Cannot persist AWS scan "
                "without account identity."
            )

        account_id = (
            scan_result.account.account_id
        )

        account_arn = (
            scan_result.account.arn
        )

        #
        # ------------------------------------
        # 1. Find or create AWS connection
        # ------------------------------------
        #

        connection = (
            await self._connections
            .find_by_user_and_account(
                db,
                user_id=user.id,
                account_id=account_id,
            )
        )

        if connection is None:

            connection = (
                await self._connections
                .create(
                    db,
                    user_id=user.id,
                    account_id=account_id,
                    account_arn=account_arn,
                )
            )

        else:

            await self._connections.update_connection_time(
                connection,
                account_arn=account_arn,
            )

        #
        # ------------------------------------
        # 2. Serialize scan structures
        # ------------------------------------
        #

        account_json = (
            scan_result.account.model_dump(
                mode="json"
            )
            if scan_result.account
            else {}
        )

        summary_json = (
            scan_result.summary.model_dump(
                mode="json"
            )
            if scan_result.summary
            else {}
        )

        regions_json = (
            scan_result.regions.model_dump(
                mode="json"
            )
            if scan_result.regions
            else {}
        )

        zones_json = (
            scan_result.zones.model_dump(
                mode="json"
            )
            if scan_result.zones
            else {}
        )

        resources_json = (
            scan_result.resources.model_dump(
                mode="json"
            )
            if scan_result.resources
            else {}
        )

        billing_json = (
            scan_result.billing.model_dump(
                mode="json"
            )
            if scan_result.billing
            else {}
        )

        classification_json = (
            scan_result.classification.model_dump(
                mode="json"
            )
            if scan_result.classification
            else {}
        )

        #
        # ------------------------------------
        # 3. Create database scan
        # ------------------------------------
        #

        scan = AWSScan(
            scan_id=scan_result.scan_id,

            user_id=user.id,

            aws_connection_id=(
                connection.id
            ),

            status=scan_result.status,

            started_at=(
                scan_result.started_at
            ),

            completed_at=(
                scan_result.completed_at
            ),

            account_json=account_json,

            summary_json=summary_json,

            regions_json=regions_json,

            zones_json=zones_json,

            resources_json=resources_json,

            billing_json=billing_json,

            classification_json=classification_json,

            warnings_json=list(
                scan_result.warnings
            ),

            timings_json=dict(
                scan_result.timings
            ),
        )

        saved_scan = (
            await self._scans.save(
                db,
                scan,
            )
        )

        # The new scan becomes the active immutable snapshot for this
        # user/account. Older scans remain persisted for history/diffing.
        await self._scans.activate(
            db,
            scan=saved_scan,
        )

        #
        # Commit connection + scan + active pointer together.
        #

        await db.commit()

        await db.refresh(
            saved_scan
        )

        return saved_scan

