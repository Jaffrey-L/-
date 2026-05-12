import { expect, test } from "@playwright/test";

expect.extend({
  async toHaveCountGreaterThan(locator, expected) {
    const actual = await locator.count();
    return {
      pass: actual > expected,
      message: () => `expected count ${actual} to be greater than ${expected}`
    };
  }
});

test.beforeEach(async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });
});

test("loads readable monthly AI news cards", async ({ page }) => {
  await expect(page.locator(".card h3").first()).toBeVisible();
  await expect(page.locator(".card")).toHaveCountGreaterThan(20);
  await expect(page.locator(".key-points").first()).toBeVisible();
  await expect(page.locator(".visual").first()).toBeVisible();
  await expect(page.locator("#kpiTotal")).not.toHaveText("-");
});

test("filters A-grade sources", async ({ page }) => {
  await page.selectOption("#gradeFilter", "A");
  await expect(page.locator(".card").first()).toBeVisible();
  await expect(page.locator(".card").filter({ hasNotText: "A级信源" })).toHaveCount(0);
});

test("filters creator articles", async ({ page }) => {
  await page.selectOption("#categoryFilter", "核心AI博主");
  await expect(page.locator(".card").first()).toContainText("核心AI博主");
});

test("time filter, search and reset work", async ({ page }) => {
  await page.selectOption("#timeFilter", "7");
  await expect(page.locator(".card").first()).toBeVisible();

  await page.fill("#searchInput", "OpenAI");
  await expect(page.locator(".card").first()).toContainText(/OpenAI/i);

  await page.click("#resetBtn");
  await expect(page.locator("#categoryFilter")).toHaveValue("all");
  await expect(page.locator("#timeFilter")).toHaveValue("30");
  await expect(page.locator("#searchInput")).toHaveValue("");
  await expect(page.locator(".card")).toHaveCountGreaterThan(20);
});

test("practice category remains usable", async ({ page }) => {
  await page.selectOption("#categoryFilter", "Vibe/Prompt/Agent实战");
  await expect(page.locator(".card").first()).toContainText("Vibe/Prompt/Agent实战");
});

test("desktop layout keeps filters left of stream", async ({ page }) => {
  const filterBox = await page.locator(".filters").boundingBox();
  const streamBox = await page.locator(".stream").boundingBox();
  expect(filterBox).not.toBeNull();
  expect(streamBox).not.toBeNull();
  expect(filterBox.x).toBeLessThan(streamBox.x);
});
