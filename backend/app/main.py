from fastapi import Depends, FastAPI
from pydantic import BaseModel

from .services.mcp_service import MCPService, get_mcp_service


class ManualRequest(BaseModel):
    prompt: str = ""


def create_app() -> FastAPI:
    app = FastAPI(title="Hackathon Backend", version="0.1.0")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/mcp/manual")
    async def mcp_manual(
        payload: ManualRequest,
        mcp: MCPService = Depends(get_mcp_service),
    ):
        """MCP와 연동해 매뉴얼(행동지침)을 받아오는 엔드포인트."""
        manual = await mcp.fetch_manual(prompt=payload.prompt)
        return {"manual": manual}

    return app


app = create_app()



