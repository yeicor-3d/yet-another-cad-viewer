import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 120000,
  expect: {
    timeout: 30000,
  },
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [["list"], ["json", { outputFile: "test-results/e2e-results.json" }], ["html", { outputFolder: "playwright-report" }]],
  use: {
    baseURL: "http://localhost:32323",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 30000,
    navigationTimeout: 60000,
  },
  webServer: [
    {
      command: "bash -c 'YACV_GRACEFUL_SECS_CONNECT=0 YACV_GRACEFUL_SECS_WORK=10 exec .venv/bin/python e2e/yacv_server_launcher.py'",
      port: 32323,
      timeout: 30000,
      reuseExistingServer: !process.env.CI,
      cwd: ".",
    },
  ],
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
        launchOptions: {
          args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        },
      },
    },
  ],
});
