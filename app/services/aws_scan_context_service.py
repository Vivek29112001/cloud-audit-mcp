# from fastapi import HTTPException

# from sqlalchemy.ext.asyncio import (
#     AsyncSession,
# )

# from app.db.models.user import User
# from app.repositories.aws_scan_repository import (
#     AWSScanRepository,
# )


# class AWSScanContextService:

#     def __init__(self) -> None:
#         self._scans = (
#             AWSScanRepository()
#         )

#     async def load_scan_context(
#         self,
#         db: AsyncSession,
#         *,
#         user: User,
#         scan_id: str,
#     ) -> dict:

#         scan = (
#             await self._scans
#             .find_by_scan_id(
#                 db,
#                 scan_id=scan_id,
#                 user_id=user.id,
#             )
#         )

#         if scan is None:

#             raise HTTPException(
#                 status_code=404,
#                 detail="AWS scan not found.",
#             )

#         if scan.status != "COMPLETED":

#             raise HTTPException(
#                 status_code=409,
#                 detail=(
#                     "AWS scan is not completed."
#                 ),
#             )

#         return {
#             "scan_id":
#                 scan.scan_id,

#             "status":
#                 scan.status,

#             "account":
#                 scan.account_json,

#             "summary":
#                 scan.summary_json,

#             "regions":
#                 scan.regions_json,

#             "zones":
#                 scan.zones_json,

#             "resources":
#                 scan.resources_json,

#             "billing":
#                 scan.billing_json,

#             "classification":
#                 scan.classification_json,

#             "warnings":
#                 scan.warnings_json,

#             "timings":
#                 scan.timings_json,
#         }



from fastapi import HTTPException

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.db.models.user import User
from app.repositories.aws_scan_repository import (
    AWSScanRepository,
)


class AWSScanContextService:

    def __init__(self) -> None:
        self._scans = (
            AWSScanRepository()
        )

    async def load_scan_context(
        self,
        db: AsyncSession,
        *,
        user: User,
        scan_id: str,
    ) -> dict:

        scan = (
            await self._scans
            .find_by_scan_id(
                db,
                scan_id=scan_id,
                user_id=user.id,
            )
        )

        if scan is None:

            raise HTTPException(
                status_code=404,
                detail="AWS scan not found.",
            )

        if scan.status != "COMPLETED":

            raise HTTPException(
                status_code=409,
                detail=(
                    "AWS scan is not completed."
                ),
            )

        return {
            "scan_id":
                scan.scan_id,

            "status":
                scan.status,

            "is_active":
                bool(scan.is_active),

            "activated_at":
                scan.activated_at,

            "started_at":
                scan.started_at,

            "completed_at":
                scan.completed_at,

            "account":
                scan.account_json,

            "summary":
                scan.summary_json,

            "regions":
                scan.regions_json,

            "zones":
                scan.zones_json,

            "resources":
                scan.resources_json,

            "billing":
                scan.billing_json,

            "classification":
                scan.classification_json,

            "warnings":
                scan.warnings_json,

            "timings":
                scan.timings_json,
        }

