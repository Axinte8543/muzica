# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: catalog.spec.ts >> E04 genre selection filters and persists in URL
- Location: tests\e2e\catalog.spec.ts:19:1

# Error details

```
Error: expect(page).toHaveURL(expected) failed

Expected pattern: /genre=e2e-genre/
Received string:  "http://127.0.0.1:5174/albums"
Timeout: 5000ms

Call log:
  - Expect "toHaveURL" with timeout 5000ms
    14 × locator resolved to <html lang="en" data-theme="light">…</html>
       - unexpected value "http://127.0.0.1:5174/albums"

```

```yaml
- banner:
  - link "roMusic - prima pagină":
    - /url: /
    - text: roMusic
  - link "Albume":
    - /url: /albums
  - link "Liste":
    - /url: /lists
  - link "Urmăriți":
    - /url: /following
  - searchbox "Caută muzică"
  - button "Caută"
  - link "Login":
    - /url: /login
  - link "Register":
    - /url: /register
  - button "Dark"
- main:
  - heading "roMusic" [level=1]
  - heading "Albume" [level=1]
  - complementary:
    - text: Căutare
    - searchbox "Caută album sau artist..."
    - button "Caută"
    - button "Curăță"
    - text: Filtre Tip
    - combobox "Tip":
      - option "Albume" [selected]
      - option "Single-uri"
      - option "Toate lansările"
    - text: Gen
    - combobox "Gen":
      - option "Toate"
      - option "E2E Genre" [selected]
    - text: An
    - combobox "An":
      - option "Toți" [selected]
      - option "2023"
    - text: Lună
    - combobox "Lună":
      - option "Toate" [selected]
      - option "01"
      - option "03"
      - option "05"
      - option "07"
    - text: Deceniu
    - combobox "Deceniu":
      - option "Toate" [selected]
      - option "2020s"
  - text: Ordonează după
  - combobox "Ordonează după":
    - option "Data lansării" [selected]
    - option "Nota"
    - option "Nr. ratinguri"
    - option "Nota mea"
  - link "E2E Album Midnight E2E Flow Artist Album · 2 piese 2023":
    - /url: /albums/e2e-album-midnight
  - link "E2E Album Aurora E2E Flow Artist Album · 2 piese 2023":
    - /url: /albums/e2e-album-aurora
  - link "E2E Album Skyline E2E Flow Artist Album · 2 piese 2023":
    - /url: /albums/e2e-album-skyline
  - link "E2E Album Sunrise E2E Flow Artist Album · 2 piese 2023":
    - /url: /albums/e2e-album-sunrise
  - button "Prev" [disabled]
  - text: Page 1 — 4 total
  - button "Next" [disabled]
- contentinfo:
  - text: ALBUMS
  - link "Cele mai apreciate":
    - /url: /top-albums
  - link "Albume recomandate":
    - /url: /albums?sort=rating
  - link "Liste":
    - /url: /lists
  - link "Lansări noi":
    - /url: /albums?sort=release_date
  - link "Aleatoriu":
    - /url: /albums/random
  - text: ARTISTS
  - link "Top artiști":
    - /url: /artists/highest-rated
  - link "Aleatoriu":
    - /url: /artists/random
  - text: GENRE
  - link "Prezentare":
    - /url: /genres
  - link "Indie Rock":
    - /url: /albums?genre=indie-rock
  - link "Electronic":
    - /url: /albums?genre=electronic
  - link "Hip Hop":
    - /url: /albums?genre=hip-hop
  - link "Folk":
    - /url: /albums?genre=folk
  - link "Indie Pop":
    - /url: /albums?genre=indie-pop
  - text: MORE
  - link "On This Day":
    - /url: /more/on-this-day
  - link "Newsworthy":
    - /url: /more/newsworthy
  - link "User Updates":
    - /url: /more/user-updates
  - link "Site Updates":
    - /url: /more/site-updates
  - link "Corrections":
    - /url: /more/corrections
  - text: SITE DETAILS
  - link "FAQ":
    - /url: /site/faq
  - link "Changelog":
    - /url: /site/changelog
  - link "Privacy Policy":
    - /url: /site/privacy
  - link "Terms of Use":
    - /url: /site/terms
  - link "Advertising":
    - /url: /site/advertising
  - link "Contact Us":
    - /url: /site/contact
  - link "Subscribe":
    - /url: /site/subscribe
  - link "Instagram":
    - /url: https://www.instagram.com/_axinte_/
  - link "X":
    - /url: https://x.com/Axinte8542
  - link "Facebook":
    - /url: https://www.facebook.com/avrinte.rica/
  - link "Threads":
    - /url: https://www.threads.com/@_axinte_
  - link "Bluesky":
    - /url: https://bsky.app/profile/axinte8542.bsky.social
  - text: © 2026 roMusic
```

# Test source

```ts
  1   | import { test, expect } from "@playwright/test";
  2   | import { ALBUM, ARTIST } from "./helpers";
  3   |
  4   | test("E01 guest home renders real discovery data", async ({ page }) => {
  5   |   await page.goto("/");
  6   |   await expect(page.locator("main")).toContainText(/E2E Album/);
  7   | });
  8   | test("E02 catalog lists all four seeded albums", async ({ page }) => {
  9   |   await page.goto("/albums");
  10  |   for (const name of ["Sunrise", "Skyline", "Aurora", "Midnight"]) await expect(page.getByRole("link", { name: new RegExp(`E2E Album ${name}`) })).toBeVisible();
  11  | });
  12  | test("E03 catalog searches by title", async ({ page }) => {
  13  |   await page.goto("/albums");
  14  |   await page.getByPlaceholder("Caută album sau artist...").fill("Aurora");
  15  |   await page.locator("aside").getByRole("button", { name: "Caută", exact: true }).click();
  16  |   await expect(page.getByRole("link", { name: /E2E Album Aurora/ })).toBeVisible();
  17  |   await expect(page.getByRole("link", { name: /E2E Album Midnight/ })).toHaveCount(0);
  18  | });
  19  | test("E04 genre selection filters and persists in URL", async ({ page }) => {
  20  |   await page.goto("/albums");
  21  |   await page.getByRole("combobox", { name: "Gen", exact: true }).selectOption("e2e-genre");
> 22  |   await expect(page).toHaveURL(/genre=e2e-genre/);
      |                      ^ Error: expect(page).toHaveURL(expected) failed
  23  |   await expect(page.getByRole("link", { name: /E2E Album Aurora/ })).toBeVisible();
  24  | });
  25  | test("E05 release year filter survives reload", async ({ page }) => {
  26  |   await page.goto("/albums");
  27  |   await page.getByRole("combobox", { name: "An", exact: true }).selectOption("2023");
  28  |   await expect(page).toHaveURL(/year=2023/);
  29  |   await page.reload();
  30  |   await expect(page.getByRole("combobox", { name: "An", exact: true })).toHaveValue("2023");
  31  |   await expect(page.getByRole("link", { name: /E2E Album Skyline/ })).toBeVisible();
  32  | });
  33  | test("E06 month filter excludes other release months", async ({ page }) => {
  34  |   await page.goto("/albums");
  35  |   await page.getByRole("combobox", { name: "Lună", exact: true }).selectOption("3");
  36  |   await expect(page.getByRole("link", { name: /E2E Album Skyline/ })).toBeVisible();
  37  |   await expect(page.getByRole("link", { name: /E2E Album Aurora/ })).toHaveCount(0);
  38  | });
  39  | test("E07 singles filter excludes multi-track albums", async ({ page }) => {
  40  |   await page.goto("/albums");
  41  |   await page.getByRole("combobox", { name: "Tip", exact: true }).selectOption("singles");
  42  |   await expect(page).toHaveURL(/release_type=singles/);
  43  |   await expect(page.getByRole("link", { name: /E2E Album/ })).toHaveCount(0);
  44  | });
  45  | test("E08 default catalog ordering is newest first", async ({ page }) => {
  46  |   await page.goto("/albums");
  47  |   await expect(page.getByRole("link", { name: /E2E Album/ }).first()).toContainText("E2E Album Midnight");
  48  | });
  49  | test("E09 missing album displays recoverable error", async ({ page }) => {
  50  |   await page.goto("/albums/no-such-album");
  51  |   await expect(page.locator("main")).toContainText(/Nu am putut|indisponibil|găsit/);
  52  |   await expect(page.getByRole("link", { name: /Înapoi la albume/ })).toBeVisible();
  53  | });
  54  | test("E10 album details expose ordered tracks", async ({ page }) => {
  55  |   await page.goto(ALBUM);
  56  |   await expect(page.getByRole("heading", { name: "E2E Album Aurora", exact: true })).toBeVisible();
  57  |   await expect(page.getByRole("link", { name: "Aurora", exact: true })).toBeVisible();
  58  |   await expect(page.getByRole("link", { name: "Aurora Outro", exact: true })).toBeVisible();
  59  | });
  60  | test("E11 album artist link opens artist details", async ({ page }) => {
  61  |   await page.goto(ALBUM);
  62  |   await page.locator("main").getByRole("link", { name: "E2E Flow Artist", exact: true }).first().click();
  63  |   await expect(page).toHaveURL(new RegExp(ARTIST));
  64  |   await expect(page.getByRole("heading", { name: "E2E Flow Artist", exact: true })).toBeVisible();
  65  | });
  66  | test("E12 track link opens song details", async ({ page }) => {
  67  |   await page.goto(ALBUM);
  68  |   await page.getByRole("link", { name: "Aurora", exact: true }).click();
  69  |   await expect(page).toHaveURL(/\/songs\/e2e-album-aurora-song$/);
  70  |   await expect(page.getByRole("heading", { name: "Aurora", exact: true })).toBeVisible();
  71  | });
  72  | test("E13 global search finds an artist", async ({ page }) => {
  73  |   await page.goto("/");
  74  |   await page.getByRole("searchbox", { name: "Caută muzică" }).fill("E2E Flow Artist");
  75  |   await page.getByRole("button", { name: "Caută", exact: true }).click();
  76  |   await expect(page).toHaveURL(/\/search\?q=/);
  77  |   await expect(page.locator("main").getByRole("link", { name: "E2E Flow Artist", exact: true }).first()).toBeVisible();
  78  | });
  79  | test("E14 global search handles no results", async ({ page }) => {
  80  |   await page.goto("/search?q=zzznomatch123");
  81  |   await expect(page.locator("main")).toContainText(/Niciun|Nu am găsit|Nu există/);
  82  | });
  83  | test("E15 selected theme survives reload", async ({ page }) => {
  84  |   await page.goto("/login");
  85  |   const initial = await page.locator("html").getAttribute("data-theme");
  86  |   await page.getByRole("button", { name: initial === "dark" ? "Light" : "Dark", exact: true }).click();
  87  |   await page.reload();
  88  |   await expect(page.locator("html")).toHaveAttribute("data-theme", initial === "dark" ? "light" : "dark");
  89  | });
  90  | test("E16 unknown route displays Not Found", async ({ page }) => {
  91  |   await page.goto("/unknown-route");
  92  |   await expect(page.getByRole("heading", { name: "Not Found", exact: true })).toBeVisible();
  93  | });
  94  | test("E17 mobile menu navigates to catalog", async ({ page }) => {
  95  |   await page.setViewportSize({width:390,height:844});
  96  |   await page.goto("/login");
  97  |   await page.getByRole("button", { name: "Meniu", exact: true }).click();
  98  |   await page.getByRole("navigation", { name: "Meniu mobil" }).getByRole("link", { name: "Albume", exact: true }).click();
  99  |   await expect(page).toHaveURL(/\/albums$/);
  100 |   await expect(page.getByRole("heading", { name: "Albume", exact: true })).toBeVisible();
  101 | });
  102 | test("E18 public profile exposes username", async ({ page }) => {
  103 |   await page.goto("/users/e2e_bob");
  104 |   await expect(page.locator("main")).toContainText("e2e_bob");
  105 | });
  106 | test("E19 genre directory includes seeded genre", async ({ page }) => {
  107 |   await page.goto("/genres");
  108 |   await expect(page.locator("main").getByText("E2E Genre", {exact:true})).toBeVisible();
  109 | });
  110 | test("E20 top albums displays rated seeded data", async ({ page }) => {
  111 |   await page.goto("/top-albums");
  112 |   await expect(page.locator("main")).toContainText(/E2E Album/);
  113 | });
  114 |
```
