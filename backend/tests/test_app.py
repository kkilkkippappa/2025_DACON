import pytest
from httpx import AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_health():
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_mcp_manual_returns_stubbed_manual():
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post("/mcp/manual", json={"prompt": "check"})
    assert resp.status_code == 200
    body = resp.json()
    assert "manual" in body
    assert body["manual"]["prompt"] == "check"
    assert "content" in body["manual"]





