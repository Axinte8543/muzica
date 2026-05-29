import { test, expect } from "@playwright/test";

test("home page loads and shows loading fallback", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("text=Se încarcă")).toBeVisible();
});
