import sys
from pathlib import Path
import types

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

sklearn_stub = types.ModuleType("sklearn")
sklearn_decomp = types.ModuleType("sklearn.decomposition")
sklearn_preproc = types.ModuleType("sklearn.preprocessing")
sklearn_decomp.PCA = type("PCA", (), {})
sklearn_preproc.StandardScaler = type("StandardScaler", (), {})
sys.modules.setdefault("sklearn", sklearn_stub)
sys.modules.setdefault("sklearn.decomposition", sklearn_decomp)
sys.modules.setdefault("sklearn.preprocessing", sklearn_preproc)

from AI import ai  # noqa: E402


class DummyResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_ai_pipeline_enqueues_mcp(monkeypatch):
    captured = []

    def fake_post(url, json=None, timeout=None):
        captured.append((url, json))
        if "dashboard/events" in url:
            return DummyResponse(201, {"id": 42})
        return DummyResponse(200, {})

    monkeypatch.setattr(ai.requests, "post", fake_post)

    event = {
        "event_type": "WARNING",
        "timestamp": 0,
        "risk": 1.0,
        "spe": 2.0,
        "top3_t2": [],
        "top3_spe": [],
        "history": [],
        "alarm_code": "A-1",
        "raw_data": [],
        "source": "sensor",
    }

    resp = ai.send_event_to_dashboard(event)
    assert resp == {"id": 42}
    ai.send_event_to_mcp(42, event)

    assert captured[0][0].endswith("/dashboard/events")
    assert captured[1][0].endswith("/mcp/enqueue")
    assert captured[1][1]["metadata"]["dashboard_id"] == 42
