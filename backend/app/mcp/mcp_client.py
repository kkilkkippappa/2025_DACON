from __future__ import annotations

import asyncio
from typing import List

from fastmcp import Client, FastMCPClientError


client = Client("mcp_manual.py")


async def main(manual_path: str, tags: List[str] | None = None) -> None:
    try:
        async with client:
            print(f"Client connected: {client.is_connected()}")
            result = await client.call_tool(
                "get_person_mannual",
                manual_path=manual_path,
                tags=tags or [],
            )
            print("Manual snippet:", result)
    except FastMCPClientError as exc:
        print(f"MCP 클라이언트 오류: {exc}")
    except Exception as exc:  # pragma: no cover
        print(f"예상치 못한 오류: {exc}")


if __name__ == "__main__":
    try:
        asyncio.run(main("default_manual.txt"))
    except KeyboardInterrupt:
        print("클라이언트가 중단되었습니다.")
    finally:
        client.close()
