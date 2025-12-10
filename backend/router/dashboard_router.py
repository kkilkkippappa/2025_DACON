from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.DB.db_config import get_db_for_table
from app.DB.table_dashboard import DashboardAlert
from app.DB.use_dashboard import (
    DashboardHandledUpdateDTO,
    DashboardAlertResponse,
    DashboardEventCreateDTO,
    fetch_dashboard_alerts,
    create_dashboard_alert,
    update_dashboard_alert_handled,
)
from app.logging_config import get_logger
from app.services.mcp_service import MCPQueueError, MCPService, get_mcp_service

logger = get_logger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/")
def dashboard_health():
    """Basic readiness endpoint for dashboard routes."""
    return {"message": "dashboard routes ready"}


dashboard_db = get_db_for_table("dashboard", schema_name="sensor_data")


@router.get("/send")
def list_dashboard_alerts(db: Session = Depends(dashboard_db)):
    """Return dashboard entries without exposing sensor_id."""
    try:
        return fetch_dashboard_alerts(db)
    except SQLAlchemyError as exc:
        logger.exception("Failed to fetch dashboard entries")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard entries: {exc.__class__.__name__} -> {exc}",
        ) from exc


@router.patch("/send/{alert_id}/handled")
def toggle_alert_handled(
    alert_id: int,
    payload: DashboardHandledUpdateDTO,
    db: Session = Depends(dashboard_db),
):
    """Set the handled flag (True/False) for a specific dashboard row."""
    try:
        updated = update_dashboard_alert_handled(db, alert_id, payload.isAcknowledged)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to update dashboard row %s", alert_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update dashboard row: {exc.__class__.__name__}",
        ) from exc

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard row not found",
        )

    return updated


class DashboardLLMRequest(BaseModel):
    id: int


class DashboardLLMResponse(BaseModel):
    trace_id: str
    summary: str
    steps: list[dict]
    confidence: str | None = None


DEFAULT_TEST_MANUAL_PATH = os.getenv("MANUAL_PATH")
DEFAULT_TEST_MANUAL_DIR = os.getenv("MANUAL_DIR", "docs/manuals")


def _resolve_manual_path(alert: DashboardAlert) -> str:
    if DEFAULT_TEST_MANUAL_PATH:
        return DEFAULT_TEST_MANUAL_PATH
    type_slug = (alert.type or "default").lower()
    manual_path = Path(DEFAULT_TEST_MANUAL_DIR) / f"{type_slug}.txt"
    try:
        return str(manual_path.resolve())
    except FileNotFoundError:
        return str(manual_path)


@router.post("/test/LLM", response_model=DashboardLLMResponse)
async def trigger_dashboard_llm(
    payload: DashboardLLMRequest,
    db: Session = Depends(dashboard_db),
    mcp_service: MCPService = Depends(get_mcp_service),
) -> DashboardLLMResponse:
    alert = db.query(DashboardAlert).filter(DashboardAlert.id == payload.id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard row not found",
        )

    manual_path = _resolve_manual_path(alert)
    trace_id = f"dashboard-test-{alert.id}-{uuid4().hex}"
    queue_payload: Dict[str, Any] = {
        "trace_id": trace_id,
        "message": alert.message or "",
        "anomaly": {"sensor_id": alert.sensor_id, "type": alert.type},
        "manual_reference": {"path": manual_path},
        "metadata": {
            "dashboard_id": alert.id,
            "event_type": (alert.type or "WARNING").upper(),
        },
    }

    try:
        entry = await mcp_service.enqueue(queue_payload)
        result = await mcp_service.process_job(entry.id or 0)
    except MCPQueueError as exc:
        logger.exception("Failed to run MCP test for dashboard %s", alert.id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except FileNotFoundError as exc:
        logger.exception("Manual file not found for dashboard %s", alert.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Manual file missing: {exc}",
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("Unexpected error running MCP test for dashboard %s", alert.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run MCP test: {exc.__class__.__name__}",
        )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP job not found or already processed",
        )

    return DashboardLLMResponse(
        trace_id=result.trace_id,
        summary=result.summary,
        steps=result.steps,
        confidence=result.confidence,
    )


class AIEventPayload(BaseModel):
    event_type: str
    timestamp: float
    risk: float
    spe: float
    top3_t2: List[Dict[str, Any]]
    top3_spe: List[Dict[str, Any]]
    history: List[List[float]]
    alarm_code: str | int
    raw_data: List[float]
    source: str


@router.post("/events", response_model=DashboardAlertResponse, status_code=status.HTTP_201_CREATED)
def ingest_ai_event(payload: AIEventPayload, db: Session = Depends(dashboard_db)):
    """Accept AI sensor events and persist them as dashboard alerts."""
    sensor_id = 1  # 실제 sensor_id 가 아직 AI 이벤트에 포함되지 않으므로, DB FK 제약을 만족시키기 위해 sensor 테이블에 존재하는 기본 ID(예: 1번 센서)를 임시로 사용합니다. 추후 이벤트에서 실제 sensor_id 를 전달하면 이 값을 교체하세요.
    try:
        create_payload = DashboardEventCreateDTO(
            event_type=payload.event_type,
            alarm_code=str(payload.alarm_code),
            sensor_id=sensor_id,
        )
        return create_dashboard_alert(db, create_payload)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to insert AI event into dashboard table")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store event: {exc.__class__.__name__}",
        ) from exc
