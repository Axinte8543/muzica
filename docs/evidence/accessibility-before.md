# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: axe.spec.ts >> Accessibility (axe) >> home page has no detectable accessibility violations
- Location: tests\e2e\axe.spec.ts:5:3

# Error details

```
AssertionError: 1 accessibility violation was detected

1 !== 0

```

# Page snapshot

```yaml
- generic [ref=e4]:
  - banner [ref=e5]:
    - generic [ref=e7]:
      - generic [ref=e8]:
        - link "roMusic - prima pagină" [ref=e9] [cursor=pointer]:
          - /url: /
          - generic [aria-hidden] [ref=e10]: rM
          - generic [ref=e11]: roMusic
        - generic [ref=e13]:
          - link "Albume" [ref=e14] [cursor=pointer]:
            - /url: /albums
          - link "Dashboard" [ref=e15] [cursor=pointer]:
            - /url: /dashboard
          - link "Recomandări" [ref=e16] [cursor=pointer]:
            - /url: /recommendations
          - link "Notificări" [ref=e17] [cursor=pointer]:
            - /url: /notifications
          - link "Mesaje" [ref=e18] [cursor=pointer]:
            - /url: /messages
          - link "Liste" [ref=e19] [cursor=pointer]:
            - /url: /lists
          - link "Urmăriți" [ref=e20] [cursor=pointer]:
            - /url: /following
          - link "Activitate" [ref=e21] [cursor=pointer]:
            - /url: /activity
          - link "Propune" [ref=e22] [cursor=pointer]:
            - /url: /suggest
      - generic [ref=e25]:
        - searchbox "Caută muzică" [ref=e26]
        - button "Caută" [ref=e27] [cursor=pointer]
      - generic [ref=e28]:
        - generic [ref=e29]:
          - generic [ref=e30]: Salut, e2e-user
          - link "Profil" [ref=e32] [cursor=pointer]:
            - /url: /profile
        - button "Logout" [ref=e33] [cursor=pointer]
        - button "Dark" [ref=e34] [cursor=pointer]
  - main [ref=e35]:
    - heading "roMusic" [level=1] [ref=e36]
    - alert [ref=e37]:
      - generic [ref=e38]:
        - generic [ref=e39]: A apărut o eroare.
        - generic [ref=e40]: Te rugăm să reîncerci.
        - button "Reîncearcă" [ref=e41] [cursor=pointer]
  - contentinfo [ref=e42]:
    - generic [ref=e43]:
      - generic [ref=e44]:
        - generic [ref=e45]:
          - generic [ref=e46]: ALBUMS
          - generic [ref=e47]:
            - link "Cele mai apreciate" [ref=e48] [cursor=pointer]:
              - /url: /top-albums
            - link "Albume recomandate" [ref=e49] [cursor=pointer]:
              - /url: /albums?sort=rating
            - link "Liste" [ref=e50] [cursor=pointer]:
              - /url: /lists
            - link "Lansări noi" [ref=e51] [cursor=pointer]:
              - /url: /albums?sort=release_date
            - link "Aleatoriu" [ref=e52] [cursor=pointer]:
              - /url: /albums/random
        - generic [ref=e53]:
          - generic [ref=e54]: ARTISTS
          - generic [ref=e55]:
            - link "Top artiști" [ref=e56] [cursor=pointer]:
              - /url: /artists/highest-rated
            - link "Aleatoriu" [ref=e57] [cursor=pointer]:
              - /url: /artists/random
        - generic [ref=e58]:
          - generic [ref=e59]: GENRE
          - generic [ref=e60]:
            - link "Prezentare" [ref=e61] [cursor=pointer]:
              - /url: /genres
            - link "Indie Rock" [ref=e62] [cursor=pointer]:
              - /url: /albums?genre=indie-rock
            - link "Electronic" [ref=e63] [cursor=pointer]:
              - /url: /albums?genre=electronic
            - link "Hip Hop" [ref=e64] [cursor=pointer]:
              - /url: /albums?genre=hip-hop
            - link "Folk" [ref=e65] [cursor=pointer]:
              - /url: /albums?genre=folk
            - link "Indie Pop" [ref=e66] [cursor=pointer]:
              - /url: /albums?genre=indie-pop
        - generic [ref=e67]:
          - generic [ref=e68]: MORE
          - generic [ref=e69]:
            - link "On This Day" [ref=e70] [cursor=pointer]:
              - /url: /more/on-this-day
            - link "Newsworthy" [ref=e71] [cursor=pointer]:
              - /url: /more/newsworthy
            - link "User Updates" [ref=e72] [cursor=pointer]:
              - /url: /more/user-updates
            - link "Site Updates" [ref=e73] [cursor=pointer]:
              - /url: /more/site-updates
            - link "Corrections" [ref=e74] [cursor=pointer]:
              - /url: /more/corrections
        - generic [ref=e75]:
          - generic [ref=e76]: SITE DETAILS
          - generic [ref=e77]:
            - link "FAQ" [ref=e78] [cursor=pointer]:
              - /url: /site/faq
            - link "Changelog" [ref=e79] [cursor=pointer]:
              - /url: /site/changelog
            - link "Privacy Policy" [ref=e80] [cursor=pointer]:
              - /url: /site/privacy
            - link "Terms of Use" [ref=e81] [cursor=pointer]:
              - /url: /site/terms
            - link "Advertising" [ref=e82] [cursor=pointer]:
              - /url: /site/advertising
            - link "Contact Us" [ref=e83] [cursor=pointer]:
              - /url: /site/contact
            - link "Subscribe" [ref=e84] [cursor=pointer]:
              - /url: /site/subscribe
        - generic [ref=e86]:
          - link "Instagram" [ref=e87] [cursor=pointer]:
            - /url: https://www.instagram.com/_axinte_/
          - link "X" [ref=e90] [cursor=pointer]:
            - /url: https://x.com/Axinte8542
          - link "Facebook" [ref=e93] [cursor=pointer]:
            - /url: https://www.facebook.com/avrinte.rica/
          - link "Threads" [ref=e96] [cursor=pointer]:
            - /url: https://www.threads.com/@_axinte_
          - link "Bluesky" [ref=e99] [cursor=pointer]:
            - /url: https://bsky.app/profile/axinte8542.bsky.social
      - generic [ref=e102]: © 2026 roMusic
```
