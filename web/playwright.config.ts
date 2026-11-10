import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  workers: 1,
  timeout: 60_000,
  use: { ...devices["Desktop Chrome"], baseURL: "http://127.0.0.1:3000", trace: "retain-on-failure",
    video: process.env.WATT_RECORD === "1" ? {mode:"on",size:{width:1280,height:720}} : "off" },
  webServer: [
    { command: ".venv/bin/python -m uvicorn watt.api:app --host 127.0.0.1 --port 8000", cwd: "..", url: "http://127.0.0.1:8000/api/health", reuseExistingServer: !process.env.CI },
    { command: "npm run dev -- --hostname 127.0.0.1", url: "http://127.0.0.1:3000", reuseExistingServer: !process.env.CI }
  ]
});
