# from contextlib import asynccontextmanager

# from fastapi import FastAPI

# from app.db.base import Base
# from app.db import models  # noqa: F401
# from app.db.session import engine

# from app.api.health import (
#     router as health_router,
# )
# from app.api.aws import (
#     router as aws_router,
# )
# from app.api import auth
# from app.api.chats import (
#     router as chats_router,
# )
# from app.core.config import settings


# @asynccontextmanager
# async def lifespan(_app: FastAPI):
#     async with engine.begin() as connection:
#         await connection.run_sync(Base.metadata.create_all)

#     yield


# app = FastAPI(
#     title=settings.app_name,
#     version="0.2.0",
#     lifespan=lifespan,
# )


# # ============================================================
# # ROUTERS
# # ============================================================


# # health.py defines routes such as:
# #
# #     /health
# #
# # therefore application-level /api is added here.
# app.include_router(
#     health_router,
#     prefix="/api",
# )


# # aws.py already defines:
# #
# #     prefix="/api/aws"
# #
# # DO NOT add prefix="/api" again here,
# # otherwise routes become:
# #
# #     /api/api/aws/...
# app.include_router(
#     aws_router,
# )


# # auth.py already owns its complete prefix:
# #
# #     /api/auth
# app.include_router(
#     auth.router,
# )


# # chats.py already owns:
# #
# #     /api/chats
# app.include_router(
#     chats_router,
# )


# # ============================================================
# # ROOT
# # ============================================================


# @app.get("/")
# async def root() -> dict[str, str]:
#     return {
#         "application": settings.app_name,
#         "status": "running",
#     }


# # ============================================================
# # OPTIONAL ROUTE DEBUGGING
# # ============================================================
# #
# # Uncomment temporarily if you want to see every registered
# # route during application startup.
# #
# # for route in app.routes:
# #     methods = getattr(
# #         route,
# #         "methods",
# #         None,
# #     )
# #
# #     if methods:
# #         print(
# #             methods,
# #             route.path,
# #         )



from fastapi import FastAPI

from app.api import auth
from app.api.aws import router as aws_router
from app.api.chats import router as chats_router
from app.api.health import router as health_router
from app.api.workspaces import router as workspaces_router
from app.core.config import settings


# Database schema changes are owned by Alembic. Do not call
# Base.metadata.create_all() on startup: doing so can create only the new tables
# in an older database before the migration has added workspace_id columns,
# leaving the schema in a partially upgraded state.
app = FastAPI(
    title=settings.app_name,
    version="0.3.0",
)


# health.py defines /health, so application-level /api is added here.
app.include_router(health_router, prefix="/api")

# These routers already own their complete /api/... prefixes.
app.include_router(aws_router)
app.include_router(auth.router)
app.include_router(workspaces_router)
app.include_router(chats_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "application": settings.app_name,
        "status": "running",
    }
