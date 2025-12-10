from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, Column, Integer, String, Text

from .db_config import Base


class DashboardAlert(Base):
    """ORM model mapping the `dashboard` table."""

    __tablename__ = "dashboard"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    sensor_id = Column(Integer, nullable=False, index=True)
    type = Column(String(45))
    mannual = Column(Text)
    message = Column(Text)
    ishandled = Column(Boolean, nullable=False, default=False, server_default="0")


class DashboardViewDTO(BaseModel):
    """DTO exposed to clients (sensor_id excluded)."""

    id: int
    type: Optional[str] = None
    mannual: Optional[str] = None
    message: Optional[str] = None
    ishandled: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


class DashboardHandledUpdateDTO(BaseModel):
    """Payload for toggling the handled flag."""

    ishandled: bool
