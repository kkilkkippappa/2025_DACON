from __future__ import annotations

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
