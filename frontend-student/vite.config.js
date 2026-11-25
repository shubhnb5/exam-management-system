import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],

    base: env.VITE_BASE_PATH || '/student/',

    build: {
      target: [
        'es2020',
        'chrome87',
        'safari14',
        'firefox78',
        'edge88',
      ],
    },

    server: {
      port: 5175,
      strictPort: false,
      host: true,

      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})