import { test, expect } from "@playwright/test";

const API_BASE = process.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

test.describe("UX loading & accessibility", () => {
  test("shows skeleton loader while messages load and is responsive", async ({
    page,
  }) => {
    // Ensure app considers us authenticated
    await page.addInitScript(() => {
      localStorage.setItem("accessToken", "fake-access-token");
    });

    // Mock current user
    await page.route("**/api/auth/me/", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: 1, username: "e2e-user" }),
      }),
    );

    // Provide one conversation so we can select it
    await page.route("**/api/chat/conversations", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([{ user_id: 2, username: "Friend" }]),
      }),
    );

    // Provide friends list
    await page.route("**/api/friends/list**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          friends: { results: [{ id: 2, username: "Friend" }] },
        }),
      }),
    );

    // Intercept messages request and hold it paused so UI stays in loading state
    let pendingRoute = null as any;
    await page.route("**/api/chat/messages**", (route) => {
      pendingRoute = route;
      // do not continue/fulfill yet — this will keep the request pending
    });

    await page.goto("/");
    await page.goto(`/messages`);

    // Wait for conversations list item to appear
    const convItem = page.locator(".conversation-item").first();
    await expect(convItem).toBeVisible();

    // Set mobile viewport and click to open conversation
    await page.setViewportSize({ width: 390, height: 844 });
    await convItem.click();

    // While the messages request is pending, a skeleton container should be visible
    const skeleton = page.locator(".skeleton-container");
    await expect(skeleton).toBeVisible({ timeout: 2000 });

    // Now switch to desktop viewport and ensure skeleton stays visible and layout adapts
    await page.setViewportSize({ width: 1280, height: 800 });
    await expect(skeleton).toBeVisible();

    // Release the pending route with an empty messages list
    if (pendingRoute) {
      await pendingRoute.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    }

    // Skeleton should disappear after messages load
    await expect(skeleton).toHaveCount(0, { timeout: 2000 });
  });

  test("displays accessible error (role=alert) when friends API fails", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      localStorage.setItem("accessToken", "fake-access-token");
    });

    await page.route("**/api/auth/me/", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: 1, username: "e2e-user" }),
      }),
    );

    // Conversations empty
    await page.route("**/api/chat/conversations", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      }),
    );

    // Simulate server error for friends list
    await page.route("**/api/friends/list**", (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "boom" }),
      }),
    );

    await page.goto("/messages");

    const alert = page.locator('[role="alert"]');
    await expect(alert).toBeVisible({ timeout: 3000 });
  });
});
