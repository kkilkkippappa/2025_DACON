const normalizeHost = (host = '') => {
  const trimmed = String(host || '').trim();
  if (!trimmed) return 'http://localhost';
  return trimmed.replace(/\/$/, '');
};

const normalizePath = (path = '') => {
  if (!path) return '/';
  return path.startsWith('/') ? path : `/${path}`;
};

export const buildApiBase = (host, port, path = '/') => {
  const safeHost = normalizeHost(host);
  const safePort = String(port ?? '').trim();
  const base = safePort ? `${safeHost}:${safePort}` : safeHost;
  return `${base}${normalizePath(path)}`;
};

export const buildEndpoint = (base, suffix = '') => {
  const safeBase = normalizeHost(base);
  let normalizedSuffix = suffix || '';
  if (!normalizedSuffix.startsWith('/')) {
    normalizedSuffix = `/${normalizedSuffix}`;
  }
  return `${safeBase}${normalizedSuffix}`;
};

export const sanitizeAlert = (rawAlert = {}) => {
  const fallbackId =
    typeof globalThis.crypto?.randomUUID === 'function'
      ? globalThis.crypto.randomUUID()
      : `alert-${Date.now()}`;

  return {
    id: String(rawAlert.id ?? fallbackId),
    occurredAt:
      rawAlert.occurredAt ??
      rawAlert.occurred_at ??
      new Date().toLocaleString('ko-KR'),
    type: rawAlert.type ?? 'warning',
    message: rawAlert.message ?? '',
    recommendation: rawAlert.recommendation ?? rawAlert.mannual ?? '',
    isAcknowledged: Boolean(
      rawAlert.isAcknowledged ?? rawAlert.ishandled ?? rawAlert.is_handled ?? false,
    ),
  };
};
