import { describe, it, expect } from 'vitest'
import { buildApiBase } from '../src/utils/dashboard'

const DASHBOARD_ENDPOINT = '/dashboard/send'

describe('Dashboard API integration (requires running backend)', () => {
  it('loads dashboard alerts via fetch', async () => {
    const host = import.meta.env.FASTAPI_LOCAL_URL ?? 'http://127.0.0.1'
    const port = import.meta.env.FASTAPI_DEV_SERVER_PORT ?? '8000'
    const basePath = import.meta.env.VUE_API_BASE_PATH ?? '/dashboard'
    const base = buildApiBase(host, port, basePath)
    const response = await fetch(`${base.replace(/\/$/, '')}/send`)
    expect(response.ok).toBe(true)
    const data = await response.json()
    expect(Array.isArray(data)).toBe(true)
    if (data.length > 0) {
      const first = data[0]
      expect(first).toHaveProperty('id')
      expect(first).toHaveProperty('message')
    }
  })
})
