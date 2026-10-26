import { expect, test } from "@playwright/test";

const E2E_USERNAME = "e2e_alice";
const E2E_PASSWORD = "E2E_Test_123!";
const E2E_MESSAGE = "Mesaj E2E din Playwright";
const RECOMMENDED_ALBUM_TITLE = "E2E Album Aurora";

test("auth, messaging and recommendations work end-to-end", async ({
  page,
}) => {
  await page.goto("/login");

  await page.getByLabel(/username/i).fill(E2E_USERNAME);
  await page.getByLabel(/password/i).fill(E2E_PASSWORD);
  await page.getByRole("button", { name: "Login", exact: true }).click();

  await expect(page).toHaveURL(/\/$/);
  await page.goto("/messages");

  await expect(page.getByText("Conversații")).toBeVisible();

  const friendItem = page
    .locator(".conversation-item")
    .filter({ hasText: "e2e_bob" })
    .first();
  await expect(friendItem).toBeVisible();
  await friendItem.click();

  await expect(page.locator(".chat-header")).toHaveText("e2e_bob");
  await page.locator(".chat-input").fill(E2E_MESSAGE);
  await page.getByRole("button", { name: /trimite/i }).click();

  await expect(
    page.locator(".message-bubble", { hasText: E2E_MESSAGE }),
  ).toBeVisible();

  await page.goto("/recommendations");
  await expect(
    page.getByRole("heading", { name: /Recomandări muzicale/i }),
  ).toBeVisible();
  await expect(page.getByText(RECOMMENDED_ALBUM_TITLE)).toBeVisible();
});
