from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/mcp", tags=["mcp"])

class MCPRequest(BaseModel):
    action: str
    data: dict

class MCPResponse(BaseModel):
    status: str
    result: dict

@router.post("/call")
async def mcp_call(request: MCPRequest):
    """MCP 서버와 통신"""
    try:
        # MCP 서비스 호출
        result = await mcp_service.execute(request.action, request.data)
        return MCPResponse(status="success", result=result)
    except Exception as e:
        return MCPResponse(status="error", result={"error": str(e)})

@router.get("/status")
async def mcp_status():
    """MCP 서버 상태 확인"""
    return {"status": "connected", "server": "mcp_server"}

@router.post("/process")
async def mcp_process(request: MCPRequest):
    """MCP로 데이터 처리"""
    result = await mcp_service.process(request.data)
    return {"processed": result}
