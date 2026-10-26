import { test, expect } from "@playwright/test";

test("home page loads discovery content", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("main")).toContainText("Găsește rapid albume");
});
