import { defineConfig, devices } from '@playwright/test';

/**
 * Конфигурация E2E тестов Playwright
 *
 * Тестирует полный рабочий процесс пользователя для анализа резюме:
 * - Навигация и отрисовка страниц
 * - Загрузка резюме (PDF/DOCX)
 * - Отображение результатов анализа
 * - Функциональность сравнения вакансий
 *
 * Базовый URL по умолчанию соответствует локальному серверу разработки.
 * Используйте переменную окружения BASE_URL для тестирования различных окружений.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['list'],
    ['json', { outputFile: 'test-results/e2e-results.json' }],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
