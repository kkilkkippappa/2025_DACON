from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.mcp_service import MCPQueueError, MCPService, get_mcp_service

router = APIRouter(prefix="/mcp", tags=["mcp"])


class ManualReference(BaseModel):
    path: str = Field(..., description="로컬 메뉴얼 파일 혹은 디렉터리 경로")
    tags: list[str] = Field(default_factory=list)


class MCPQueuePayload(BaseModel):
    trace_id: str | None = Field(default=None, description="요청 추적 ID")
    anomaly: dict = Field(default_factory=dict)
    ai_error: dict = Field(default_factory=dict)
    manual_reference: ManualReference
    metadata: dict = Field(default_factory=dict)


class QueueResponse(BaseModel):
    queue_id: int
    trace_id: str
    status: str


class RemediationResponse(BaseModel):
    trace_id: str
    summary: str
    steps: list[dict]
    confidence: str | None = None


@router.post("/enqueue", response_model=QueueResponse)
async def enqueue_job(
    payload: MCPQueuePayload,
    mcp_service: MCPService = Depends(get_mcp_service),
) -> QueueResponse:
    """큐에 MCP 작업을 적재한다."""
    try:
        entry = await mcp_service.enqueue(payload.model_dump())
    except MCPQueueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return QueueResponse(queue_id=entry.id or 0, trace_id=entry.trace_id, status=entry.status)


@router.post("/process-next", response_model=RemediationResponse)
async def process_next_job(
    mcp_service: MCPService = Depends(get_mcp_service),
) -> RemediationResponse:
    """큐에서 다음 작업을 꺼내 처리한다."""
    result = await mcp_service.process_next()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="대기 중인 작업이 없습니다.")

    return RemediationResponse(
        trace_id=result.trace_id,
        summary=result.summary,
        steps=result.steps or [],
        confidence=result.confidence,
    )


@router.get("/status")
async def mcp_status(
    mcp_service: MCPService = Depends(get_mcp_service),
) -> dict:
    """큐/데드레터 현황을 반환한다."""
    return await mcp_service.get_status()
