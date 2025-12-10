import { describe, it, expect } from 'vitest'

const DASHBOARD_ENDPOINT = '/dashboard/send'

describe('Dashboard API integration (requires running backend)', () => {
  it('loads dashboard alerts via fetch', async () => {
    const response = await fetch(`${import.meta.env.FASTAPI_LOCAL_URL}:${import.meta.env.FASTAPI_DEV_SERVER_PORT}${DASHBOARD_ENDPOINT}`)
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
