const stripQuotes = (value = '') => String(value || '').trim().replace(/^['"]|['"]$/g, '');

const normalizeHost = (host = '') => {
  const trimmed = stripQuotes(host);
  if (!trimmed) return 'http://localhost';
  return trimmed.replace(/\/$/, '');
};

const normalizePath = (path = '') => {
  const normalized = stripQuotes(path);
  if (!normalized) return '/';
  return normalized.startsWith('/') ? normalized : `/${normalized}`;
};

export const buildApiBase = (host, port, path = '/') => {
  const safeHost = normalizeHost(host);
  const safePort = stripQuotes(port);
  const base = safePort ? `${safeHost}:${safePort}` : safeHost;
  return `${base}${normalizePath(path)}`;
};

export const buildEndpoint = (base, suffix = '') => {
  const safeBase = normalizeHost(base);
  let normalizedSuffix = stripQuotes(suffix || '');
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
  const resolvedTimestamp =
    rawAlert.timestamp ??
    rawAlert.occurredAt ??
    rawAlert.occurred_at ??
    new Date().toLocaleString('ko-KR');

  const normalizeType = () => {
    const value = String(rawAlert.type || '').toUpperCase();
    if (value === 'ALARM') {
      return { typeClass: 'alarm', typeLabel: 'ALARM' };
    }
    if (value === 'WARN') {
      return { typeClass: 'warning', typeLabel: 'WARN' };
    }
    if (value === 'WARNING') {
      return { typeClass: 'warning', typeLabel: 'WARN' };
    }
    return { typeClass: 'warning', typeLabel: value || 'WARN' };
  };
  const { typeClass, typeLabel } = normalizeType();

  return {
    id: String(rawAlert.id ?? fallbackId),
    occurredAt: resolvedTimestamp,
    timestamp: resolvedTimestamp,
    type: typeClass,
    typeLabel,
    message: rawAlert.message ?? '',
    recommendation: rawAlert.recommendation ?? rawAlert.mannual ?? '',
    isAcknowledged: Boolean(
      rawAlert.isAcknowledged ?? rawAlert.ishandled ?? rawAlert.is_handled ?? false,
    ),
  };
};
