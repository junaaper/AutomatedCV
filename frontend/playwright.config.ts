import { defineConfig, devices } from '@playwright/test'

// End-to-end tests drive the real frontend against the real backend, with the backend's
// LLM and embeddings switched to the offline fakes so runs are fast, free and deterministic.
//   CI:    starts both servers itself (see .github/workflows/ci.yml)
//   Local: E2E_BACKEND_CMD="python -m uv run python run.py" E2E_DATABASE_URL=... npx playwright test

const backendEnv: Record<string, string> = {
  LLM_PROVIDER: 'fake',
  EMBED_PROVIDER: 'fake',
  ENVIRONMENT: 'test',
}
if (process.env.E2E_DATABASE_URL) backendEnv.DATABASE_URL = process.env.E2E_DATABASE_URL

export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } }],
  webServer: [
    {
      command: process.env.E2E_BACKEND_CMD ?? 'uv run python run.py',
      cwd: '../backend',
      url: 'http://127.0.0.1:8000/healthz',
      env: backendEnv,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
})
