from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import settings
from app.api.aws import router as aws_router

app = FastAPI(
    title = settings.app_name,
    version = "0.1.0"
)

app.include_router(
    health_router,
    prefix="/api"
)

app.include_router(
    aws_router,
    prefix="/api"
)

@app.get("/")
async def root() -> dict[str,str]:
    return{
        "application": settings.app_name,
        "status": "running",
    }
    
