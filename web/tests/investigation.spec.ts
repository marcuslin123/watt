import { expect, test } from "@playwright/test";

test("live investigation verifies the three solar drivers and survives reload", async ({ page }) => {
  test.skip(process.env.WATT_RUN_LIVE !== "1", "Requires local investigator worker and ChatGPT authentication");
  test.setTimeout(150_000);
  await page.goto("/");
  await page.getByRole("button", {name:"Refresh snapshot"}).click();
  await page.getByRole("button", {name:"Investigate Solar"}).click();
  await expect(page.getByRole("heading",{name:"Margin investigation"})).toBeVisible();
  await expect(page.getByTestId("run-status")).toHaveText("completed",{timeout:120_000});
  await expect(page.getByRole("heading",{name:"Prior-period settlement charge"})).toBeVisible();
  await expect(page.getByRole("heading",{name:"Higher export credits under one solar plan"})).toBeVisible();
  await expect(page.getByRole("heading",{name:"Lower recorded imports; cause unresolved"})).toBeVisible();
  await expect(page.getByText("Check posted adjustments · complete")).toBeVisible();
  await page.getByRole("button",{name:"December ancillary service settlement"}).click();
  await expect(page.getByText(/November service posted in December/)).toBeVisible();
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
  await page.getByLabel("Question",{exact:true}).fill("Did they move out?");
  await page.getByRole("button",{name:"Ask Watt"}).click();
  await expect(page.getByRole("region",{name:"Investigation follow-up"}).getByText("unresolved",{exact:true})).toBeVisible();
  await page.getByRole("button",{name:"Compare scenarios"}).click();
  await expect(page.getByTestId("scenario-incremental")).toHaveText("$420.00");
  await expect(page.getByText(/Break-even at 77.46%/)).toBeVisible();
  await page.getByRole("region",{name:"Retention scenario"}).screenshot({path:"test-results/retention.png"});
  await page.getByLabel("Stay probability with offer (%)").fill("70");
  await page.getByRole("button",{name:"Compare scenarios"}).click();
  await expect(page.getByTestId("scenario-incremental")).toHaveText("-$1,230.00");
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
