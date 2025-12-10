from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.DB.db_config import get_db
from app.DB.table_dashboard import (
    DashboardAlert,
    DashboardHandledUpdateDTO,
    DashboardViewDTO,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/")
def dashboard_health():
    """Basic readiness endpoint for dashboard routes."""
    return {"message": "dashboard routes ready"}


@router.get("/alerts")
def list_dashboard_alerts(db: Session = Depends(get_db)):
    """Return dashboard entries without exposing sensor_id."""
    try:
        alerts = db.query(DashboardAlert).order_by(DashboardAlert.id.desc()).all()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard entries: {exc.__class__.__name__}",
        ) from exc
    return [DashboardViewDTO.model_validate(alert) for alert in alerts]


@router.patch("/alerts/{alert_id}/handled")
def toggle_alert_handled(
    alert_id: int,
    payload: DashboardHandledUpdateDTO,
    db: Session = Depends(get_db),
):
    """Set the handled flag (True/False) for a specific dashboard row."""
    alert = db.query(DashboardAlert).filter(DashboardAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard row not found")

    alert.ishandled = payload.ishandled
    try:
        db.commit()
        db.refresh(alert)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update dashboard row: {exc.__class__.__name__}",
        ) from exc

    return DashboardViewDTO.model_validate(alert)
