import { expect, test, type Page } from "@playwright/test";

async function beat(page: Page) {
  // Recording pace only; every state transition is verified by assertions.
  if (process.env.WATT_RECORD === "1") await page.waitForTimeout(1600);
}

test("live investigation verifies the three solar drivers and survives reload", async ({ page }) => {
  test.skip(process.env.WATT_RUN_LIVE !== "1", "Requires local investigator worker and ChatGPT authentication");
  test.setTimeout(150_000);
  await page.goto("/");
  await expect(page.getByTestId("reported-total")).toHaveText("$571,322.95");
  await beat(page);
  await page.getByRole("button", {name:"Refresh snapshot"}).click();
  await expect(page.getByTestId("reported-total")).toHaveText("$570,322.95");
  await page.getByRole("button", {name:"Browse Solar contracts"}).click();
  await page.getByRole("button", {name:"contract-00000",exact:true}).click();
  await expect(page.getByRole("row", {name:/Dec 2025/})).toContainText("$29.00");
  await beat(page);
  await page.getByRole("button", {name:"Back to portfolio"}).click();
  await page.getByRole("button", {name:"Clear group"}).click();
  await page.getByRole("button", {name:"Investigate Solar"}).scrollIntoViewIfNeeded();
  await beat(page);
  await page.getByRole("button", {name:"Investigate Solar"}).click();
  await expect(page.getByRole("heading",{name:"Margin investigation"})).toBeVisible();
  await expect(page.getByTestId("run-status")).toHaveText("completed",{timeout:120_000});
  await expect(page.getByRole("heading",{name:"Prior-period settlement charge"})).toBeVisible();
  await expect(page.getByRole("heading",{name:"Higher export credits under one solar plan"})).toBeVisible();
  await expect(page.getByRole("heading",{name:"Lower recorded imports; cause unresolved"})).toBeVisible();
  await expect(page.getByText("Check posted adjustments · complete")).toBeVisible();
  await page.getByRole("button",{name:"December ancillary service settlement"}).click();
  await expect(page.getByText(/November service posted in December/)).toBeVisible();
  await beat(page);
  await page.getByRole("button",{name:"ERCOT RTC+B implementation notice"}).click();
  await expect(page.getByRole("link",{name:"Open public source"})).toHaveAttribute("href", /ercot\.com/);
  await beat(page);
  await page.reload();
  await expect(page.getByTestId("run-status")).toHaveText("completed");
  await page.getByRole("button",{name:"December ancillary service settlement"}).click();
  await page.screenshot({path:"test-results/investigation.png",fullPage:true});
  const original = page.url();
  await page.getByText("Attach analyst evidence", {exact:true}).click();
  await page.getByLabel("Record date").fill("2025-12-15");
  await page.getByLabel("Source", {exact:true}).fill("Synthetic service note");
  await page.getByLabel("What does the record show?").fill("This example record states that service ended on December 15.");
  await page.getByRole("button",{name:"Save evidence as revision"}).click();
  await expect(page.getByText("Analyst evidence recorded; original run preserved")).toBeVisible();
  const revision = page.url();
  expect(revision).not.toBe(original);
  await page.getByRole("button",{name:"Synthetic service note"}).click();
  await expect(page.getByText(/analyst supplied · contract-00000 · 2025-12-15/)).toBeVisible();
  await beat(page);
  await page.getByLabel("Question",{exact:true}).fill("Did they move out?");
  await page.getByRole("button",{name:"Ask Watt"}).click();
  await expect(page.getByRole("region",{name:"Investigation follow-up"}).getByText("unresolved",{exact:true})).toBeVisible();
  await page.getByRole("button",{name:"Compare scenarios"}).click();
  await expect(page.getByTestId("scenario-incremental")).toHaveText("$420.00");
  await expect(page.getByText(/Break-even at 77.46%/)).toBeVisible();
  await page.getByRole("region",{name:"Retention scenario"}).screenshot({path:"test-results/retention.png"});
  await beat(page);
  await page.getByLabel("Stay probability with offer (%)").fill("70");
  await page.getByRole("button",{name:"Compare scenarios"}).click();
  await expect(page.getByTestId("scenario-incremental")).toHaveText("-$1,230.00");
  await beat(page);
  await page.getByRole("button",{name:"Open parent run"}).click();
  await expect(page).toHaveURL(original);
  await expect(page.getByRole("button",{name:"Synthetic service note"})).toHaveCount(0);
});

test("a partial result does not read as a completed investigation", async ({ page }) => {
  await page.route("**/api/investigations/demo-partial",route=>route.fulfill({json:{
    id:"demo-partial",status:"partial",scope:{snapshot:"refreshed",month:"2025-12-01",group:"solar"},
    findings:[],events:[],message:"Five-minute investigation limit reached"
  }}));
  await page.goto("/?run=demo-partial");
  await expect(page.getByTestId("run-status")).toHaveText("partial");
  await expect(page.getByText("Five-minute investigation limit reached")).toBeVisible();
  await expect(page.getByRole("button",{name:"Run again"})).toBeVisible();
});

test("a failed run shows the authentication remedy and no fabricated findings", async ({ page }) => {
  await page.route("**/api/investigations/demo-failed",route=>route.fulfill({json:{
    id:"demo-failed",status:"failed",scope:{snapshot:"refreshed",month:"2025-12-01",group:"solar"},
    findings:[],events:[],message:"Sign into Codex using ChatGPT before running investigations"
  }}));
  await page.goto("/?run=demo-failed");
  await expect(page.getByTestId("run-status")).toHaveText("failed");
  await expect(page.getByText("Sign into Codex using ChatGPT before running investigations")).toBeVisible();
  await expect(page.getByText("No verified findings published yet.")).toBeVisible();
  await expect(page.getByRole("region",{name:"Retention scenario"})).toHaveCount(0);
});
