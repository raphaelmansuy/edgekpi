import { defineConfig } from '@playwright/test'
import path from 'node:path'

const repo = path.resolve(import.meta.dirname, '../..')
const python = process.env.EDGEKPI_PYTHON ?? path.join(repo, '.venv/bin/python')

export default defineConfig({
  testDir: './e2e/tests',
  outputDir: './e2e/.results',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    viewport: { width: 1440, height: 900 },
    channel: 'chrome',
    colorScheme: 'light',
    reducedMotion: 'reduce',
    trace: 'off',
  },
  webServer: [
    {
      command: `${python} -m edgekpi.server --port 8765`,
      cwd: repo,
      url: 'http://127.0.0.1:8765/api/catalogue',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: { PYTHONDONTWRITEBYTECODE: '1' },
    },
    {
      command: 'npm run build && npm run preview',
      cwd: import.meta.dirname,
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
})
