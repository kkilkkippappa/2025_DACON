import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import create_app


@pytest.fixture()
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio("asyncio")
async def test_root_welcome_message():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"message": "Welcome to 2025 Hackathon API"}


@pytest.mark.anyio("asyncio")
async def test_unknown_route_returns_404():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/unknown")
    assert resp.status_code == 404





