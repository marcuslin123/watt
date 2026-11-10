import { expect, test } from "@playwright/test";

test("snapshot and contract API reconcile to the seeded reporting views", async ({ request }) => {
  const initial = await request.get("/api/portfolio?snapshot=initial");
  expect(initial.ok()).toBeTruthy();
  expect(await initial.json()).toMatchObject({ month: "2025-11-01", reported: 57132295 });
  const refreshed = await request.get("/api/portfolio?snapshot=refreshed");
  expect(refreshed.ok()).toBeTruthy();
  const data = await refreshed.json();
  expect(data).toMatchObject({ month: "2025-12-01", reported: 57032295, normalized: 57122295, delta: -100000 });
  expect(Object.fromEntries(data.groups.map((g: {group:string; delta:number}) => [g.group, g.delta])))
    .toEqual({ high_winter: 220000, low_winter: -80000, solar: -240000 });
  expect((await request.get("/api/portfolio?snapshot=initial&month=2025-12-01")).status()).toBe(404);
  const detail = await (await request.get("/api/contracts/contract-00000?snapshot=initial")).json();
  expect(detail.months).toHaveLength(23);
  expect(detail.months[0].month).toBe("2025-11-01");
  expect(detail.months.reduce((sum: number, row: {reported:number}) => sum + row.reported, 0)).toBe(detail.reported);
});

test("refresh, switch margin basis, and drill into a real contract", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Portfolio margins" })).toBeVisible();
  await expect(page.getByTestId("reported-total")).toHaveText("$571,322.95");
  await page.getByRole("button", { name: "Refresh snapshot" }).click();
  await expect(page.getByTestId("reported-total")).toHaveText("$570,322.95");
  await expect(page.getByRole("row", { name: /Solar/ })).toContainText("−$2,400.00");
  await page.getByRole("button", { name: "Normalized", exact: true }).click();
  await expect(page.getByTestId("reported-total")).toHaveText("$571,222.95");
  await page.getByRole("button", { name: "Reported", exact: true }).click();
  await page.getByRole("button", { name: "Browse Solar contracts" }).click();
  await page.getByRole("button", { name: "contract-00000", exact: true }).click();
  await expect(page.getByRole("heading", { name: "contract-00000", exact: true })).toBeVisible();
  await expect(page.getByRole("row", { name: /Dec 2025/ })).toBeVisible();
  await expect(page.getByText("24 / 24 months observed")).toBeVisible();
  await page.screenshot({ path: "test-results/contract.png", fullPage: true });
  await page.getByRole("button", { name: "Back to portfolio" }).click();
  await expect(page.getByRole("heading", { name: "Portfolio margins" })).toBeVisible();
  await page.getByRole("button", { name: "Clear group" }).click();
  await page.screenshot({ path: "test-results/portfolio.png", fullPage: true });
});

test("empty search preserves the selected snapshot and group", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", {name:"Browse Solar contracts"}).click();
  await page.getByRole("searchbox", { name: "Find contract" }).fill("no-such-contract");
  await expect(page.getByText("No contracts match this search.")).toBeVisible();
  await expect(page.getByTestId("reported-total")).toHaveText("$571,322.95");
});

test("a posted adjustment remains traceable in contract-month detail", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Refresh snapshot" }).click();
  await page.getByRole("button", { name: "Browse Solar contracts" }).click();
  await page.getByRole("searchbox", { name: "Find contract" }).fill("contract-00080");
  await page.getByRole("button", { name: "contract-00080", exact: true }).click();
  await page.getByRole("button", { name: "Dec 2025" }).click();
  await expect(page.getByText(/Settlement adjustment: \$45.00 · Nov 2025 service/)).toBeVisible();
  await page.getByRole("button", { name: "Normalized", exact: true }).click();
  await expect(page.getByText(/excluded from normalized margin/)).toBeVisible();
});
