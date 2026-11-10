import react from '@vitejs/plugin-react'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Overridden by scripts that run a throwaway backend beside the developer's own.
      '/api': loadEnv(mode, '.', 'API_PROXY_').API_PROXY_TARGET ?? 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      include: ['src/utils/**', 'src/store/**', 'src/hooks/useCopilot.ts', 'src/lib/api.ts'],
      exclude: ['src/**/*.test.ts'],
      reporter: ['text-summary', 'text'],
      thresholds: { 'src/utils/**': { lines: 70, functions: 70, branches: 70, statements: 70 } },
    },
  },
}))
