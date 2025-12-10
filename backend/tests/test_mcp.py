import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import create_app
from app.services.mcp_service import (
    MCPQueueError,
    MCPService,
    ProcessingQueueDTO,
    RemediationResult,
    get_mcp_service,
)
from app.mcp.mcp_client_openai import MCPClientError, OpenAIMCPClient
import app.DB.db_config as db_config
from app.DB.db_config import session_scope
from app.DB.mcp_tables import ProcessingQueueTable
from app.DB.table_dashboard import DashboardAlert


@pytest.fixture()
def anyio_backend():
    return "asyncio"


class StubMCPService(MCPService):
    """router 테스트용 스텁 서비스."""

    def __init__(self) -> None:
        pass  # type: ignore[super-init-not-called]

    async def enqueue(self, payload: Dict[str, Any]) -> ProcessingQueueDTO:  # type: ignore[override]
        if payload.get("manual_reference", {}).get("path") == "dup":
            raise MCPQueueError("duplicate")
        return ProcessingQueueDTO(id=1, trace_id=payload.get("trace_id") or "trace-test", payload=payload)

    async def process_next(self) -> Optional[RemediationResult]:  # type: ignore[override]
        return RemediationResult(
            trace_id="trace-test",
            summary="test summary",
            steps=[{"order": 1, "action": "action", "note": "note"}],
            confidence="high",
        )

    async def get_status(self) -> Dict[str, int]:  # type: ignore[override]
        return {"pending": 1, "processing": 0, "error": 0, "completed": 2, "dead_letters": 0}


class DummyResponses:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text

    async def create(self, **kwargs: Any) -> Any:
        class _Obj:
            pass

        obj = _Obj()
        obj.output_text = self._response_text
        return obj


class DummyAsyncOpenAI:
    def __init__(self, timeout: int = 30, response_text: str | None = None) -> None:
        self.timeout = timeout
        self.responses = DummyResponses(response_text or "")


@pytest.fixture()
def test_app(monkeypatch: pytest.MonkeyPatch):
    app = create_app()
    stub_service = StubMCPService()

    from app.services import mcp_service

    app.dependency_overrides[mcp_service.get_mcp_service] = lambda: stub_service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def sqlite_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    db_path = tmp_path / "mcp_test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    class _SQLiteConfig:
        def __init__(self):
            self.engine = engine
            self._session_factory = TestingSessionLocal

        def session(self):
            return self._session_factory()

        def dependency(self):
            def _dep():
                db = self.session()
                try:
                    yield db
                finally:
                    db.close()

            return _dep

        def session_scope(self):
            @contextmanager
            def _scope():
                db = self.session()
                try:
                    yield db
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
                finally:
                    db.close()

            return _scope()

    sqlite_config = _SQLiteConfig()

    def fake_get_db_config(*args, **kwargs):
        return sqlite_config

    monkeypatch.setattr(db_config, "get_db_config", fake_get_db_config, False)
    monkeypatch.setattr(db_config, "default_db_config", sqlite_config, False)
    monkeypatch.setattr(db_config, "get_db", sqlite_config.dependency(), False)

    db_config.Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal
    db_config.Base.metadata.drop_all(bind=engine)


def test_enqueue_success(test_app: TestClient):
    payload = {
        "trace_id": "trace-1",
        "anomaly": {"sensor": "S1"},
        "ai_error": {"code": "X"},
        "manual_reference": {"path": "manuals/doc.txt", "tags": ["temp"]},
    }
    resp = test_app.post("/mcp/enqueue", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["trace_id"] == "trace-1"
    assert body["status"] == "pending"


def test_enqueue_duplicate_returns_400(test_app: TestClient):
    payload = {
        "anomaly": {},
        "ai_error": {},
        "manual_reference": {"path": "dup", "tags": []},
    }
    resp = test_app.post("/mcp/enqueue", json=payload)
    assert resp.status_code == 400


def test_process_next_returns_remediation(test_app: TestClient):
    resp = test_app.post("/mcp/process-next")
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"] == "test summary"
    assert len(body["steps"]) == 1


def test_status_endpoint(test_app: TestClient):
    resp = test_app.get("/mcp/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pending"] == 1


@pytest.mark.anyio("asyncio")
async def test_openai_client_parses_json(monkeypatch: pytest.MonkeyPatch):
    os.environ["OPENAI_API_KEY"] = "test-key"
    response_text = '{"summary":"ok","steps":[{"order":1,"action":"do","note":"now"}],"confidence":"high"}'

    def fake_client_factory(*args, **kwargs):
        return DummyAsyncOpenAI(response_text=response_text)

    monkeypatch.setattr("app.mcp.mcp_client_openai.AsyncOpenAI", fake_client_factory)
    client = OpenAIMCPClient()
    guidance = await client.generate_guidance({"trace_id": "T"}, "manual text")
    assert guidance["summary"] == "ok"
    assert guidance["steps"][0]["action"] == "do"
    assert guidance["confidence"] == "high"


@pytest.mark.anyio("asyncio")
async def test_openai_client_fallback(monkeypatch: pytest.MonkeyPatch):
    os.environ["OPENAI_API_KEY"] = "test-key"

    def fake_client_factory(*args, **kwargs):
        return DummyAsyncOpenAI(response_text="not-json")

    monkeypatch.setattr("app.mcp.mcp_client_openai.AsyncOpenAI", fake_client_factory)
    client = OpenAIMCPClient()
    guidance = await client.generate_guidance({"trace_id": "T", "anomaly": {"sensor_id": "S1"}}, "manual text")
    assert guidance["summary"].startswith("S1")
    assert guidance["steps"]


class DummyManualRepo:
    def __init__(self, content: str) -> None:
        self.content = content

    def read_manual(self, manual_path: str) -> str:
        return self.content


class DummyLLM:
    def __init__(self) -> None:
        self.model = "dummy-llm"

    async def generate_guidance(self, payload: Dict[str, Any], manual_text: str) -> Dict[str, Any]:
        return {
            "summary": f"{payload.get('trace_id')} result",
            "steps": [{"order": 1, "action": "review", "note": manual_text[:50]}],
            "confidence": "high",
            "model": self.model,
        }


@pytest.mark.anyio("asyncio")
async def test_queue_to_remediation_integration(sqlite_db):
    service = MCPService(manual_repo=DummyManualRepo("menu text"), llm_client=DummyLLM())
    with session_scope() as session:
        alert = DashboardAlert(sensor_id=99, type="temp", mannual="", message="initial")
        session.add(alert)
        session.flush()
        dashboard_id = alert.id

    payload = {
        "trace_id": "trace-integration",
        "anomaly": {"sensor_id": "S99"},
        "ai_error": {"code": "LLM_TIMEOUT"},
        "manual_reference": {"path": "ignored", "tags": ["sensor"]},
        "metadata": {"dashboard_id": dashboard_id},
        "message": "Temperature high",
    }

    entry = await service.enqueue(payload)
    assert entry.id is not None

    remediation = await service.process_next()
    assert remediation.summary == "trace-integration result"
    assert remediation.steps and remediation.steps[0]["action"] == "review"

    with session_scope() as session:
        queue_record = session.query(ProcessingQueueTable).filter_by(trace_id="trace-integration").first()
        assert queue_record is not None
        assert queue_record.status == "done"

        dashboard_entry = session.get(DashboardAlert, dashboard_id)
        assert dashboard_entry is not None
        assert "trace-integration result" in (dashboard_entry.mannual or "")


class AlwaysFailLLM:
    def __init__(self) -> None:
        self.model = "dummy-llm"

    async def generate_guidance(self, payload: Dict[str, Any], manual_text: str) -> Dict[str, Any]:
        raise MCPClientError("LLM failure")


@pytest.mark.anyio("asyncio")
async def test_queue_failure_marks_dashboard(sqlite_db):
    service = MCPService(
        manual_repo=DummyManualRepo("menu text"),
        llm_client=AlwaysFailLLM(),
        max_attempts=1,
    )
    with session_scope() as session:
        alert = DashboardAlert(sensor_id=1, type="temp", mannual="", message="initial")
        session.add(alert)
        session.flush()
        dashboard_id = alert.id

    payload = {
        "trace_id": "trace-failure",
        "anomaly": {"sensor_id": "S1"},
        "manual_reference": {"path": "ignored", "tags": []},
        "metadata": {"dashboard_id": dashboard_id},
        "message": "High temp",
    }

    await service.enqueue(payload)
    with pytest.raises(MCPClientError):
        await service.process_next()

    with session_scope() as session:
        alert = session.get(DashboardAlert, dashboard_id)
        assert alert is not None
        assert alert.mannual == "매뉴얼 생성 실패"


@pytest.mark.anyio("asyncio")
async def test_process_without_dashboard_id_raises(sqlite_db):
    service = MCPService(manual_repo=DummyManualRepo("menu text"), llm_client=DummyLLM())
    payload = {
        "trace_id": "trace-missing-dashboard",
        "anomaly": {"sensor_id": "S2"},
        "manual_reference": {"path": "ignored"},
    }
    await service.enqueue(payload)
    with pytest.raises(MCPQueueError):
        await service.process_next()


class MissingManualRepo(DummyManualRepo):
    def read_manual(self, manual_path: str) -> str:  # type: ignore[override]
        raise FileNotFoundError("not found")


@pytest.mark.anyio("asyncio")
async def test_missing_manual_path_marks_failure(sqlite_db):
    service = MCPService(
        manual_repo=MissingManualRepo(""),
        llm_client=DummyLLM(),
        max_attempts=1,
    )
    with session_scope() as session:
        alert = DashboardAlert(sensor_id=3, type="temp", mannual="", message="initial")
        session.add(alert)
        session.flush()
        dashboard_id = alert.id

    payload = {
        "trace_id": "trace-missing-manual",
        "anomaly": {"sensor_id": "S3"},
        "manual_reference": {"path": "missing"},
        "metadata": {"dashboard_id": dashboard_id},
        "message": "Temp high",
    }
    await service.enqueue(payload)
    with pytest.raises(FileNotFoundError):
        await service.process_next()

    with session_scope() as session:
        alert = session.get(DashboardAlert, dashboard_id)
        assert alert is not None
        assert alert.mannual == "매뉴얼 생성 실패"


class DashboardStubMCPService(MCPService):
    def __init__(self) -> None:
        pass  # type: ignore[super-init-not-called]

    async def enqueue(self, payload: Dict[str, Any]) -> ProcessingQueueDTO:  # type: ignore[override]
        return ProcessingQueueDTO(id=999, trace_id=payload.get("trace_id", ""), payload=payload)

    async def process_job(self, queue_id: int) -> RemediationResult:  # type: ignore[override]
        return RemediationResult(
            trace_id="stub-trace",
            summary="stub summary",
            steps=[{"order": 1, "action": "act", "note": "note"}],
            confidence="high",
        )


def test_dashboard_llm_test_endpoint(monkeypatch, tmp_path):
    os.environ["MCP_TEST_MANUAL_PATH"] = "docs/manuals/fake.txt"
    from router import dashboard_router as dashboard
    dashboard.DEFAULT_TEST_MANUAL_PATH = "docs/manuals/fake.txt"

    app = create_app()
    stub_service = DashboardStubMCPService()
    app.dependency_overrides[get_mcp_service] = lambda: stub_service

    from app.DB import db_config
    engine = create_engine(f"sqlite:///{tmp_path/'db.sqlite'}")
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db_config.Base.metadata.create_all(bind=engine)

    with TestingSession() as session:
        alert = DashboardAlert(sensor_id=10, type="warning", mannual="", message="msg")
        session.add(alert)
        session.commit()
        alert_id = alert.id

    def override_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[dashboard.dashboard_db] = override_db

    client = TestClient(app)
    resp = client.post("/dashboard/test/LLM", json={"id": alert_id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"] == "stub summary"
