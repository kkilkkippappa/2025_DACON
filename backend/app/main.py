import sys
from pathlib import Path
from starlette.middleware.cors import CORSMiddleware
from fastapi import Depends, FastAPI
from pydantic import BaseModel
import uvicorn

# Ensure sibling router package is importable when running this file directly
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from router import dashboard_router as dashboard, sensor_router as sensor, mcp_router as mcp
from app.services.mcp_service import MCPService, get_mcp_service
from app.logging_config import get_logger

logger = get_logger(__name__)

class ManualRequest(BaseModel):
    prompt: str



def create_app() -> FastAPI:
    """Application factory so tests/importers can initialize a fresh FastAPI app."""
    application = FastAPI(title="Hackathon Backend", version="0.1.0")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(sensor.router)
    application.include_router(mcp.router)
    application.include_router(dashboard.router)

    @application.get("/")
    async def root():
        return {"message": "Welcome to 2025 Hackathon API"}

    logger.info("FastAPI application created with routers: dashboard, sensor, mcp")
    return application


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
