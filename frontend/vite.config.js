import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const devPort = Number(env.VUE_DEV_SERVER_PORT ?? 3000)
  const apiPath = env.VUE_API_BASE_PATH ?? '/dashboard'
  const apiHost = env.FASTAPI_LOCAL_URL ?? 'http://localhost'
  const apiPort = env.FASTAPI_DEV_SERVER_PORT ?? '8000'
  const apiTarget = `${apiHost.replace(/\/$/, '')}:${apiPort}`

  return {
    plugins: [vue()],
    server: {
      port: devPort,
      open: true,
      proxy: {
        [apiPath]: {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
