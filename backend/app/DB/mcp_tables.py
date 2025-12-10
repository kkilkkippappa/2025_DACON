from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, Column, DateTime, Integer, String, Text

from .db_config import Base


class ProcessingQueueTable(Base):
    """메인 큐에 쌓이는 MCP 작업 항목."""

    __tablename__ = "mcp_processing_queue"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trace_id = Column(String(64), nullable=False, index=True, unique=True)
    payload = Column(JSON, nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class DeadLetterQueueTable(Base):
    """재시도 실패한 메시지를 모아두는 데드레터 큐 테이블."""

    __tablename__ = "mcp_dead_letter_queue"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trace_id = Column(String(64), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    error_message = Column(Text, nullable=False)
    failed_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ProcessingQueueDTO(BaseModel):
    """API/서비스 계층에서 사용할 DTO."""

    id: Optional[int] = None
    trace_id: str
    payload: Dict[str, Any]
    status: str = "pending"
    attempt_count: int = 0
    last_error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
