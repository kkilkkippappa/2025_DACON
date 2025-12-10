# Alert Dashboard 웹 UI 프로토타입 기능 목록

## 개요
팀원 피드백용 초기 웹 UI 프로토타입으로, Alert 모니터링 대시보드의 핵심 기능을 구현했습니다.

**기술 스택**: Vue.js 3 (Composition API) + Vanilla CSS

---

## 1. 메인 대시보드

### 1.1 알림 목록 테이블
- **위치**: 메인 화면 중앙
- **표시 항목**:
  - 발생일자: 알림이 발생한 날짜 및 시간
  - Alert Type: `warning` 또는 `alarm` 타입을 배지로 표시
  - 조치 완료 여부: 완료/대기 상태를 배지로 표시
- **정렬**: 발생일자 기준 내림차순 (최신순)
- **상호작용**: 
  - 행 클릭 시 상세보기 모달 열림
  - 행 호버 시 배경색 변경으로 클릭 가능 표시

### 1.2 조치 완료 상태 표시
- **완료 상태**: 초록색 배지로 "완료" 표시, 행 전체 투명도 감소 (opacity: 0.65)
- **대기 상태**: 회색 배지로 "대기" 표시
- **데이터 유지**: 조치 완료 후에도 대시보드에서 데이터가 계속 표시됨

### 1.3 업데이트 시간 표시
- **위치**: 카드 헤더 우측
- **기능**: 테이블 렌더링 시 현재 시간을 한국어 형식으로 표시

---

## 2. 상세보기 모달

### 2.1 모달 헤더
- **Alert Type 배지**: warning/alarm 타입을 색상별 배지로 표시
- **Alert ID**: 상세 정보 식별용 ID 표시
- **닫기 버튼**: 모달 종료

### 2.2 메타 정보
- **발생시각**: 알림 발생 일시
- **Alert Type**: 대문자로 타입 표시

### 2.3 본문 섹션
- **경고 메세지**: 
  - 알림의 상세 경고 내용 표시
  - 긴 텍스트도 줄바꿈 처리
- **AI 추천 조치사항**: 
  - AI가 추천하는 조치 방법 표시
  - 긴 텍스트도 줄바꿈 처리

### 2.4 모달 푸터
- **확인 버튼**: 모달 닫기
- **조치 완료 버튼**: 
  - 클릭 시 해당 알림의 `isAcknowledged` 상태를 `true`로 변경
  - 조치 완료 후 버튼 비활성화 및 "조치 완료됨" 텍스트로 변경
  - 조치 완료된 항목은 다시 클릭 불가능

### 2.5 모달 닫기 방법
- 닫기 버튼 클릭
- 확인 버튼 클릭
- 모달 배경(backdrop) 클릭

---

## 3. 신규 Alarm 수신 알림

### 3.1 토스트 알림
- **트리거**: 백엔드로부터 새로운 alarm 데이터 수신 시
- **위치**: 화면 우측 상단
- **표시 내용**:
  - 제목: "새로운 Alarm 도착" (빨간색 강조)
  - 메시지: 발생일자와 경고 메세지 미리보기
  - 버튼: "상세 바로 보기"

### 3.2 자동 숨김
- **타이머**: 7초 후 자동으로 토스트 알림 숨김
- **중복 방지**: 새로운 알림이 오면 기존 타이머 취소 후 재설정

### 3.3 상세보기 바로가기
- **기능**: 토스트의 "상세 바로 보기" 버튼 클릭 시
  - 토스트 알림 닫기
  - 해당 알림의 상세보기 모달 자동 열림

### 3.4 데이터 처리
- **중복 방지**: 동일 ID의 알림은 중복 추가하지 않음
- **자동 추가**: 신규 알림을 대시보드 목록 최상단에 추가
- **기본 상태**: 신규 알림은 자동으로 `isAcknowledged: false` 상태로 설정

---

## 4. 데이터 구조

### 4.1 Alert 객체 구조
```javascript
{
  id: string,                    // 고유 식별자
  occurredAt: string,            // 발생일자 (YYYY-MM-DD HH:mm:ss 형식)
  type: "warning" | "alarm",     // 알림 타입
  message: string,                // 경고 메세지
  recommendation: string,         // AI 추천 조치사항
  isAcknowledged: boolean        // 조치 완료 여부
}
```

### 4.2 초기 데이터
- 3개의 샘플 알림 데이터 포함
- 모든 알림은 기본적으로 `isAcknowledged: false` 상태

---

## 5. UI/UX 특징

### 5.1 디자인
- **다크 테마**: 어두운 배경과 밝은 텍스트로 구성
- **그라데이션 효과**: 배경에 미묘한 그라데이션 적용
- **글래스모피즘**: 카드와 모달에 반투명 효과 및 블러 적용
- **색상 구분**:
  - Warning: 주황색 (#f59e0b)
  - Alarm: 빨간색 (#ef4444)
  - 완료: 초록색 (#22c55e)
  - 대기: 회색 (#9ca3af)

### 5.2 반응형 디자인
- **모바일 대응**: 640px 이하 화면에서 레이아웃 자동 조정
- **모달 크기**: 최대 720px, 작은 화면에서는 전체 너비 사용

### 5.3 접근성
- **키보드 네비게이션**: 모달에 `role="dialog"` 및 `aria-modal` 속성 적용
- **시각적 피드백**: 호버, 클릭 시 명확한 시각적 변화

---

## 6. 백엔드 연동 준비

### 6.1 API 연동 포인트
- **데이터 로드**: `alerts` ref를 API 응답으로 대체
- **조치 완료**: `handleAcknowledge()` 함수 내부에 API 호출 코드 주석 처리됨
  ```javascript
  // await fetch(`/api/alerts/${currentModalAlert.value.id}/acknowledge`, { method: 'POST' });
  ```

### 6.2 실시간 알림 연동
- **함수**: `handleIncomingAlarm(newAlert)` 함수 제공
- **사용법**: WebSocket 또는 Server-Sent Events에서 수신한 데이터를 이 함수로 전달
- **데모**: 4초 후 자동으로 신규 alarm 도착 시뮬레이션 (실제 연동 시 제거)
- **Vue 반응성**: `alerts` ref를 통해 자동으로 UI 업데이트

---

## 7. 주요 함수 (Vue.js Composition API)

### 7.1 `sortedAlerts` (Computed)
- 대시보드 테이블용 정렬된 알림 목록
- 발생일자 기준 내림차순 정렬
- Vue의 반응성 시스템을 통해 자동 업데이트

### 7.2 `openModal(alert)`
- 상세보기 모달 열기
- Alert 데이터를 모달에 표시
- `currentModalAlert` ref 업데이트

### 7.3 `closeModal()`
- 상세보기 모달 닫기
- 현재 모달 상태 초기화
- `isModalOpen` ref를 false로 설정

### 7.4 `handleAcknowledge()`
- 조치 완료 처리
- `isAcknowledged` 상태를 true로 변경
- Vue 반응성을 통해 자동 UI 업데이트

### 7.5 `handleIncomingAlarm(newAlert)`
- 신규 alarm 수신 처리
- 중복 방지
- 대시보드 업데이트 (alerts ref에 추가)
- 토스트 알림 표시

### 7.6 `updateLastUpdated()`
- 마지막 업데이트 시간 갱신
- 한국어 형식으로 시간 표시

---

## 8. 향후 개선 가능 사항

- [ ] 필터링 기능 (Alert Type, 조치 완료 여부별 필터)
- [ ] 검색 기능
- [ ] 페이지네이션 또는 무한 스크롤
- [ ] 정렬 옵션 추가
- [ ] 알림 소리 재생 옵션
- [ ] 다중 선택 및 일괄 조치 완료
- [ ] 조치 완료 취소 기능
- [ ] 알림 통계 대시보드 (차트 등)

---

## 파일 구조

```
2025_Hackathon/
├── index.html              # Vue.js 앱 진입점 (HTML)
├── main.js                 # Vue.js 앱 메인 로직 (Composition API)
├── styles.css              # 스타일시트
├── package.json            # npm 의존성 관리
├── vite.config.js          # Vite 빌드 설정 (선택사항)
└── web_function_list.md   # 본 기능 목록 문서
```

## 9. Vue.js 구현 특징

### 9.1 반응성 시스템
- **ref**: 알림 목록, 모달 상태, 토스트 상태 등을 반응형으로 관리
- **computed**: 정렬된 알림 목록을 계산된 속성으로 제공
- **자동 업데이트**: 데이터 변경 시 UI 자동 갱신

### 9.2 Composition API
- **setup()**: 컴포넌트 로직을 setup 함수 내에서 구성
- **생명주기 훅**: `onMounted`, `onUnmounted` 사용
- **모듈화**: 기능별로 함수 분리하여 가독성 향상

### 9.3 템플릿 문법
- **v-for**: 알림 목록 렌더링
- **v-if**: 조건부 렌더링 (모달, 토스트)
- **v-bind**: 동적 클래스 및 스타일 바인딩
- **@click**: 이벤트 핸들링

### 9.4 개발 환경
- **CDN 방식**: Vue 3 CDN을 통한 즉시 사용 가능
- **Vite 지원**: `package.json` 및 `vite.config.js` 제공 (선택사항)
- **빌드 도구 없이 실행 가능**: CDN 방식으로 바로 실행 가능

## 10. FastAPI × Vue 연동 계획

### 10.1 API 게이트웨이 (FastAPI)
- `/dashboard` 프리픽스를 유지한 채 Vue가 호출할 REST 엔드포인트를 제공한다.
- 현재는 스펙 정의 단계이므로 `GET /dashboard/alerts`, `GET /dashboard/stats`, `POST /dashboard/acknowledge` 같은 라우트의 골격만 마련하고, 응답 페이로드는 샘플 JSON으로 대체한다.
- 실제 DB 스키마와 JSON 포맷이 확정되면 위 라우트의 응답을 교체하고, 별도 서비스 계층에서 데이터베이스 접근 로직을 구현한다.

### 10.2 Vue 데이터 흐름
- Vue 컴포넌트는 `fetch('/dashboard/...')` 또는 `axios` 호출을 통해 FastAPI에서 제공하는 데이터를 수신한다.
- 현재 단계에서는 mock 응답을 사용하여 UI 상태만 구축하고, API 스펙이 확정되면 동일한 인터페이스로 실제 데이터를 연결한다.
- 데이터 구조(예: Alert 객체 필드) 정의가 완료되면 전역 타입 또는 composable을 통해 재사용하도록 설계한다.

### 10.3 CORS 및 프록시 설정
- FastAPI: `CORSMiddleware`를 추가하여 `http://localhost:5173` 등 프론트 개발 서버를 `allow_origins`에 포함하고, `allow_methods`, `allow_headers`를 전체 허용으로 설정한다.
- Vue/Vite: `vite.config.js`의 `server.proxy`에 `/dashboard`: `http://localhost:8000`을 지정하면, 개발 중에도 동일한 origin에서 호출하는 것처럼 API 요청을 전송할 수 있다.

### 10.4 배포 시 정적 자산 서빙
- `npm run build` 결과물(`frontend/dist`)을 FastAPI에 `StaticFiles(directory="frontend/dist", html=True)`로 mount하여 `/dashboard` 경로에서 Vue SPA를 제공한다.
- 이렇게 하면 FastAPI 단일 서버가 API와 정적 대시보드 모두를 처리하므로 운영 배포 구성이 단순해진다.

---

**작성일**: 2025-12-05  
**버전**: 2.0 (Vue.js 전환)
