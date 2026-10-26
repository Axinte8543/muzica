import { test, expect } from "@playwright/test";
import { login, openChat, ALBUM, ARTIST } from "./helpers";

test("E36 sent message persists after reload", async ({ page }) => {
  await openChat(page);
  const text=`Mesaj persistent ${Date.now()}`;
  await page.locator(".chat-input").fill(text);
  await page.getByRole("button",{name:"Trimite",exact:true}).click();
  await expect(page.locator(".message-bubble",{hasText:text})).toBeVisible();
  await page.reload();
  await page.getByRole("button",{name:/e2e_bob/}).click();
  await expect(page.locator(".message-bubble",{hasText:text})).toBeVisible();
});
test("E37 whitespace-only messages cannot be sent", async ({ page }) => {
  await openChat(page);
  await page.locator(".chat-input").fill("   ");
  await expect(page.getByRole("button",{name:"Trimite",exact:true})).toBeDisabled();
});
test("E38 friend search excludes nonmatching conversations", async ({ page }) => {
  await openChat(page);
  await page.getByRole("searchbox",{name:"Caută prieteni"}).fill("no-such-friend");
  await expect(page.getByText("Niciun prieten găsit.")).toBeVisible();
  await expect(page.locator(".conversation-item")).toHaveCount(0);
});
test("E39 keyboard opens conversation", async ({ page }) => {
  await login(page); await page.goto("/messages");
  await page.getByRole("button",{name:/e2e_bob/}).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".chat-header")).toHaveText("e2e_bob");
});
test("E40 album rating persists after reload", async ({ page }) => {
  await login(page); await page.goto(ALBUM);
  await page.getByRole("button",{name:"Dă rating 3",exact:true}).click();
  await expect(page.getByText("Ratingul tău: 3/5",{exact:true})).toBeVisible();
  await page.reload();
  await expect(page.getByText("Ratingul tău: 3/5",{exact:true})).toBeVisible();
});
test("E41 artist rating persists after reload", async ({ page }) => {
  await login(page); await page.goto(ARTIST);
  await page.getByRole("button",{name:"Dă rating 4",exact:true}).click();
  await page.reload();
  await expect(page.getByText("Ratingul tău: 4/5",{exact:true})).toBeVisible();
});
test("E42 song rating persists after reload", async ({ page }) => {
  await login(page); await page.goto("/songs/e2e-album-aurora-song");
  await page.getByRole("button",{name:"Dă rating 2",exact:true}).click();
  await expect(page.getByText("Ratingul tău: 2/5",{exact:true})).toBeVisible();
  await page.reload();
  await expect(page.getByText("Ratingul tău: 2/5",{exact:true})).toBeVisible();
});
test("E43 album like can be added and removed", async ({ page }) => {
  await login(page); await page.goto(ALBUM);
  await page.getByRole("button",{name:"Apreciază",exact:true}).click();
  await page.reload();
  await page.getByRole("button",{name:"Retrage aprecierea",exact:true}).click();
  await expect(page.getByRole("button",{name:"Apreciază",exact:true})).toBeEnabled();
});
test("E44 want-to-listen entry persists and can be removed", async ({ page }) => {
  await login(page); await page.goto(ALBUM);
  await page.getByRole("button",{name:"Adaugă la ascultat",exact:true}).click();
  await page.reload();
  await page.getByRole("button",{name:"Scoate din lista de ascultat",exact:true}).click();
  await expect(page.getByRole("button",{name:"Adaugă la ascultat",exact:true})).toBeEnabled();
});
test("E45 marking album listened disables duplicate daily listen", async ({ page }) => {
  await login(page); await page.goto(ALBUM);
  await page.getByRole("button",{name:"Am ascultat",exact:true}).click();
  await page.reload();
  await expect(page.getByRole("button",{name:"Ai ascultat azi",exact:true})).toBeDisabled();
});
test("E46 following artist persists and can be removed", async ({ page }) => {
  await login(page); await page.goto(ARTIST);
  await page.getByRole("button",{name:"Follow",exact:true}).click();
  await page.reload();
  await page.getByRole("button",{name:"Unfollow",exact:true}).click();
  await expect(page.getByRole("button",{name:"Follow",exact:true})).toBeEnabled();
});
test("E47 recommendations exclude own rated albums", async ({ page }) => {
  await login(page); await page.goto("/recommendations");
  await expect(page.getByRole("heading",{name:/Recomandări muzicale/})).toBeVisible();
  await expect(page.locator("main")).toContainText("E2E Album Midnight");
  await expect(page.locator("main").getByRole("link",{name:"E2E Album Sunrise",exact:true})).toHaveCount(0);
});
