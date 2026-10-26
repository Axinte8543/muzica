import { test, expect } from "@playwright/test";
import { ALBUM, ARTIST } from "./helpers";

test("E01 guest home renders real discovery data", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("main")).toContainText(/E2E Album/);
});
test("E02 catalog lists all four seeded albums", async ({ page }) => {
  await page.goto("/albums");
  for (const name of ["Sunrise", "Skyline", "Aurora", "Midnight"]) await expect(page.getByRole("link", { name: new RegExp(`E2E Album ${name}`) })).toBeVisible();
});
test("E03 catalog searches by title", async ({ page }) => {
  await page.goto("/albums");
  await page.getByPlaceholder("Caută album sau artist...").fill("Aurora");
  await page.locator("aside").getByRole("button", { name: "Caută", exact: true }).click();
  await expect(page.getByRole("link", { name: /E2E Album Aurora/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /E2E Album Midnight/ })).toHaveCount(0);
});
test("E04 genre selection filters and persists in URL", async ({ page }) => {
  await page.goto("/albums");
  await page.getByRole("combobox", { name: "Gen", exact: true }).selectOption("e2e-genre");
  await expect(page).toHaveURL(/genre=e2e-genre/);
  await expect(page.getByRole("link", { name: /E2E Album Aurora/ })).toBeVisible();
});
test("E05 release year filter survives reload", async ({ page }) => {
  await page.goto("/albums");
  await page.getByRole("combobox", { name: "An", exact: true }).selectOption("2023");
  await expect(page).toHaveURL(/year=2023/);
  await page.reload();
  await expect(page.getByRole("combobox", { name: "An", exact: true })).toHaveValue("2023");
  await expect(page.getByRole("link", { name: /E2E Album Skyline/ })).toBeVisible();
});
test("E06 month filter excludes other release months", async ({ page }) => {
  await page.goto("/albums");
  await page.getByRole("combobox", { name: "Lună", exact: true }).selectOption("3");
  await expect(page.getByRole("link", { name: /E2E Album Skyline/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /E2E Album Aurora/ })).toHaveCount(0);
});
test("E07 singles filter excludes multi-track albums", async ({ page }) => {
  await page.goto("/albums");
  await page.getByRole("combobox", { name: "Tip", exact: true }).selectOption("singles");
  await expect(page).toHaveURL(/release_type=singles/);
  await expect(page.getByRole("link", { name: /E2E Album/ })).toHaveCount(0);
});
test("E08 default catalog ordering is newest first", async ({ page }) => {
  await page.goto("/albums");
  await expect(page.getByRole("link", { name: /E2E Album/ }).first()).toContainText("E2E Album Midnight");
});
test("E09 missing album displays recoverable error", async ({ page }) => {
  await page.goto("/albums/no-such-album");
  await expect(page.locator("main")).toContainText("Albumul nu a putut fi încărcat.");
  await expect(page.getByRole("link", { name: /Înapoi la albume/ })).toBeVisible();
});
test("E10 album details expose ordered tracks", async ({ page }) => {
  await page.goto(ALBUM);
  await expect(page.getByRole("heading", { name: "E2E Album Aurora", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Aurora", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Aurora Outro", exact: true })).toBeVisible();
});
test("E11 album artist link opens artist details", async ({ page }) => {
  await page.goto(ALBUM);
  await page.locator("main").getByRole("link", { name: "E2E Flow Artist", exact: true }).first().click();
  await expect(page).toHaveURL(new RegExp(ARTIST));
  await expect(page.getByRole("heading", { name: "E2E Flow Artist", exact: true })).toBeVisible();
});
test("E12 track link opens song details", async ({ page }) => {
  await page.goto(ALBUM);
  await page.getByRole("link", { name: "Aurora", exact: true }).click();
  await expect(page).toHaveURL(/\/songs\/e2e-album-aurora-song$/);
  await expect(page.getByRole("heading", { name: "Aurora", exact: true })).toBeVisible();
});
test("E13 global search finds an artist", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("searchbox", { name: "Caută muzică" }).fill("E2E Flow Artist");
  await page.getByRole("button", { name: "Caută", exact: true }).click();
  await expect(page).toHaveURL(/\/search\?q=/);
  await expect(page.locator("main").getByRole("link", { name: "E2E Flow Artist", exact: true }).first()).toBeVisible();
});
test("E14 global search handles no results", async ({ page }) => {
  await page.goto("/search?q=zzznomatch123");
  await expect(page.locator("main")).toContainText(/Niciun|Nu am găsit|Nu există/);
});
test("E15 selected theme survives reload", async ({ page }) => {
  await page.goto("/login");
  const initial = await page.locator("html").getAttribute("data-theme");
  await page.getByRole("button", { name: initial === "dark" ? "Light" : "Dark", exact: true }).click();
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", initial === "dark" ? "light" : "dark");
});
test("E16 unknown route displays Not Found", async ({ page }) => {
  await page.goto("/unknown-route");
  await expect(page.getByRole("heading", { name: "Not Found", exact: true })).toBeVisible();
});
test("E17 mobile menu navigates to catalog", async ({ page }) => {
  await page.setViewportSize({width:390,height:844});
  await page.goto("/login");
  await page.getByRole("button", { name: "Meniu", exact: true }).click();
  await page.getByRole("navigation", { name: "Meniu mobil" }).getByRole("link", { name: "Albume", exact: true }).click();
  await expect(page).toHaveURL(/\/albums$/);
  await expect(page.getByRole("heading", { name: "Albume", exact: true })).toBeVisible();
});
test("E18 public profile exposes username", async ({ page }) => {
  await page.goto("/users/e2e_bob");
  await expect(page.locator("main")).toContainText("e2e_bob");
});
test("E19 genre directory includes seeded genre", async ({ page }) => {
  await page.goto("/genres");
  await expect(page.locator("main").getByText("E2E Genre", {exact:true})).toBeVisible();
});
test("E20 top albums displays rated seeded data", async ({ page }) => {
  await page.goto("/top-albums");
  await expect(page.locator("main")).toContainText(/E2E Album/);
});
