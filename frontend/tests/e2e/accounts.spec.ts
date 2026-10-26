import { test, expect } from "@playwright/test";
import { login, PASSWORD, registerAccount } from "./helpers";

test("E21 valid login creates browser session", async ({ page }) => {
  await login(page);
  expect(await page.evaluate(() => Boolean(localStorage.getItem("accessToken") && localStorage.getItem("refreshToken")))).toBe(true);
});
test("E22 logout removes stored credentials", async ({ page }) => {
  await login(page);
  await page.getByRole("button", {name:"Logout",exact:true}).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => [localStorage.getItem("accessToken"),localStorage.getItem("refreshToken")])).toEqual([null,null]);
});
test("E23 verified session survives reload", async ({ page }) => {
  await login(page); await page.reload();
  await expect(page.getByRole("button", {name:"Logout",exact:true})).toBeVisible();
  await page.goto("/profile/friends");
  await expect(page.locator("main")).toContainText("e2e_bob");
});
test("E24 empty login is blocked by browser validation", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button",{name:"Login",exact:true}).click();
  expect(await page.getByLabel("username",{exact:true}).evaluate((element: HTMLInputElement) => element.validity.valueMissing)).toBe(true);
  await expect(page).toHaveURL(/\/login$/);
});
test("E25 incorrect password displays server error", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("username",{exact:true}).fill("e2e_alice");
  await page.getByLabel("password",{exact:true}).fill("wrong-password");
  await page.getByRole("button",{name:"Login",exact:true}).click();
  await expect(page.locator("main")).toContainText(/No active account|Login eșuat|credentials/);
  await expect(page).toHaveURL(/\/login$/);
});
test("E26 weak registration password disables submission", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("password",{exact:true}).fill("short");
  await expect(page.getByRole("button",{name:"Înregistrează-te",exact:true})).toBeDisabled();
  await expect(page.locator(".requirement.unmet")).not.toHaveCount(0);
});
test("E27 registration requires email confirmation", async ({ page }) => {
  await registerAccount(page,"confirm");
  await expect(page.getByRole("button",{name:"Retrimite verificarea"})).toBeVisible();
  expect(await page.evaluate(()=>localStorage.getItem("accessToken"))).toBeNull();
});
test("E28 unverified account cannot log in", async ({ page }) => {
  const name=await registerAccount(page,"blocked");
  await page.goto("/login");
  await page.getByLabel("username",{exact:true}).fill(name);
  await page.getByLabel("password",{exact:true}).fill(PASSWORD);
  await page.getByRole("button",{name:"Login",exact:true}).click();
  await expect(page.locator("main")).toContainText(/Contul nu este verificat/);
});
test("E29 invalid email verification token displays error", async ({ page }) => {
  await page.goto("/verify-email?token=invalid-token");
  await expect(page.locator("main")).toContainText(/invalid|expirat|eșuat/i);
});
test("E30 registration rejects duplicate username", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("username",{exact:true}).fill("e2e_alice");
  await page.getByLabel("email",{exact:true}).fill("different@example.com");
  await page.getByLabel("password",{exact:true}).fill(PASSWORD);
  await page.getByRole("button",{name:"Înregistrează-te",exact:true}).click();
  await expect(page.locator("main")).toContainText(/already exists|există deja/i);
});

for (const [id, route, text] of [
  ["E31","/messages",/logat|autentific/i],
  ["E32","/recommendations",/logat|autentific/i],
  ["E33","/profile/friends",/logat/i],
  ["E34","/my-lists",/logat/i],
  ["E35","/profile/privacy",/logat|autentific|Login/i],
] as const) {
  test(`${id} guest is informed that ${route} requires login`, async ({ page }) => {
    await page.goto(route);
    await expect(page.locator("main")).toContainText(text);
    expect(await page.evaluate(()=>localStorage.getItem("accessToken"))).toBeNull();
  });
}
