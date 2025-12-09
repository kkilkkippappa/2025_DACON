from typing import Any, Dict


class MCPService:
    """MCP 연동용 서비스 (현재는 스텁 구현)."""

    async def fetch_manual(self, prompt: str) -> Dict[str, Any]:
        # TODO: 실제 MCP 클라이언트 연동 필요
        return {
            "prompt": prompt,
            "content": "MCP 연동 스텁: 실제 MCP 호출로 교체하세요.",
        }


def get_mcp_service() -> MCPService:
    return MCPService()





