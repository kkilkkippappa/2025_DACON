from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, Integer, Numeric

from .db_config import Base


class SensorTable(Base):
    """SQLAlchemy model reflecting the `sensor` table definition."""

    __tablename__ = "sensor"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    date_time = Column(DateTime, nullable=False, index=True)

    XMEAS_1 = Column(Numeric(25, 20))
    XMEAS_2 = Column(Numeric(25, 20))
    XMEAS_3 = Column(Numeric(25, 20))
    XMEAS_4 = Column(Numeric(25, 20))
    XMEAS_5 = Column(Numeric(25, 20))
    XMEAS_6 = Column(Numeric(25, 20))
    XMEAS_7 = Column(Numeric(25, 20))
    XMEAS_8 = Column(Numeric(25, 20))
    XMEAS_9 = Column(Numeric(25, 20))
    XMEAS_10 = Column(Numeric(25, 20))
    XMEAS_11 = Column(Numeric(25, 20))
    XMEAS_12 = Column(Numeric(25, 20))
    XMEAS_13 = Column(Numeric(25, 20))
    XMEAS_14 = Column(Numeric(25, 20))
    XMEAS_15 = Column(Numeric(25, 20))
    XMEAS_16 = Column(Numeric(25, 20))
    XMEAS_17 = Column(Numeric(25, 20))
    XMEAS_18 = Column(Numeric(25, 20))
    XMEAS_19 = Column(Numeric(25, 20))
    XMEAS_20 = Column(Numeric(25, 20))
    XMEAS_21 = Column(Numeric(25, 20))
    XMEAS_22 = Column(Numeric(25, 20))
    XMEAS_23 = Column(Numeric(25, 20))
    XMEAS_24 = Column(Numeric(25, 20))
    XMEAS_25 = Column(Numeric(25, 20))
    XMEAS_26 = Column(Numeric(25, 20))
    XMEAS_27 = Column(Numeric(25, 20))
    XMEAS_28 = Column(Numeric(25, 20))
    XMEAS_29 = Column(Numeric(25, 20))
    XMEAS_30 = Column(Numeric(25, 20))
    XMEAS_31 = Column(Numeric(25, 20))
    XMEAS_32 = Column(Numeric(25, 20))
    XMEAS_33 = Column(Numeric(25, 20))
    XMEAS_34 = Column(Numeric(25, 20))
    XMEAS_35 = Column(Numeric(25, 20))
    XMEAS_36 = Column(Numeric(25, 20))
    XMEAS_37 = Column(Numeric(25, 20))
    XMEAS_38 = Column(Numeric(25, 20))
    XMEAS_39 = Column(Numeric(25, 20))
    XMEAS_40 = Column(Numeric(25, 20))
    XMEAS_41 = Column(Numeric(25, 20))

    XMV_1 = Column(Numeric(25, 20))
    XMV_2 = Column(Numeric(25, 20))
    XMV_3 = Column(Numeric(25, 20))
    XMV_4 = Column(Numeric(25, 20))
    XMV_5 = Column(Numeric(25, 20))
    XMV_6 = Column(Numeric(25, 20))
    XMV_7 = Column(Numeric(25, 20))
    XMV_8 = Column(Numeric(25, 20))
    XMV_9 = Column(Numeric(25, 20))
    XMV_10 = Column(Numeric(25, 20))
    XMV_11 = Column(Numeric(25, 20))

    status = Column(Integer)


class SensorDTO(BaseModel):
    """DTO used when creating or returning sensor records."""

    id: Optional[int] = None
    date_time: datetime

    XMEAS_1: Optional[Decimal] = None
    XMEAS_2: Optional[Decimal] = None
    XMEAS_3: Optional[Decimal] = None
    XMEAS_4: Optional[Decimal] = None
    XMEAS_5: Optional[Decimal] = None
    XMEAS_6: Optional[Decimal] = None
    XMEAS_7: Optional[Decimal] = None
    XMEAS_8: Optional[Decimal] = None
    XMEAS_9: Optional[Decimal] = None
    XMEAS_10: Optional[Decimal] = None
    XMEAS_11: Optional[Decimal] = None
    XMEAS_12: Optional[Decimal] = None
    XMEAS_13: Optional[Decimal] = None
    XMEAS_14: Optional[Decimal] = None
    XMEAS_15: Optional[Decimal] = None
    XMEAS_16: Optional[Decimal] = None
    XMEAS_17: Optional[Decimal] = None
    XMEAS_18: Optional[Decimal] = None
    XMEAS_19: Optional[Decimal] = None
    XMEAS_20: Optional[Decimal] = None
    XMEAS_21: Optional[Decimal] = None
    XMEAS_22: Optional[Decimal] = None
    XMEAS_23: Optional[Decimal] = None
    XMEAS_24: Optional[Decimal] = None
    XMEAS_25: Optional[Decimal] = None
    XMEAS_26: Optional[Decimal] = None
    XMEAS_27: Optional[Decimal] = None
    XMEAS_28: Optional[Decimal] = None
    XMEAS_29: Optional[Decimal] = None
    XMEAS_30: Optional[Decimal] = None
    XMEAS_31: Optional[Decimal] = None
    XMEAS_32: Optional[Decimal] = None
    XMEAS_33: Optional[Decimal] = None
    XMEAS_34: Optional[Decimal] = None
    XMEAS_35: Optional[Decimal] = None
    XMEAS_36: Optional[Decimal] = None
    XMEAS_37: Optional[Decimal] = None
    XMEAS_38: Optional[Decimal] = None
    XMEAS_39: Optional[Decimal] = None
    XMEAS_40: Optional[Decimal] = None
    XMEAS_41: Optional[Decimal] = None

    XMV_1: Optional[Decimal] = None
    XMV_2: Optional[Decimal] = None
    XMV_3: Optional[Decimal] = None
    XMV_4: Optional[Decimal] = None
    XMV_5: Optional[Decimal] = None
    XMV_6: Optional[Decimal] = None
    XMV_7: Optional[Decimal] = None
    XMV_8: Optional[Decimal] = None
    XMV_9: Optional[Decimal] = None
    XMV_10: Optional[Decimal] = None
    XMV_11: Optional[Decimal] = None

    status: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
