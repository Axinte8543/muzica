import { expect, Page } from "@playwright/test";

export const ALBUM = "/albums/e2e-album-aurora";
export const ARTIST = "/artists/e2e-flow-artist";
export const PASSWORD = "E2E_Test_123!";
export async function login(page: Page, username = "e2e_alice") {
  await page.goto("/login");
  await page.getByLabel("username", { exact: true }).fill(username);
  await page.getByLabel("password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Login", exact: true }).click();
  await expect(page.getByRole("button", { name: "Logout", exact: true })).toBeVisible();
}
export async function openChat(page: Page) {
  await login(page);
  await page.goto("/messages");
  await page.getByRole("button", { name: /e2e_bob/ }).click();
  await expect(page.locator(".chat-header")).toHaveText("e2e_bob");
}
export async function registerAccount(page: Page, suffix: string) {
  const username = `browser_${suffix}_${Date.now()}`;
  await page.goto("/register");
  await page.getByLabel("username", { exact: true }).fill(username);
  await page.getByLabel("email", { exact: true }).fill(`${username}@example.com`);
  await page.getByLabel("password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Înregistrează-te", exact: true }).click();
  await expect(page.getByText(/Cont creat/)).toBeVisible();
  return username;
}
