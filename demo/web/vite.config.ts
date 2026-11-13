import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

const api = { '/api': { target: 'http://127.0.0.1:8765', changeOrigin: false } }

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: api },
  preview: { port: 4173, proxy: api },
  test: { include: ['src/**/*.test.ts'], environment: 'node' },
})
