from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

MANUAL_BASE_PATH = Path(os.getenv("MCP_MANUAL_BASE", "docs/manuals"))
MANUAL_BASE_PATH.mkdir(parents=True, exist_ok=True)

mcp = FastMCP("manual_mcp")


class ManualRepository:
    """로컬 메뉴얼 파일을 읽고 간단히 필터링한다."""

    def __init__(self, base_path: Path = MANUAL_BASE_PATH) -> None:
        self.base_path = base_path

    def resolve_path(self, manual_path: str) -> Path:
        path = Path(manual_path)
        if not path.is_absolute():
            path = self.base_path / path
        return path

    def read_manual(self, manual_path: str) -> str:
        resolved = self.resolve_path(manual_path)
        if not resolved.exists():
            raise FileNotFoundError(f"메뉴얼 {resolved} 을(를) 찾을 수 없습니다.")

        if resolved.is_dir():
            contents = []
            for candidate in resolved.glob("**/*"):
                if candidate.is_file():
                    contents.append(candidate.read_text(encoding="utf-8", errors="ignore"))
            return "\n".join(contents)
        return resolved.read_text(encoding="utf-8", errors="ignore")

    def extract_snippets(self, manual_path: str, tags: Optional[List[str]] = None) -> Dict[str, str]:
        tags = tags or []
        manual_text = self.read_manual(manual_path)
        if not tags:
            return {"full": manual_text}

        lowered = manual_text.lower()
        snippets = {}
        for tag in tags:
            tag_lower = tag.lower()
            idx = lowered.find(tag_lower)
            if idx == -1:
                continue
            start = max(idx - 120, 0)
            end = min(idx + 120, len(manual_text))
            snippets[tag] = manual_text[start:end]

        if not snippets:
            snippets["full"] = manual_text[:5000]
        return snippets


_manual_repository: Optional[ManualRepository] = None


def get_manual_repository() -> ManualRepository:
    global _manual_repository
    if _manual_repository is None:
        _manual_repository = ManualRepository()
    return _manual_repository


@mcp.tool()
def get_person_mannual(manual_path: str, tags: Optional[List[str]] = None) -> Dict[str, str]:
    """fastmcp 툴로 메뉴얼을 노출한다."""
    repo = get_manual_repository()
    try:
        return repo.extract_snippets(manual_path, tags)
    except FileNotFoundError as exc:
        return {"error": f"Menu얼 조회 실패: {exc}"}
    except Exception as exc:  # pragma: no cover - 범용 안전장치
        return {"error": f"알 수 없는 오류: {exc}"}


# Resources require fully qualified URIs, so use a custom manual:// scheme to satisfy Pydantic.
@mcp.resource("manual://manuals")
def list_manuals() -> Dict[str, List[str]]:
    """메뉴얼 디렉터리 구조를 반환한다."""
    repo = get_manual_repository()
    manuals = []
    for file in repo.base_path.glob("**/*"):
        if file.is_file():
            manuals.append(str(file.relative_to(repo.base_path)))
    return {"manuals": manuals}


if __name__ == "__main__":
    try:
        mcp.run()
    except KeyboardInterrupt:
        print("MCP 서버가 중단되었습니다.")
