from __future__ import annotations

import os
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

MANUAL_BASE_PATH = Path(
    os.getenv("MANUAL_DIR")
    or os.getenv("MCP_MANUAL_BASE", "docs/manuals")
)
MANUAL_BASE_PATH.mkdir(parents=True, exist_ok=True)

mcp = FastMCP("manual_mcp")


class ManualRepository:
    """로컬 매뉴얼을 조회하고 단순 가공할 레이어."""

    def __init__(self, base_path: Path = MANUAL_BASE_PATH, sensor_case_filename: str = "sensor_error_case.txt") -> None:
        self.base_path = base_path
        self.sensor_case_filename = sensor_case_filename
        self._sensor_cases: Optional[Dict[str, str]] = None

    def resolve_path(self, manual_path: str) -> Path:
        path = Path(manual_path)
        if not path.is_absolute():
            path = self.base_path / path
        return path

    def read_manual(self, manual_path: str) -> str:
        resolved = self.resolve_path(manual_path)
        if not resolved.exists():
            raise FileNotFoundError(f"매뉴얼 {resolved} 을(를) 찾을 수 없습니다.")

        if resolved.is_dir():
            contents = [self._read_file(candidate) for candidate in self._iter_manual_files(resolved)]
            return "\n".join(contents)
        return self._read_file(resolved)

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

    def render_sensor_context(self, sensor_tokens: Optional[List[str]] = None) -> str:
        tokens = [token for token in (sensor_tokens or []) if token]
        if not tokens:
            return ""
        cases = self._load_sensor_cases()
        if not cases:
            return ""

        used_keys: List[str] = []
        lines: List[str] = []
        for token in tokens:
            key = self._match_case_key(token, cases)
            if not key or key in used_keys:
                continue
            used_keys.append(key)
            block = cases.get(key, "").strip()
            if not block:
                continue
            lines.append(f"- {key}:")
            lines.append(block)
        if not lines:
            return ""
        return "Sensor specific guidance\n" + "\n".join(lines)

    def _iter_manual_files(self, directory: Path) -> List[Path]:
        files: List[Path] = []
        for candidate in directory.glob("**/*"):
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in {".txt", ".docx"}:
                continue
            if candidate.name == self.sensor_case_filename:
                continue
            files.append(candidate)
        return sorted(files)

    def _read_file(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".docx":
            return self._read_docx(path)
        return path.read_text(encoding="utf-8", errors="ignore")

    def _read_docx(self, path: Path) -> str:
        try:
            with zipfile.ZipFile(path) as archive:
                xml_bytes = archive.read("word/document.xml")
        except (KeyError, FileNotFoundError, zipfile.BadZipFile):
            return ""
        root = ET.fromstring(xml_bytes)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: List[str] = []
        for paragraph in root.findall(".//w:p", ns):
            texts = [node.text for node in paragraph.findall(".//w:t", ns) if node.text]
            if texts:
                paragraphs.append("".join(texts))
        return "\n".join(paragraphs)

    def _load_sensor_cases(self) -> Dict[str, str]:
        if self._sensor_cases is not None:
            return self._sensor_cases
        sensor_file = self.base_path / self.sensor_case_filename
        if not sensor_file.exists():
            self._sensor_cases = {}
            return self._sensor_cases
        raw = sensor_file.read_text(encoding="utf-8", errors="ignore")
        self._sensor_cases = self._parse_sensor_case_text(raw)
        return self._sensor_cases

    def _parse_sensor_case_text(self, raw_text: str) -> Dict[str, str]:
        sections: Dict[str, str] = {}
        current_key: Optional[str] = None
        buffer: List[str] = []

        def flush() -> None:
            nonlocal current_key, buffer
            if current_key and buffer:
                sections[current_key] = "\n".join(buffer).strip()
            buffer = []

        for line in raw_text.splitlines():
            stripped = line.strip()
            if not stripped:
                flush()
                current_key = None
                continue
            if self._is_section_header(stripped):
                flush()
                current_key = stripped
            else:
                buffer.append(stripped)
        flush()
        return sections

    def _is_section_header(self, line: str) -> bool:
        return bool(
            re.match(r"^(XMEAS|XMV)\s*\d+", line, re.IGNORECASE)
            or re.match(r"^[A-Z]\s*:", line)
        )

    def _normalize_token(self, token: str) -> str:
        cleaned = re.sub(r"\s+", " ", token.upper())
        return cleaned.strip()

    def _match_case_key(self, token: str, cases: Dict[str, str]) -> Optional[str]:
        normalized = self._normalize_token(token)
        numeric = "".join(ch for ch in normalized if ch.isdigit())
        for key in cases.keys():
            key_norm = self._normalize_token(key)
            if normalized and normalized in key_norm:
                return key
            if numeric and numeric in key_norm:
                return key
        return None


_manual_repository: Optional[ManualRepository] = None


def get_manual_repository() -> ManualRepository:
    global _manual_repository
    if _manual_repository is None:
        _manual_repository = ManualRepository()
    return _manual_repository


@mcp.tool()
def get_person_mannual(manual_path: str, tags: Optional[List[str]] = None) -> Dict[str, str]:
    """fastmcp 경로로 매뉴얼을 호출한다."""
    repo = get_manual_repository()
    try:
        return repo.extract_snippets(manual_path, tags)
    except FileNotFoundError as exc:
        return {"error": f"Menu얼 조회 실패: {exc}"}
    except Exception as exc:  # pragma: no cover - 범용 예외처리
        return {"error": f"예상치 못한 오류: {exc}"}


@mcp.resource("manual://manuals")
def list_manuals() -> Dict[str, List[str]]:
    """매뉴얼 디렉터리 구조를 반환한다."""
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
