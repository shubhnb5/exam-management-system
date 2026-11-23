import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE_PATH || '/',
  build: {
    // Students use all kinds of phones. Vite's default target (~Chrome 107 /
    // Safari 16) would give older phones — e.g. iPhones stuck on iOS 15 — a
    // blank page, so compile down to browsers from ~2020.
    target: ['es2020', 'chrome87', 'safari14', 'firefox78', 'edge88'],
  },
  server: {
    port: 5175,
    strictPort: false,
    host: true,
    // Same pattern as the scanner: in dev, /api is proxied to the backend so
    // the portal also works when opened from a phone on the local network.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
