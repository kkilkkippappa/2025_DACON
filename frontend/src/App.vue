<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

/**
 * @typedef {Object} Alert
 * @property {string} id - 고유 식별자
 * @property {string} occurredAt - 발생일자 (YYYY-MM-DD HH:mm:ss 형식)
 * @property {'warning'|'alarm'} type - 알림 타입
 * @property {string} message - 경고 메세지
 * @property {string} recommendation - AI 추천 조치사항
 * @property {boolean} isAcknowledged - 조치 완료 여부
 */

// 반응형 상태 관리
const alerts = ref([
  {
    id: 'a-001',
    occurredAt: '2025-12-04 10:15:23',
    type: 'warning',
    message: 'CPU 사용률이 80%를 초과했습니다. 비정상 프로세스 여부 확인 필요.',
    recommendation: 'Top 3 프로세스 점검 후 불필요 프로세스 종료, 5분 후 재측정.',
    isAcknowledged: false,
  },
  {
    id: 'a-002',
    occurredAt: '2025-12-04 09:58:41',
    type: 'alarm',
    message: '웹 애플리케이션 응답 지연 감지. 평균 응답시간 4.5s.',
    recommendation: '최근 배포 롤백 검토, APM 트레이스 확인 후 장애 전파 여부 판단.',
    isAcknowledged: false,
  },
  {
    id: 'a-003',
    occurredAt: '2025-12-04 09:12:05',
    type: 'warning',
    message: '디스크 사용률 70% 도달. 로그 로테이션 필요.',
    recommendation: '로그 로테이션 스케줄 확인, 불필요 로그 삭제 및 압축.',
    isAcknowledged: false,
  },
]);

// 모달 상태 관리
const currentModalAlert = ref(null);
const isModalOpen = ref(false);

// 토스트 상태 관리
const toastMessage = ref('');
const isToastVisible = ref(false);
let toastTimer = null;

// 마지막 업데이트 시간
const lastUpdated = ref('업데이트 대기 중...');

/**
 * 정렬된 알림 목록 (발생일자 기준 내림차순)
 */
const sortedAlerts = computed(() => {
  return [...alerts.value].sort((a, b) => new Date(b.occurredAt) - new Date(a.occurredAt));
});

/**
 * 마지막 업데이트 시간 갱신
 */
const updateLastUpdated = () => {
  const now = new Date();
  lastUpdated.value = `업데이트: ${now.toLocaleString('ko-KR')}`;
};

/**
 * 모달 열기
 * @param {Alert} alert
 */
const openModal = (alert) => {
  currentModalAlert.value = alert;
  isModalOpen.value = true;
};

/**
 * 모달 닫기
 */
const closeModal = () => {
  isModalOpen.value = false;
  currentModalAlert.value = null;
};

/**
 * 조치 완료 처리
 */
const handleAcknowledge = () => {
  if (!currentModalAlert.value || currentModalAlert.value.isAcknowledged) return;

  currentModalAlert.value.isAcknowledged = true;

  const idx = alerts.value.findIndex((a) => a.id === currentModalAlert.value.id);
  if (idx !== -1) alerts.value[idx].isAcknowledged = true;

  updateLastUpdated();

  // 실제 연동 시 API 호출
  // await fetch(`/api/alerts/${currentModalAlert.value.id}/acknowledge`, { method: 'POST' });
};

/**
 * 신규 alarm 수신 처리
 * @param {Alert} newAlert
 */
const handleIncomingAlarm = (newAlert) => {
  const exists = alerts.value.some((a) => a.id === newAlert.id);
  if (exists) return;

  newAlert.isAcknowledged = false;
  alerts.value.unshift(newAlert);

  updateLastUpdated();

  toastMessage.value = `${newAlert.occurredAt} · ${newAlert.message}`;
  isToastVisible.value = true;

  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    isToastVisible.value = false;
  }, 7000);
};

/**
 * 토스트에서 상세보기 열기
 */
const openModalFromToast = () => {
  const latestAlert = sortedAlerts.value.find((a) => !a.isAcknowledged);
  if (latestAlert) {
    isToastVisible.value = false;
    openModal(latestAlert);
  }
};

onMounted(() => {
  updateLastUpdated();

  // 데모용: 4초 후 신규 alarm 도착 시나리오
  setTimeout(() => {
    const incoming = {
      id: 'a-004',
      occurredAt: new Date().toLocaleString('ko-KR'),
      type: 'alarm',
      message: 'DB 연결 지연 및 재시도 발생. 연결 실패율 12% 감지.',
      recommendation: 'DB 연결 풀 모니터링, 장애 조치 스위치 점검 후 read replica 전환 고려.',
      isAcknowledged: false,
    };
    handleIncomingAlarm(incoming);
  }, 4000);
});

onUnmounted(() => {
  if (toastTimer) clearTimeout(toastTimer);
});
</script>

<template>
  <div>
    <header>
      <div>
        <div class="title">Alert Dashboard</div>
        <div class="subtitle">초기 프로토타입 · UI 피드백용</div>
      </div>
      <div class="pill">실시간 모니터링</div>
    </header>

    <main>
      <section class="card">
        <div class="card-header">
          <div>
            <div style="font-weight:700;">최근 발생 알림</div>
            <div class="subtitle">행을 클릭하면 상세를 볼 수 있어요.</div>
          </div>
          <div class="subtitle">{{ lastUpdated }}</div>
        </div>
        <table id="alert-table">
          <thead>
            <tr>
              <th>발생일자</th>
              <th>Alert Type</th>
              <th>조치 완료 여부</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="alert in sortedAlerts"
              :key="alert.id"
              :class="{ acknowledged: alert.isAcknowledged }"
              @click="openModal(alert)"
            >
              <td>{{ alert.occurredAt }}</td>
              <td>
                <span :class="['badge', alert.type]">
                  <span class="status-dot"></span>
                  {{ alert.type }}
                </span>
              </td>
              <td>
                <span :class="['badge', alert.isAcknowledged ? 'completed' : 'pending']">
                  <span class="status-dot"></span>
                  {{ alert.isAcknowledged ? '완료' : '대기' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>

    <!-- 상세보기 모달 -->
    <div v-if="isModalOpen" class="modal-backdrop" @click.self="closeModal">
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modal-header">
          <div style="display:flex; gap:10px; align-items:center;">
            <div v-if="currentModalAlert" :class="['badge', currentModalAlert.type]">
              {{ currentModalAlert.type.toUpperCase() }}
            </div>
            <div style="font-weight:700;">
              Alert 상세
              <span v-if="currentModalAlert"> · {{ currentModalAlert.id }}</span>
            </div>
          </div>
          <button class="secondary" @click="closeModal">닫기</button>
        </div>
        <div class="modal-body" v-if="currentModalAlert">
          <div class="meta">
            <span>{{ currentModalAlert.occurredAt }}</span>
            <span style="color:rgba(255,255,255,0.15);">•</span>
            <span>{{ currentModalAlert.type.toUpperCase() }}</span>
          </div>
          <div class="section">
            <div class="section-title">경고 메세지</div>
            <div class="section-content">{{ currentModalAlert.message }}</div>
          </div>
          <div class="section">
            <div class="section-title">AI 추천 조치사항</div>
            <div class="section-content">{{ currentModalAlert.recommendation }}</div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="secondary" @click="closeModal">확인</button>
          <button
            :disabled="currentModalAlert?.isAcknowledged"
            :style="{
              background: currentModalAlert?.isAcknowledged
                ? 'rgba(34,197,94,0.2)'
                : '#60a5fa',
              color: currentModalAlert?.isAcknowledged
                ? '#22c55e'
                : '#0b1220'
            }"
            @click="handleAcknowledge"
          >
            {{ currentModalAlert?.isAcknowledged ? '조치 완료됨' : '조치 완료' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 신규 alarm 알림 토스트 -->
    <div v-if="isToastVisible" class="toast" style="display: block;">
      <div style="flex:1;">
        <div class="toast-title">새로운 Alarm 도착</div>
        <div class="subtitle">{{ toastMessage }}</div>
        <button @click="openModalFromToast">상세 바로 보기</button>
      </div>
    </div>
  </div>
</template>

