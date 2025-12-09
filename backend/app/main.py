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

from router import dashboard_router as dashboard, db_router as db, mcp_router as mcp
from app.services.mcp_service import MCPService, get_mcp_service

class ManualRequest(BaseModel):
    prompt: str



def create_app() -> FastAPI:
    """Application factory so tests/importers can initialize a fresh FastAPI app."""
    application = FastAPI(title="Hackathon Backend", version="0.1.0")


    application.include_router(db.router)
    application.include_router(mcp.router)
    application.include_router(dashboard.router)

    @application.get("/")
    async def root():
        return {"message": "Welcome to 2025 Hackathon API"}

    return application


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
