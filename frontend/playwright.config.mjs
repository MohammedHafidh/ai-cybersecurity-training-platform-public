import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './browser',
  use: { baseURL: 'http://localhost:5173' },
  webServer: {
    command: 'npm run preview -- --host localhost --port 5173 --strictPort',
    url: 'http://localhost:5173',
  },
})
