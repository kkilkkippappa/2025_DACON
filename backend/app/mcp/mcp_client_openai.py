from __future__ import annotations

import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAIError

load_dotenv()


class MCPClientError(RuntimeError):
    """LLM 호출 오류."""


class OpenAIMCPClient:
    """OpenAI Responses API를 통해 권장 조치를 생성하는 클라이언트."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise MCPClientError("OPENAI_API_KEY 가 설정되어 있지 않습니다.")
        self.model = os.getenv("MCP_OPENAI_MODEL", "gpt-4o-mini")
        timeout = int(os.getenv("MCP_OPENAI_TIMEOUT", "30"))
        self.client = AsyncOpenAI(timeout=timeout)

    async def generate_guidance(
        self,
        payload: Dict[str, Any],
        manual_text: str,
    ) -> Dict[str, Any]:
        """LLM에게 권장 조치를 요청한다."""
        prompt = self._build_prompt(payload, manual_text)
        try:
            response = await self.client.responses.create(
                model=self.model,
                input=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_output_tokens=800,
            )
        except OpenAIError as exc:
            raise MCPClientError(f"OpenAI 오류: {exc}") from exc
        except Exception as exc:  # pragma: no cover
            raise MCPClientError(f"LLM 호출 중 알 수 없는 오류: {exc}") from exc

        parsed = self._parse_response(response)
        if parsed:
            return parsed

        return self._fallback_response(payload, manual_text)

    def _build_prompt(self, payload: Dict[str, Any], manual_text: str) -> str:
        anomaly = payload.get("anomaly", {})
        ai_error = payload.get("ai_error", {})
        trace_id = payload.get("trace_id", "unknown-trace")
        manual_excerpt = manual_text[:4000]

        prompt = (
            "You are an MCP assistant who recommends operator guidance.\n"
            "Always respond with JSON containing summary, steps(list), and confidence.\n"
            f"TRACE_ID: {trace_id}\n"
            f"ANOMALY: {json.dumps(anomaly, ensure_ascii=False)}\n"
            f"AI_ERROR: {json.dumps(ai_error, ensure_ascii=False)}\n"
            "MANUAL_SNIPPET:\n"
            f"{manual_excerpt}\n"
            "Return JSON with keys summary(str), steps(list of {order,int,action,note}), confidence(str).\n"
        )
        return prompt

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        raw_text = getattr(response, "output_text", "") or ""
        if not raw_text:
            try:
                # responses API
                raw_text = response.output[0].content[0].text
            except Exception:
                raw_text = ""
        try:
            data = json.loads(raw_text)
            summary = data.get("summary")
            steps = data.get("steps")
            if summary and isinstance(steps, list):
                return {
                    "summary": summary,
                    "steps": steps,
                    "confidence": data.get("confidence"),
                    "model": self.model,
                }
        except json.JSONDecodeError:
            return {}
        return {}

    def _fallback_response(
        self,
        payload: Dict[str, Any],
        manual_text: str,
    ) -> Dict[str, Any]:
        anomaly = payload.get("anomaly") or {}
        desc = anomaly.get("metric") or anomaly.get("sensor_id") or "unknown metric"
        summary = f"{desc} 이상치 대응 - 메뉴얼을 확인해 즉각 조치하세요."
        steps = [
            {
                "order": 1,
                "action": "메뉴얼 요약 검토",
                "note": manual_text[:200] or "메뉴얼 내용 없음",
            },
            {
                "order": 2,
                "action": "현장 설비 점검",
                "note": "센서 상태와 최근 변경 사항을 확인하세요.",
            },
            {
                "order": 3,
                "action": "조치 결과 기록",
                "note": "백엔드에 권장 조치를 완료로 표시합니다.",
            },
        ]
        return {
            "summary": summary,
            "steps": steps,
            "confidence": "low",
            "model": self.model,
        }
