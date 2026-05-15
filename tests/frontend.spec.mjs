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
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.locator(".card").first()).toBeVisible();
});

test("loads readable monthly AI news cards", async ({ page }) => {
  await expect(page.locator(".top-briefing")).toBeVisible();
  await expect(page.locator(".top-card")).toHaveCount(10);
  await expect(page.locator("#sourceHealth")).toContainText("\u6765\u6e90\u5065\u5eb7");
  await expect(page.locator("#sourceHealth")).toContainText("\u7cbe\u9009\u515c\u5e95");
  await expect(page.locator(".card h3").first()).toBeVisible();
  await expect(page.locator(".card")).toHaveCountGreaterThan(30);
  await expect(page.locator(".reading-actions").first()).toBeVisible();
  await expect(page.locator(".brief-grid").first()).toBeVisible();
  await expect(page.locator(".key-points").first()).toBeVisible();
  await expect(page.locator(".visual").first()).toBeVisible();
  await expect(page.locator(".chip").filter({ hasText: /\u6280\u672f\u66f4\u65b0|\u91cd\u8981\u529f\u80fd\u66f4\u65b0|AI\u5e94\u7528\u65b9\u6cd5/ }).first()).toBeVisible();
  await expect(page.locator(".read-more-note").first()).toContainText("\u5982\u679c\u611f\u5174\u8da3\u8bf7\u70b9\u51fb\u67e5\u770b\u539f\u6587");
  await expect(page.locator(".original-title")).toHaveCount(0);
  await expect(page.locator("#kpiTotal")).not.toHaveText("-");
});

test("filters A-grade sources", async ({ page }) => {
  await page.selectOption("#gradeFilter", "A");
  await page.click("#applyBtn");
  await expect(page.locator(".card").first()).toBeVisible();
  await expect(page.locator(".card").filter({ hasNotText: "A\u7ea7\u4fe1\u6e90" })).toHaveCount(0);
});

test("filters creator articles", async ({ page }) => {
  await page.selectOption("#categoryFilter", "\u6838\u5fc3AI\u535a\u4e3b");
  await page.click("#applyBtn");
  await expect(page.locator(".card").first()).toContainText("\u6838\u5fc3AI\u535a\u4e3b");
});

test("source, date, search and reset work", async ({ page }) => {
  const initialCount = await page.locator(".card").count();
  await page.selectOption("#sourceFilter", { index: 1 });
  await expect(page.locator(".card")).toHaveCount(initialCount);
  await page.click("#applyBtn");
  await expect(page.locator(".card").first()).toBeVisible();

  await page.click('[data-days="7"]');
  await expect(page.locator('[data-days="7"]')).toHaveClass(/active/);
  await expect(page.locator(".card").first()).toBeVisible();
  await page.click("#applyBtn");
  await expect(page.locator(".card").first()).toBeVisible();

  await page.fill("#startDateFilter", "2099-01-01");
  await page.fill("#endDateFilter", "2099-01-02");
  await expect(page.locator(".card").first()).toBeVisible();
  await page.click("#applyBtn");
  await expect(page.locator(".empty")).toBeVisible();

  await page.click("#resetBtn");
  await page.fill("#searchInput", "OpenAI");
  await expect(page.locator(".card")).toHaveCountGreaterThan(20);
  await page.click("#applyBtn");
  await expect(page.locator(".card").first()).toContainText(/OpenAI/i);

  await page.click("#resetBtn");
  await expect(page.locator("#categoryFilter")).toHaveValue("all");
  await expect(page.locator("#sourceFilter")).toHaveValue("all");
  await expect(page.locator("#readingFilter")).toHaveValue("all");
  await expect(page.locator('[data-days="year"]')).toHaveClass(/active/);
  await expect(page.locator("#searchInput")).toHaveValue("");
  await expect(page.locator(".card")).toHaveCountGreaterThan(30);
});

test("practice category remains usable", async ({ page }) => {
  await page.selectOption("#categoryFilter", "Vibe/Prompt/Agent\u5b9e\u6218");
  await page.click("#applyBtn");
  await expect(page.locator(".card").first()).toContainText("Vibe/Prompt/Agent\u5b9e\u6218");
});

test("date fields use native date picker controls", async ({ page }) => {
  await expect(page.locator("#startDateFilter")).toHaveAttribute("type", "date");
  await expect(page.locator("#endDateFilter")).toHaveAttribute("type", "date");
  await expect(page.locator('[data-target="startDateFilter"]')).toBeVisible();
  await expect(page.locator('[data-target="endDateFilter"]')).toBeVisible();
});

test("source health details and reading state persist", async ({ page }) => {
  await page.click("#sourceHealthToggle");
  await expect(page.locator("#sourceHealthPanel")).toBeVisible();
  await expect(page.locator(".source-health-row").filter({ hasText: "AI\u4e2a\u4eba\u516c\u53f8\u5927\u795e" }).first()).toBeVisible();

  const firstTitle = await page.locator(".card h3").first().innerText();
  await page.locator(".card").first().locator('[data-state="read"]').click();
  await page.locator(".card").first().locator('[data-state="favorite"]').click();
  await page.locator(".card").first().locator('[data-state="later"]').click();
  await expect(page.locator(".card").first()).toHaveClass(/is-read/);

  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.locator(".card h3").first()).toContainText(firstTitle.slice(0, 12));
  await expect(page.locator(".card").first().locator('[data-state="read"]')).toHaveClass(/active/);

  await page.selectOption("#readingFilter", "favorite");
  await page.click("#applyBtn");
  await expect(page.locator(".card").first()).toContainText(firstTitle.slice(0, 12));

  await page.selectOption("#readingFilter", "later");
  await page.click("#applyBtn");
  await expect(page.locator(".card").first()).toContainText(firstTitle.slice(0, 12));
});

test("desktop layout keeps filters left of stream", async ({ page }) => {
  const filterBox = await page.locator(".filters").boundingBox();
  const streamBox = await page.locator(".stream").boundingBox();
  expect(filterBox).not.toBeNull();
  expect(streamBox).not.toBeNull();
  expect(filterBox.x).toBeLessThan(streamBox.x);
});
