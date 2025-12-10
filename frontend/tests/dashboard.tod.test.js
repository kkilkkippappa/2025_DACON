import { describe, it, expect } from 'vitest'
import { buildApiBase, buildEndpoint, sanitizeAlert } from '../src/utils/dashboard'

describe('TOD Frontend Smoke Tests', () => {
  it('buildApiBase combines host, port, and path safely', () => {
    const endpoint = buildApiBase('http://localhost/', '8000', 'dashboard')
    expect(endpoint).toBe('http://localhost:8000/dashboard')
  })

  it('buildEndpoint appends suffix with single slash', () => {
    const base = 'http://localhost:8000/dashboard'
    expect(buildEndpoint(base, 'alerts')).toBe('http://localhost:8000/dashboard/alerts')
    expect(buildEndpoint(`${base}/`, '/health')).toBe('http://localhost:8000/dashboard/health')
  })

  it('sanitizeAlert fills defaults and normalizes flags/type/timestamp', () => {
    const alert = sanitizeAlert({
      id: 10,
      type: 'ALARM',
      message: 'hi',
      ishandled: 1,
      timestamp: '2025-12-10 12:00:00'
    })
    expect(alert.id).toBe('10')
    expect(alert.type).toBe('alarm')
    expect(alert.typeLabel).toBe('ALARM')
    expect(alert.timestamp).toBe('2025-12-10 12:00:00')
    expect(alert.isAcknowledged).toBe(true)
    expect(alert.message).toBe('hi')
    expect(alert.recommendation).toBe('')
  })
})
