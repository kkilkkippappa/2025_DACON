from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.DB.db_config import session_scope
from app.DB.mcp_tables import (
    DeadLetterQueueTable,
    ProcessingQueueDTO,
    ProcessingQueueTable,
)
from app.DB.table_dashboard import DashboardAlert
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

    async def enqueue(self, payload: Dict[str, Any]) -> ProcessingQueueDTO:
        """processing_queue 테이블에 항목을 추가한다."""
        if not payload:
            raise MCPQueueError("비어 있는 payload는 큐에 추가할 수 없습니다.")

        trace_id = payload.get("trace_id") or f"trace-{uuid4().hex}"
        payload["trace_id"] = trace_id
        payload.setdefault("queued_at", datetime.utcnow().isoformat())

        with session_scope() as session:
            existing = (
                session.query(ProcessingQueueTable)
                .filter(ProcessingQueueTable.trace_id == trace_id)
                .one_or_none()
            )
            if existing:
                raise MCPQueueError(f"{trace_id} 는 이미 큐에 존재합니다.")

            entry = ProcessingQueueTable(
                trace_id=trace_id,
                payload=payload,
                status="pending",
                attempt_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(entry)
            session.flush()
            dto = ProcessingQueueDTO.model_validate(entry)
            return dto

    async def process_next(self) -> Optional[RemediationResult]:
        """큐에서 다음 항목을 꺼내 LLM까지 처리한다."""
        with session_scope() as session:
            record = (
                session.query(ProcessingQueueTable)
                .filter(ProcessingQueueTable.status.in_(["pending", "error"]))
                .order_by(ProcessingQueueTable.created_at)
                .first()
            )
            if not record:
                return None

            job_id, payload, manual_path = self._prepare_job_record(session, record)

        return await self._execute_job(job_id, payload, manual_path)

    async def process_job(self, queue_id: int) -> Optional[RemediationResult]:
        """특정 큐 ID를 즉시 처리한다."""
        with session_scope() as session:
            record = session.get(ProcessingQueueTable, queue_id)
            if not record or record.status not in ("pending", "error"):
                return None
            job_id, payload, manual_path = self._prepare_job_record(session, record)

        return await self._execute_job(job_id, payload, manual_path)

    async def get_status(self) -> Dict[str, Any]:
        """큐 및 데드레터 현황을 반환."""
        with session_scope() as session:
            pending = (
                session.query(func.count(ProcessingQueueTable.id))
                .filter(ProcessingQueueTable.status == "pending")
                .scalar()
            )
            processing = (
                session.query(func.count(ProcessingQueueTable.id))
                .filter(ProcessingQueueTable.status == "processing")
                .scalar()
            )
            failed = (
                session.query(func.count(ProcessingQueueTable.id))
                .filter(ProcessingQueueTable.status == "error")
                .scalar()
            )
            completed = (
                session.query(func.count(ProcessingQueueTable.id))
                .filter(ProcessingQueueTable.status == "done")
                .scalar()
            )
            dead_letters = session.query(func.count(DeadLetterQueueTable.id)).scalar()

        return {
            "pending": pending or 0,
            "processing": processing or 0,
            "error": failed or 0,
            "completed": completed or 0,
            "dead_letters": dead_letters or 0,
        }

    def _prepare_job_record(
        self,
        session: Session,
        record: ProcessingQueueTable,
    ) -> tuple[int, Dict[str, Any], str]:
        payload = record.payload or {}
        manual_path = self._extract_manual_path(payload)

        record.status = "processing"
        record.attempt_count += 1
        record.updated_at = datetime.utcnow()
        session.flush()

        return record.id, payload, manual_path

    async def _execute_job(
        self,
        job_id: int,
        payload: Dict[str, Any],
        manual_path: str,
    ) -> RemediationResult:
        try:
            manual_text = self.manual_repo.read_manual(manual_path)
            guidance = await self.llm_client.generate_guidance(payload, manual_text)
        except FileNotFoundError as exc:
            await self._handle_failure(job_id, payload, f"메뉴얼 파일 없음: {exc}")
            raise
        except MCPClientError as exc:
            await self._handle_failure(job_id, payload, f"LLM 호출 실패: {exc}")
            raise
        except Exception as exc:
            await self._handle_failure(job_id, payload, f"예상치 못한 오류: {exc}")
            raise

        remediation = await self._persist_result(job_id, payload, guidance)
        return remediation

    async def _handle_failure(
        self,
        job_id: Optional[int],
        payload: Dict[str, Any],
        error_message: str,
    ) -> None:
        """실패한 항목을 업데이트하고 필요하면 데드레터 큐로 보낸다."""
        if job_id is None:
            logger.error("job_id 없음: %s", error_message)
            return

        with session_scope() as session:
            record = session.get(ProcessingQueueTable, job_id)
            if not record:
                logger.error("기록되지 않은 job_id %s", job_id)
                return

            record.status = "error"
            record.last_error = error_message
            record.updated_at = datetime.utcnow()
            attempt_count = record.attempt_count
            session.flush()

            if attempt_count >= self.max_attempts:
                try:
                    self._write_dashboard_manual(
                        session,
                        record.payload or {},
                        MANUAL_FAILURE_TEXT,
                    )
                except MCPQueueError as exc:
                    logger.error("Failed to mark dashboard manual failure: %s", exc)
                dead_letter = DeadLetterQueueTable(
                    trace_id=record.trace_id,
                    payload=record.payload,
                    error_message=error_message,
                    failed_at=datetime.utcnow(),
                )
                session.add(dead_letter)
                session.delete(record)
                logger.error(
                    "Job %s 이(가) %s회 실패하여 데드레터 큐로 이동했습니다.", job_id, attempt_count
                )

    async def _persist_result(
        self,
        job_id: int,
        payload: Dict[str, Any],
        guidance: Dict[str, Any],
    ) -> RemediationResult:
        """LLM 결과를 Dashboard 테이블에 저장하고 큐 상태를 완료로 변경."""
        trace_id = payload.get("trace_id", f"trace-{uuid4().hex}")

        with session_scope() as session:
            record = session.get(ProcessingQueueTable, job_id)
            if not record:
                raise MCPQueueError(f"job_id {job_id} 를 찾을 수 없습니다.")

            record.status = "done"
            record.last_error = None
            record.updated_at = datetime.utcnow()

            steps = guidance.get("steps")
            if not isinstance(steps, list):
                steps = []

            summary = guidance.get("summary", "요약 없음")
            manual_blob = self._render_manual_text(summary, steps)
            self._write_dashboard_manual(
                session,
                payload,
                manual_blob,
                overwrite_message=payload.get("message"),
            )
            session.flush()

            dto = RemediationResult(
                trace_id=trace_id,
                summary=summary,
                steps=steps,
                confidence=guidance.get("confidence"),
            )
            return dto

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
