# MCP → Dashboard 연계 JSON 구조

## 개요
/dashboard 모듈이 이상치를 감지하면 아래 정보를 포함한 JSON을 /mcp 큐에 넣는다. MCP는 해당 payload를 기반으로 로컬 메뉴얼을 조회하고, 결과를 동일한 dashboard row에 다시 써 넣는다.

## 필수 필드
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `trace_id` | string | 이벤트 추적 ID. 없으면 MCP에서 생성 |
| `dashboard_id` | integer | dashboard 테이블 row id (LLM 결과를 업데이트할 대상) |
| `message` | string | dashboard.message에 들어간 원본 알림/상황 설명 |
| `anomaly` | object | (옵션) 센서/룰 상세 정보. MCP 프롬프트에 포함됨 |
| `ai_error` | object | (옵션) AI/시스템 에러 신호 |
| `manual_reference.path` | string | 로컬 메뉴얼 폴더/파일 경로 |
| `manual_reference.tags` | array[string] | (선택) 메뉴얼에서 참조할 키워드. 지정하면 해당 키워드 주변만 스니펫으로 추출하고, 비우면 파일 전체(앞부분 최대 약 5,000자)를 그대로 사용한다. |

## 예시
```json
{
  "trace_id": "trace-1733898212",
  "dashboard_id": 42,
  "message": "TEMP_SENSOR_5 온도가 95℃로 임계치 초과",
  "anomaly": {
    "sensor_id": 5,
    "metric": "temperature",
    "actual": 95.0,
    "expected": 75.0,
    "rule": "zscore>3"
  },
  "ai_error": {},
  "manual_reference": {
    "path": "docs/manuals/temperature",
    "tags": ["sensor5", "overheat"]
  }
}
```

## 처리 규칙 요약
1. MCP는 `manual_reference`에 따라 로컬 메뉴얼을 추출하고 `message` + `anomaly`를 프롬프트에 포함한다.
2. LLM 응답이 성공하면 `dashboard_id` 행의 `mannual` 컬럼을 조치안 문자열로 업데이트하고, `ishandled`를 false로 유지한다.
3. 최대 3회 재시도에도 실패하면 `mannual`을 `"매뉴얼 생성 실패"`로 채우고 데드레터 큐에 기록한다.
