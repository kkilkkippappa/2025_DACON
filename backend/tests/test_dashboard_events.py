import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import create_app
from app.DB import db_config
from app.DB.table_dashboard import DashboardAlert
from router import dashboard_router as dashboard


@pytest.fixture()
def dashboard_client(tmp_path: Path):
    app = create_app()
    engine = create_engine(f"sqlite:///{tmp_path/'dashboard_events.db'}")
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db_config.Base.metadata.create_all(bind=engine)

    def override_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[dashboard.dashboard_db] = override_db

    with TestClient(app) as client:
        yield client, TestingSession

    app.dependency_overrides.clear()
    db_config.Base.metadata.drop_all(bind=engine)


def test_ai_event_route_inserts_dashboard_row(dashboard_client):
    client, TestingSession = dashboard_client
    payload = {
        "event_type": "ALARM",
        "timestamp": 1234567890.0,
        "risk": 12.3,
        "spe": 4.5,
        "top3_t2": [{"sensor": 1, "score": 0.5}],
        "top3_spe": [{"sensor": 2, "score": 0.4}],
        "history": [[1.0, 2.0], [3.0, 4.0]],
        "alarm_code": 101,
        "raw_data": [9.9, 8.8],
        "source": "sensor",
    }

    resp = client.post("/dashboard/events", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["type"] == "ALARM"
    assert body["message"] == "101"
    assert body["isAcknowledged"] is False

    with TestingSession() as session:
        alerts = session.query(DashboardAlert).all()
        assert len(alerts) == 1
        assert alerts[0].sensor_id == 1
        assert alerts[0].message == "101"
