from __future__ import annotations

import json
import asyncio
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, Optional
from uuid import uuid4

from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.DB.db_config import session_scope
from app.DB.table_dashboard import DashboardAlert
from app.mcp.queue_models import DeadLetterEntry, ProcessingQueueDTO, QueueEntry
from app.mcp.mcp_client_openai import MCPClientError, OpenAIMCPClient
from app.mcp.mcp_manual import ManualRepository, get_manual_repository
from app.logging_config import get_logger

logger = get_logger(__name__)
MANUAL_FAILURE_TEXT = "매뉴얼 생성 실패"


class MCPQueueError(Exception):
    """Generic queue level error."""


class RemediationResult(BaseModel):
    """LLM 결과를 API/기타 계층에 전달하기 위한 DTO."""

    trace_id: str
    summary: str
    steps: list[Dict[str, Any]]
    confidence: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MCPService:
    """MCP 큐 적재, LLM 호출, 결과 저장을 담당하는 서비스."""

    def __init__(
        self,
        manual_repo: Optional[ManualRepository] = None,
        llm_client: Optional[OpenAIMCPClient] = None,
        max_attempts: int = 3,
    ) -> None:
        self.manual_repo = manual_repo or get_manual_repository()
        self.llm_client = llm_client or OpenAIMCPClient()
        self.max_attempts = max_attempts
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._entries: Dict[int, QueueEntry] = {}
        self._dead_letters: Deque[DeadLetterEntry] = deque(maxlen=200)
        self._worker_task: Optional[asyncio.Task] = None

    async def enqueue(self, payload: Dict[str, Any]) -> ProcessingQueueDTO:
        """큐에 항목을 추가하고 백그라운드 워커를 보장한다."""
        if not payload:
            raise MCPQueueError("비어 있는 payload는 큐에 추가할 수 없습니다.")

        trace_id = payload.get("trace_id") or f"trace-{uuid4().hex}"
        payload["trace_id"] = trace_id
        payload.setdefault("queued_at", datetime.utcnow().isoformat())

        entry_id = uuid4().int & 0x7FFFFFFF
        entry = QueueEntry(id=entry_id, trace_id=trace_id, payload=payload.copy())
        self._entries[entry_id] = entry
        await self._queue.put(entry_id)
        self._ensure_worker_started()
        return ProcessingQueueDTO.model_validate(entry)

    async def process_next(self) -> Optional[RemediationResult]:
        """수동으로 큐에서 다음 항목을 처리한다."""
        entry = self._next_pending_entry()
        if not entry:
            return None
        return await self._run_entry(entry)

    async def process_job(self, queue_id: int) -> Optional[RemediationResult]:
        """특정 큐 ID를 즉시 처리한다."""
        entry = self._entries.get(queue_id)
        if not entry or entry.status not in ("pending", "error"):
            return None
        return await self._run_entry(entry)

    async def get_status(self) -> Dict[str, Any]:
        """큐 및 데드레터 현황을 반환."""
        pending = sum(1 for entry in self._entries.values() if entry.status == "pending")
        processing = sum(1 for entry in self._entries.values() if entry.status == "processing")
        failed = sum(1 for entry in self._entries.values() if entry.status == "error")
        completed = sum(1 for entry in self._entries.values() if entry.status == "done")
        dead_letters = len(self._dead_letters)
        return {
            "pending": pending,
            "processing": processing,
            "error": failed,
            "completed": completed,
            "dead_letters": dead_letters,
        }

    async def _run_entry(self, entry: QueueEntry) -> RemediationResult:
        entry.status = "processing"
        entry.attempt_count += 1
        entry.updated_at = datetime.utcnow()
        payload = entry.payload
        manual_path = self._extract_manual_path(payload)
        try:
            manual_text = self.manual_repo.read_manual(manual_path)
            guidance = await self.llm_client.generate_guidance(payload, manual_text)
        except FileNotFoundError as exc:
            await self._handle_failure(entry, f"메뉴얼 파일 없음: {exc}")
            raise
        except MCPClientError as exc:
            await self._handle_failure(entry, f"LLM 호출 실패: {exc}")
            raise
        except Exception as exc:
            await self._handle_failure(entry, f"예상치 못한 오류: {exc}")
            raise

        remediation = await self._persist_result(entry, payload, guidance)
        return remediation

    async def _handle_failure(
        self,
        entry: QueueEntry,
        error_message: str,
    ) -> None:
        """실패한 항목을 업데이트하고 필요하면 데드레터 큐로 보낸다."""
        entry.status = "error"
        entry.last_error = error_message
        entry.updated_at = datetime.utcnow()

        if entry.attempt_count >= self.max_attempts:
            with session_scope() as session:
                try:
                    self._write_dashboard_manual(
                        session,
                        entry.payload or {},
                        MANUAL_FAILURE_TEXT,
                    )
                except MCPQueueError as exc:
                    logger.error("Failed to mark dashboard manual failure: %s", exc)
            self._dead_letters.append(
                DeadLetterEntry(
                    trace_id=entry.trace_id,
                    payload=entry.payload,
                    error_message=error_message,
                )
            )
        else:
            await self._queue.put(entry.id)

    async def _persist_result(
        self,
        entry: QueueEntry,
        payload: Dict[str, Any],
        guidance: Dict[str, Any],
    ) -> RemediationResult:
        """LLM 결과를 Dashboard 테이블에 저장하고 큐 상태를 완료로 변경."""
        trace_id = payload.get("trace_id", f"trace-{uuid4().hex}")

        steps = guidance.get("steps")
        if not isinstance(steps, list):
            steps = []

        summary = guidance.get("summary", "요약 없음")
        manual_blob = self._render_manual_text(summary, steps)
        with session_scope() as session:
            self._write_dashboard_manual(
                session,
                payload,
                manual_blob,
                overwrite_message=payload.get("message"),
            )

        entry.status = "done"
        entry.last_error = None
        entry.updated_at = datetime.utcnow()

        dto = RemediationResult(
            trace_id=trace_id,
            summary=summary,
            steps=steps,
            confidence=guidance.get("confidence"),
        )
        return dto

    def _next_pending_entry(self) -> Optional[QueueEntry]:
        for entry in sorted(self._entries.values(), key=lambda e: e.created_at):
            if entry.status in ("pending", "error"):
                return entry
        return None

    def _ensure_worker_started(self) -> None:
        if self._worker_task and not self._worker_task.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._worker_task = loop.create_task(self._worker_loop())

    async def _worker_loop(self) -> None:
        while True:
            entry_id = await self._queue.get()
            entry = self._entries.get(entry_id)
            if not entry or entry.status not in ("pending", "error"):
                self._queue.task_done()
                continue
            try:
                await self._run_entry(entry)
            except Exception as exc:  # pragma: no cover - 로그 목적
                logger.exception("Background MCP worker failed for %s: %s", entry.trace_id, exc)
            finally:
                self._queue.task_done()

    def _extract_manual_path(self, payload: Dict[str, Any]) -> str:
        manual_ref = payload.get("manual_reference") or {}
        path = manual_ref.get("path")
        if not path:
            raise MCPQueueError("manual_reference.path 값이 필요합니다.")
        return path

    def _resolve_sensor_id(self, payload: Dict[str, Any]) -> int:
        anomaly = payload.get("anomaly") or {}
        sensor_id = anomaly.get("sensor_id") or payload.get("metadata", {}).get("sensor_id")
        try:
            return int(sensor_id)
        except (TypeError, ValueError):
            return 0

    def _resolve_alert_type(self, payload: Dict[str, Any]) -> str:
        metadata = payload.get("metadata") or {}
        anomaly = payload.get("anomaly") or {}
        return metadata.get("type") or anomaly.get("metric") or "alert"

    def _resolve_message(self, payload: Dict[str, Any]) -> str:
        anomaly = payload.get("anomaly") or {}
        return json.dumps(anomaly, ensure_ascii=False)

    def _render_manual_text(self, summary: str, steps: list[Dict[str, Any]]) -> str:
        lines = [summary]
        for idx, step in enumerate(steps, start=1):
            order = step.get("order") or idx
            action = step.get("action") or ""
            note = step.get("note")
            detail = f"{order}. {action}".strip()
            if note:
                detail = f"{detail} - {note}"
            lines.append(detail)
        return "\n".join(line for line in lines if line)

    def _extract_dashboard_id(self, payload: Dict[str, Any]) -> int:
        metadata = payload.get("metadata") or {}
        candidate = metadata.get("dashboard_id") or metadata.get("alert_id")
        if candidate is None:
            raise MCPQueueError("metadata.dashboard_id 값이 필요합니다.")
        try:
            return int(candidate)
        except (TypeError, ValueError):
            raise MCPQueueError("metadata.dashboard_id 는 정수여야 합니다.")

    def _write_dashboard_manual(
        self,
        session: Session,
        payload: Dict[str, Any],
        manual_text: str,
        overwrite_message: Optional[str] = None,
    ) -> DashboardAlert:
        dashboard_id = self._extract_dashboard_id(payload)
        alert = (
            session.query(DashboardAlert)
            .filter(DashboardAlert.id == dashboard_id)
            .one_or_none()
        )
        if not alert:
            raise MCPQueueError(f"dashboard_id {dashboard_id} 를 찾을 수 없습니다.")

        alert.mannual = manual_text
        if overwrite_message is not None:
            alert.message = overwrite_message
        alert.ishandled = False
        return alert


_mcp_service: Optional[MCPService] = None


def get_mcp_service() -> MCPService:
    """FastAPI dependency provider."""
    global _mcp_service
    if _mcp_service is None:
        _mcp_service = MCPService()
    return _mcp_service
