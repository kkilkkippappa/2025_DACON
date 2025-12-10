from __future__ import annotations

from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from .table_dashboard import DashboardAlert


class DashboardHandledUpdateDTO(BaseModel):
    """Payload for toggling the handled flag."""

    isAcknowledged: bool = Field(
        default=False,
        validation_alias=AliasChoices("isAcknowledged", "ishandled"),
    )

    model_config = ConfigDict(populate_by_name=True)


class DashboardAlertResponse(BaseModel):
    """View model tailored for the frontend dashboard."""

    id: str
    occurredAt: str
    type: str
    message: str
    recommendation: str
    isAcknowledged: bool

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_dashboard(cls, alert: DashboardAlert) -> "DashboardAlertResponse":
        return cls(
            id=str(alert.id),
            occurredAt=_resolve_occurred_at(alert),
            type=alert.type or "warning",
            message=alert.message or "",
            recommendation=alert.mannual or "",
            isAcknowledged=bool(alert.ishandled),
        )


def fetch_dashboard_alerts(db: Session) -> list[DashboardAlertResponse]:
    """Fetch dashboard alerts ordered by newest first."""
    alerts = db.query(DashboardAlert).order_by(DashboardAlert.id.desc()).all()
    return [DashboardAlertResponse.from_dashboard(alert) for alert in alerts]


def update_dashboard_alert_handled(
    db: Session,
    alert_id: int,
    acknowledged: bool,
) -> DashboardAlertResponse | None:
    """Toggle the handled flag for a dashboard alert."""
    alert = db.query(DashboardAlert).filter(DashboardAlert.id == alert_id).first()
    if not alert:
        return None

    alert.ishandled = acknowledged
    db.commit()
    db.refresh(alert)
    return DashboardAlertResponse.from_dashboard(alert)


def _resolve_occurred_at(alert: DashboardAlert) -> str:
    """Attempt to expose a human-readable timestamp placeholder."""

    candidate = getattr(alert, "occurred_at", None)
    if isinstance(candidate, datetime):
        return candidate.strftime("%Y-%m-%d %H:%M:%S")
    return f"Sensor #{alert.sensor_id}"
