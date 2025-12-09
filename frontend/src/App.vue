<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

/** @typedef {'warning' | 'alarm'} AlertType */

/**
 * @typedef {Object} Alert
 * @property {string} id
 * @property {string} occurredAt
 * @property {AlertType} type
 * @property {string} message
 * @property {string} recommendation
 * @property {boolean} isAcknowledged
 */

const TOAST_DURATION_MS = 7000;
const ALERT_STREAM_DELAY_MS = 4000;

/** @type {Alert[]} */
const INITIAL_ALERTS = [
  {
    id: 'a-001',
    occurredAt: '2025-12-04 10:15:23',
    type: 'warning',
    message: 'CPU usage has stayed above 80% for the last 10 minutes.',
    recommendation: 'Review the top CPU processes and scale the workload within 5 minutes.',
    isAcknowledged: false,
  },
  {
    id: 'a-002',
    occurredAt: '2025-12-04 09:58:41',
    type: 'alarm',
    message: 'Application response latency breached the 4.5s threshold.',
    recommendation: 'Check the most recent deployment and inspect critical APM traces.',
    isAcknowledged: false,
  },
  {
    id: 'a-003',
    occurredAt: '2025-12-04 09:12:05',
    type: 'warning',
    message: 'Disk usage is at 70% and climbing steadily.',
    recommendation: 'Rotate log files and evaluate short-term storage expansion.',
    isAcknowledged: false,
  },
];

const cloneAlert = (alert) => ({
  ...alert,
  isAcknowledged: Boolean(alert.isAcknowledged),
});

const toLastUpdatedCopy = () => `Last updated: ${new Date().toLocaleString('ko-KR')}`;

const useAlertDashboard = () => {
  const alerts = ref(INITIAL_ALERTS.map(cloneAlert));
  const lastUpdated = ref('Waiting for updates...');

  const sortedAlerts = computed(() =>
    [...alerts.value].sort(
      (first, second) => new Date(second.occurredAt) - new Date(first.occurredAt),
    ),
  );

  const touchLastUpdated = () => {
    lastUpdated.value = toLastUpdatedCopy();
  };

  const addAlert = (incomingAlert) => {
    if (alerts.value.some((alert) => alert.id === incomingAlert.id)) {
      return null;
    }

    const nextAlert = cloneAlert({ ...incomingAlert, isAcknowledged: false });
    alerts.value.unshift(nextAlert);
    touchLastUpdated();
    return nextAlert;
  };

  const acknowledgeAlert = (alertId) => {
    const target = alerts.value.find((alert) => alert.id === alertId);
    if (!target || target.isAcknowledged) {
      return false;
    }

    target.isAcknowledged = true;
    touchLastUpdated();
    return true;
  };

  return {
    alerts,
    sortedAlerts,
    lastUpdated,
    addAlert,
    acknowledgeAlert,
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

  const showToast = (alert) => {
    toastMessage.value = `${alert.occurredAt} · ${alert.message}`;
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

const { sortedAlerts, lastUpdated, addAlert, acknowledgeAlert, touchLastUpdated } =
  useAlertDashboard();
const { currentModalAlert, isModalOpen, openModal, closeModal } = useModalController();
const { toastMessage, isToastVisible, showToast, hideToast } = useToast();

const acknowledgeCurrentAlert = () => {
  if (!currentModalAlert.value) {
    return;
  }

  const acknowledged = acknowledgeAlert(currentModalAlert.value.id);
  if (!acknowledged) {
    return;
  }

  currentModalAlert.value.isAcknowledged = true;
};

const handleIncomingAlert = (incomingAlert) => {
  const alert = addAlert(incomingAlert);
  if (alert) {
    showToast(alert);
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
  touchLastUpdated();

  setTimeout(() => {
    handleIncomingAlert({
      id: 'a-004',
      occurredAt: new Date().toLocaleString('ko-KR'),
      type: 'alarm',
      message: 'Database read latency exceeded 400ms on P99.',
      recommendation: 'Scale read replicas and inspect slow queries immediately.',
    });
  }, ALERT_STREAM_DELAY_MS);
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
                  {{ alert.isAcknowledged ? 'Completed' : 'Pending' }}
                </span>
              </td>
            </tr>
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
            {{ currentModalAlert?.isAcknowledged ? 'Acknowledged' : 'Acknowledge Alert' }}
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
