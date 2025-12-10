from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.DB.db_config import get_db_for_table
from app.DB.use_dashboard import (
    DashboardHandledUpdateDTO,
    fetch_dashboard_alerts,
    update_dashboard_alert_handled,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/")
def dashboard_health():
    """Basic readiness endpoint for dashboard routes."""
    return {"message": "dashboard routes ready"}


@router.get("/alerts")
def list_dashboard_alerts(db: Session = Depends(get_db_for_table("dashboard"))):
    """Return dashboard entries without exposing sensor_id."""
    try:
        return fetch_dashboard_alerts(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard entries: {exc.__class__.__name__}",
        ) from exc


@router.patch("/alerts/{alert_id}/handled")
def toggle_alert_handled(
    alert_id: int,
    payload: DashboardHandledUpdateDTO,
    db: Session = Depends(get_db_for_table("dashboard")),
):
    """Set the handled flag (True/False) for a specific dashboard row."""
    try:
        updated = update_dashboard_alert_handled(db, alert_id, payload.isAcknowledged)
    except SQLAlchemyError as exc:
        db.rollback()
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
