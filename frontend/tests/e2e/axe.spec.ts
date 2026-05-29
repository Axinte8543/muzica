import { test } from "@playwright/test";
import { injectAxe, checkA11y } from "axe-playwright";

test.describe("Accessibility (axe)", () => {
  test("home page has no detectable accessibility violations", async ({
    page,
  }) => {
    // Make the app consider us authenticated and stub basic APIs used on load
    await page.addInitScript(() => {
      localStorage.setItem("accessToken", "fake-access-token");

      class MockEventSource {
        constructor() {
          setTimeout(() => {
            if (typeof this.onopen === "function") {
              this.onopen(new Event("open"));
            }
          }, 0);
        }

        close() {}

        addEventListener() {}

        removeEventListener() {}
      }

      window.EventSource = MockEventSource;
    });

    await page.route("**/api/auth/me/", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: 1, username: "e2e-user" }),
      }),
    );

    await page.route("**/api/chat/conversations", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      }),
    );

    await page.route("**/api/home**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      }),
    );

    await page.route("**/api/onboarding/setup/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ is_completed: true }),
      }),
    );

    // Visit home / root
    await page.goto("/");

    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });

    // Inject axe and run checks
    await injectAxe(page);
    await checkA11y(page, undefined, { detailedReport: true });
  });

  test("messages page has no detectable accessibility violations", async ({
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

    // Provide a minimal conversations list so messages UI renders
    await page.route("**/api/chat/conversations", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([{ user_id: 2, username: "Friend" }]),
      }),
    );

    await page.route("**/api/friends/list**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          friends: { results: [{ id: 2, username: "Friend" }] },
        }),
      }),
    );

    // Intercept messages request and return an empty list
    await page.route("**/api/chat/messages**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      }),
    );

    await page.goto("/messages");

    await page.locator("h1").first().waitFor({ state: "visible" });

    await injectAxe(page);
    await checkA11y(page);
  });
});
