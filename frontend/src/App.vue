<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

import { buildApiBase, buildEndpoint, sanitizeAlert } from './utils/dashboard';

const FASTAPI_HOST = import.meta.env.FASTAPI_LOCAL_URL ?? 'http://localhost';
const FASTAPI_PORT = import.meta.env.FASTAPI_DEV_SERVER_PORT ?? '8000';
const DASHBOARD_API_BASE_PATH = import.meta.env.VUE_API_BASE_PATH ?? '/dashboard';

const DASHBOARD_API_BASE = buildApiBase(FASTAPI_HOST, FASTAPI_PORT, DASHBOARD_API_BASE_PATH);

const mapEndpoint = (suffix = '') => buildEndpoint(DASHBOARD_API_BASE, suffix);
const TOAST_DURATION_MS = 7000;

const useAlertDashboard = () => {
  const alerts = ref([]);
  const lastUpdated = ref('데이터 동기화 대기 중...');

  const toEpoch = (value) => {
    const parsed = Date.parse(value);
    return Number.isNaN(parsed) ? 0 : parsed;
  };

  const sortedAlerts = computed(() =>
    [...alerts.value].sort(
      (first, second) => toEpoch(second.occurredAt) - toEpoch(first.occurredAt),
    ),
  );

  const touchLastUpdated = () => {
    lastUpdated.value = `마지막 동기화: ${new Date().toLocaleString('ko-KR')}`;
  };

  const setAlerts = (nextAlerts) => {
    alerts.value = nextAlerts.map(sanitizeAlert);
    touchLastUpdated();
  };

  const syncAlert = (nextAlert) => {
    if (!nextAlert) {
      return null;
    }

    const normalized = sanitizeAlert(nextAlert);
    const existingIdx = alerts.value.findIndex((alert) => alert.id === normalized.id);

    if (existingIdx === -1) {
      alerts.value.unshift(normalized);
      touchLastUpdated();
      return alerts.value[0];
    }

    alerts.value[existingIdx] = { ...alerts.value[existingIdx], ...normalized };
    touchLastUpdated();
    return alerts.value[existingIdx];
  };

  return {
    sortedAlerts,
    lastUpdated,
    setAlerts,
    syncAlert,
    touchLastUpdated,
  };
};

const useModalController = () => {
  const currentModalAlert = ref(null);
  const isModalOpen = computed(() => Boolean(currentModalAlert.value));

  const openModal = (alert) => {
    currentModalAlert.value = alert;
  };

  const closeModal = () => {
    currentModalAlert.value = null;
  };

  return { currentModalAlert, isModalOpen, openModal, closeModal };
};

const useToast = () => {
  const toastMessage = ref('');
  const isToastVisible = ref(false);
  let toastTimerId;

  const stopTimer = () => {
    if (toastTimerId) {
      clearTimeout(toastTimerId);
      toastTimerId = null;
    }
  };

  const hideToast = () => {
    isToastVisible.value = false;
    stopTimer();
  };

  const showToast = (message) => {
    toastMessage.value = message;
    isToastVisible.value = true;

    stopTimer();
    toastTimerId = setTimeout(() => {
      isToastVisible.value = false;
      toastTimerId = null;
    }, TOAST_DURATION_MS);
  };

  onUnmounted(stopTimer);

  return { toastMessage, isToastVisible, showToast, hideToast };
};

const { sortedAlerts, lastUpdated, setAlerts, syncAlert } = useAlertDashboard();
const { currentModalAlert, isModalOpen, openModal, closeModal } = useModalController();
const { toastMessage, isToastVisible, hideToast } = useToast();

const isLoadingAlerts = ref(false);
const loadError = ref('');

const fetchDashboardAlerts = async () => {
  isLoadingAlerts.value = true;
  loadError.value = '';

  try {
    const response = await fetch(mapEndpoint('/alerts'));
    if (!response.ok) {
      throw new Error(`Failed to load alerts (${response.status})`);
    }

    const payload = await response.json();
    const normalized = Array.isArray(payload) ? payload : [];
    setAlerts(normalized);
  } catch (error) {
    console.error('Failed to load dashboard alerts', error);
    loadError.value = '알림 데이터를 불러오지 못했습니다. 잠시 후 다시 시도하세요.';
  } finally {
    isLoadingAlerts.value = false;
  }
};

const acknowledgeCurrentAlert = async () => {
  if (!currentModalAlert.value || currentModalAlert.value.isAcknowledged) {
    return;
  }

  try {
    const response = await fetch(
      mapEndpoint(`/alerts/${currentModalAlert.value.id}/handled`),
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isAcknowledged: true }),
      },
    );

    if (!response.ok) {
      throw new Error(`Failed to acknowledge alert (${response.status})`);
    }

    const payload = await response.json();
    const synced = syncAlert(payload);
    if (synced) {
      currentModalAlert.value = synced;
    }
  } catch (error) {
    console.error('Failed to acknowledge alert', error);
  }
};

const openModalFromToast = () => {
  const latestAlert = sortedAlerts.value.find((alert) => !alert.isAcknowledged);
  if (latestAlert) {
    hideToast();
    openModal(latestAlert);
  }
};

onMounted(() => {
  fetchDashboardAlerts();
});
</script>

<template>
  <div>
    <header>
      <div>
        <div class="title">Alert Dashboard</div>
        <div class="subtitle">Early prototype dashboard &amp; UI playground</div>
      </div>
      <div class="pill">Real-time Monitoring</div>
    </header>

    <main>
      <section class="card">
        <div class="card-header">
          <div>
            <div class="section-heading">Latest Alerts</div>
            <div class="subtitle">Click any row to inspect the full context</div>
          </div>
          <div class="subtitle">{{ lastUpdated }}</div>
        </div>
        <table id="alert-table">
          <thead>
            <tr>
              <th>Occurred At</th>
              <th>Alert Type</th>
              <th>Resolution</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="isLoadingAlerts">
              <td colspan="3" class="table-message">데이터를 불러오는 중입니다...</td>
            </tr>
            <tr v-else-if="loadError">
              <td colspan="3" class="table-message error">{{ loadError }}</td>
            </tr>
            <tr v-else-if="!sortedAlerts.length">
              <td colspan="3" class="table-message">표시할 알림이 없습니다.</td>
            </tr>
            <template v-else>
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
                    {{ alert.isAcknowledged ? '조치 완료' : '대기 중' }}
                  </span>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </section>
    </main>

    <div v-if="isModalOpen" class="modal-backdrop" @click.self="closeModal">
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modal-header">
          <div class="modal-heading">
            <div v-if="currentModalAlert" :class="['badge', currentModalAlert.type]">
              {{ currentModalAlert.type.toUpperCase() }}
            </div>
            <div class="modal-title">
              Alert Details
              <span v-if="currentModalAlert"> · {{ currentModalAlert.id }}</span>
            </div>
          </div>
          <button class="secondary" type="button" @click="closeModal">Close</button>
        </div>
        <div v-if="currentModalAlert" class="modal-body">
          <div class="meta">
            <span>{{ currentModalAlert.occurredAt }}</span>
            <span class="meta-divider">·</span>
            <span>{{ currentModalAlert.type.toUpperCase() }}</span>
          </div>
          <div class="section">
            <div class="section-title">Message</div>
            <div class="section-content">{{ currentModalAlert.message }}</div>
          </div>
          <div class="section">
            <div class="section-title">AI Recommendation</div>
            <div class="section-content">{{ currentModalAlert.recommendation }}</div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="secondary" type="button" @click="closeModal">Cancel</button>
          <button
            type="button"
            :disabled="currentModalAlert?.isAcknowledged"
            class="primary"
            :class="{ completed: currentModalAlert?.isAcknowledged }"
            @click="acknowledgeCurrentAlert"
          >
            {{ currentModalAlert?.isAcknowledged ? '조치 완료됨' : '조치 완료' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="isToastVisible" class="toast">
      <div class="toast-content">
        <div class="toast-title">New Alert Received</div>
        <div class="subtitle">{{ toastMessage }}</div>
        <button type="button" @click="openModalFromToast">Open the alert</button>
      </div>
    </div>
  </div>
</template>
