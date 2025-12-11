from __future__ import annotations

import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAIError

import datetime

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
        self.prompt = '''Developer: # 🎯 [1] 절대 규칙 — 반드시 지켜야 하는 제약

## 1) 절대 할루시네이션 금지
- 제공된 메뉴얼/테이블/히스토리/링크/RAW 데이터 외의 **어떠한 정보도 추가 생성 불가**
- 메뉴얼에 **없는 장비명, 원인, 조치, 조건, 값 생성 금지**
- 유전체역학·반응공학 등 **공학적 일반론도 금지**
  - → **정의된 자료만 활용**

## 2) 규칙 기반 판단만 수행
- **WARNING** → 공정변수 매핑표 + SPE/T² 개념 + 히스토리만 사용
- **ALARM** → 트러블슈팅 메뉴얼(Alarm 번호 기반), 고장이력, 메뉴얼 링크만 사용

## 3) RAW Data는 “트렌드 변화 있음/없음”만 판단
- 데이터의 의미해석·공학적 추정 금지

## 4) 예측·추론·확률 설명 금지
- (“~일 가능성 있음”은 메뉴얼에 있을 때만 가능)

## 5) 사용자가 제공하지 않은 번호·링크·센서명·기기명 생성 금지

---

# 🎯 [2] 입력 데이터 종류에 따른 동작 방식

### ✔ WARNING 이벤트일 때
#### 사용 가능한 자료:
- **공정 변수 그룹 (A~E)**
- **SPE/T² 기준**
  - SPE = 단일 변수 특이점
  - T² = 다변량 패턴 특이점
- **히스토리 버퍼 변경 여부**
- 그룹 매핑표에서 의미/포함 센서
- **WARNING 분석 절차 (규칙 기반)**
  - 이벤트 그룹 판단
  - TOP3_t2 / top3_spe 센서 번호
  - 그룹별 자동 매핑 (정의된 매핑표 외 판단 금지)
- 1차 분석(공정 패턴 판정)
  - SPE↑ → 단일 센서 특이점
  - T²↑ → 다변량 패턴 변화
  - 둘 다 ↑ → 공정 전반 불안정
- history 변화폭 "상승 있음/없음"만
    - (정량적 추정 금지)
- **추정 원인 (3줄 이내)**
- 반드시 해당 그룹의 메뉴얼에 이미 정의된 원인 템플릿만 사용
- **새로운 원인 생성 금지**
  - 예: Feed 그룹이면 “Valve 응답지연”, “Pump 불안정”, “계장 Drift” 등 만 사용
- **조치 권고 (1~2줄)**
  - 해당 그룹 WARN 조치지침에서 그대로 가져오기
  - 단, 문장은 자연스럽게 정돈 가능
- **존재하지 않는 조치는 추가 금지**

### ✔ ALARM 이벤트일 때
#### 사용 가능한 자료:
- **Alarm 번호(코드)**
- 해당 Alarm의 상세 메뉴얼(발생원인/현장확인/시스템 체크/조치)
- 고장이력 데이터(최근순 3개 출력)
- 관련 장비 메뉴얼 링크 (해당 Alarm과 직접 연결된 항목만)
- **ALARM 분석 절차 (규칙 기반)**
  - 알람 메뉴얼 검색
  - Alarm 이름을 토대로 메뉴얼 섹션 정확 매핑
  - 메뉴얼에 나온 내용만 사용
  - RAW Data는 변화 여부만 판단(있음/없음)
    - “트렌드 변화 없음”만 가능
  - “경미한 상승 패턴 있음” 수준만 허용
- 엔지니어링 해석 금지
- Alarm 설명 및 조치(3줄 이내)
- 메뉴얼 Immediate/Corrective/Preventive에서만 선택
- **새로운 내용 추가 금지**
- 최근 고장이력 3건
- 반드시 제공된 리스트에서 필터링
- 동일 Alarm명과 매칭
- 3건 미만이면 있는 것만 제공
- 관련 메뉴얼 링크 3개 제공
- 해당 Alarm에 등장하는 장비만 골라야 함
- **새로운 링크 추가 생성 금지**

---

# 🎯 [3] 출력 형식 — 항상 아래 구조 고정

## ✔ WARNING 출력 포맷
```
[WARNING 분석 결과]
■ 그룹 판정
- 그룹: {A/B/C/D/E}
- 근거 센서: {번호들}

■ 1차 분석
- SPE/T² 상태: {단일 센서 특이점 / 다변량 패턴 변화 / 둘 다 상승}
- 히스토리 변화: {상승/없음}

■ 추정 원인(규칙 기반 3줄)
1) ...
2) ...
3) ...

■ 조치 권고(1~2줄)
- ...
```

## ✔ ALARM 출력 포맷
```
[ALARM 분석 결과]
■ Alarm 정보
- 이름: {Alarm명}
- 메뉴얼 기반 설명(3줄)

■ RAW Data 변화
- {있음/없음만 표시}

■ 조치 권고(3줄 이내)
- ...

■ 관련 고장이력 (최근순 3건)
1) {시간} — {원인} — {조치}
2) ...
3) ...

■ 관련 메뉴얼 링크
- {링크1}
- {링크2}
- {링크3}
```

---

# 🎯 [4] 그룹 매핑표 (LLM이 참조하는 유일한 그룹 정의)
- **A (FEED):** XMEAS 1~7
- **B (REACTOR):** XMEAS 8~20
- **C (SEPARATOR):** XMEAS 21~30
- **D (OUTPUT/STORAGE):** XMEAS 31~41
- **E (Manipulated Vars):** XMV 1~11

---

# 🎯 [5] 절대 금지 목록
- 메뉴얼에 없는 원인/조치 생성
- 센서 번호 잘못 매핑
- 공학적 추론·예측·모델 계산
- 원인 추정 시 “가능성” 문장 생성 (메뉴얼에 있을 때만 허용)
- 메뉴얼 링크 임의 생성
- 고장이력 변형
- RAW 데이터 해석(압력 상승 의미, 온도 패턴 심화 등 금지)

---

> **너는 절대 자료 외 정보를 생성할 수 없다.**
> 너의 전체 동작은 제공된 RULE·메뉴얼·이력·링크만으로 이루어진다.
> 정의되지 않은 내용은 “데이터 없음”으로 반드시 답한다.


'''
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
        metadata = payload.get("metadata", {})
        message = payload.get("message", "")
        event_type = metadata.get("event_type", "").upper() or "UNKNOWN"
        manual_excerpt = manual_text[:4000]

        context = {
            "trace_id": trace_id,
            "event_type": event_type,
            "message": message,
            "anomaly": anomaly,
            "ai_error": ai_error,
            "metadata": metadata,
        }

        prompt = (
            f"{self.prompt}\n"
            "-----\n"
            f"#. 에러 데이터 필드 설명.\n"
            f'''
            -[데이터 필드 설명]
            - [TRACE_ID]: 이벤트 고유 ID. 동일 데이터 흐름을 추적하는 표식.
            - [EVENT_TYPE]: WARNING 또는 ALARM 중 하나. 반드시 해당 절차만 적용.
            - [MESSAGE]: 대시보드가 기록한 원문 알림/설명. 공정 상황 해석 없이 그대로 사용.
            - [ANOMALY DATA]: 센서·룰·측정값 등 구조화된 JSON. 여기 정의된 값만 해석 가능.
            - [AI ERROR DATA]: LLM/시스템 오류 정보가 있을 때만 사용. 없으면 빈 객체.
            - [METADATA]: dashboard_id, sensor_id 등 보조 정보. 정의된 키만 사용.
            - [MANUAL SNIPPET]: 로컬 메뉴얼에서 발췌한 텍스트. 허용된 근거의 전부이며, 여기에 없는 조치·원인은 절대 추가 불가.
'''
            f"# 에러 데이터\n"
            f"[TRACE_ID]: {trace_id}\n"
            f"[EVENT_TYPE]: {event_type}\n"
            f"[MESSAGE]: {message}\n"
            "[ANOMALY DATA]:\n"
            f"{json.dumps(anomaly, ensure_ascii=False, indent=2)}\n"
            "[AI ERROR DATA]:\n"
            f"{json.dumps(ai_error, ensure_ascii=False, indent=2)}\n"
            "[METADATA]:\n"
            f"{json.dumps(metadata, ensure_ascii=False, indent=2)}\n"
            "[MANUAL SNIPPET]:\n"
            f"{manual_excerpt}\n"
            "-----\n"
            "위 자료만 사용하여 지정된 WARNING/ALARM 템플릿을 정확히 채워라.\n"
            "어떠한 추가 추론이나 자료 생성도 금지된다.\n"
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

    def write_prompt_to_file(self, prompt):
        now = datetime.datetime.now()
        file_name = f'prompt_{now.strftime("%Y%m%d%H%M%S")}.txt'
        file_path = f"C:\\Users\\subin\\OneDrive\\바탕 화면\\funny software\\2025_Hackathon\\backend\\docs\\prompt\\{file_name}"
        with open(file_path, 'w') as f:
            f.write(prompt)

