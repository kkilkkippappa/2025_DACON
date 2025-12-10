from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


@dataclass
class QueueEntry:
    """In-memory representation of a queued MCP task."""

    id: int
    trace_id: str
    payload: Dict[str, Any]
    status: str = "pending"
    attempt_count: int = 0
    last_error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DeadLetterEntry:
    trace_id: str
    payload: Dict[str, Any]
    error_message: str
    failed_at: datetime = field(default_factory=datetime.utcnow)


class ProcessingQueueDTO(BaseModel):
    id: Optional[int] = None
    trace_id: str
    payload: Dict[str, Any]
    status: str = "pending"
    attempt_count: int = 0
    last_error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
