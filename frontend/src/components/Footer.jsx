import { Link } from "react-router-dom";

function FooterLink({ to, href, children }) {
  if (to) {
    return (
      <Link className="siteFooter__link" to={to}>
        {children}
      </Link>
    );
  }

  if (href) {
    return (
      <a
        className="siteFooter__link"
        href={href}
        target="_blank"
        rel="noreferrer"
      >
        {children}
      </a>
    );
  }

  return <span className="siteFooter__link is-disabled">{children}</span>;
}

function SocialIcon({ href, label, children }) {
  return (
    <a
      className="siteFooter__social"
      href={href}
      target="_blank"
      rel="noreferrer"
      aria-label={label}
      title={label}
    >
      {children}
    </a>
  );
}

export default function Footer() {
  const year = new Date().getFullYear();

  const columns = [
    {
      title: "ALBUMS",
      items: [
        { label: "Cele mai apreciate", to: "/top-albums" },
        { label: "Albume recomandate", to: "/albums?sort=rating" },
        { label: "Liste", to: "/lists" },
        { label: "Lansări noi", to: "/albums?sort=release_date" },
        { label: "Aleatoriu", to: "/albums/random" },
      ],
    },
    {
      title: "ARTISTS",
      items: [
        { label: "Top artiști", to: "/artists/highest-rated" },
        { label: "Aleatoriu", to: "/artists/random" },
      ],
    },
    {
      title: "GENRE",
      items: [
        { label: "Prezentare", to: "/genres" },
        { label: "Indie Rock", to: "/albums?genre=indie-rock" },
        { label: "Electronic", to: "/albums?genre=electronic" },
        { label: "Hip Hop", to: "/albums?genre=hip-hop" },
        { label: "Folk", to: "/albums?genre=folk" },
        { label: "Indie Pop", to: "/albums?genre=indie-pop" },
      ],
    },
    {
      title: "MORE",
      items: [
        { label: "On This Day", to: "/more/on-this-day" },
        { label: "Newsworthy", to: "/more/newsworthy" },
        { label: "User Updates", to: "/more/user-updates" },
        { label: "Site Updates", to: "/more/site-updates" },
        { label: "Corrections", to: "/more/corrections" },
      ],
    },
    {
      title: "SITE DETAILS",
      items: [
        { label: "FAQ", to: "/site/faq" },
        { label: "Changelog", to: "/site/changelog" },
        { label: "Privacy Policy", to: "/site/privacy" },
        { label: "Terms of Use", to: "/site/terms" },
        { label: "Advertising", to: "/site/advertising" },
        { label: "Contact Us", to: "/site/contact" },
        { label: "Subscribe", to: "/site/subscribe" },
      ],
    },
  ];

  return (
    <footer className="siteFooter">
      <div className="siteFooter__inner">
        <div className="siteFooter__grid">
          {columns.map((col) => (
            <div key={col.title} className="siteFooter__col">
              <div className="siteFooter__title">{col.title}</div>
              <div className="siteFooter__list">
                {col.items.map((item) => (
                  <FooterLink key={item.label} to={item.to} href={item.href}>
                    {item.label}
                  </FooterLink>
                ))}
              </div>
            </div>
          ))}

          <div className="siteFooter__socialCol">
            <div className="siteFooter__socialRow">
              <SocialIcon
                href="https://www.instagram.com/_axinte_/"
                label="Instagram"
              >
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden>
                  <path
                    fill="currentColor"
                    d="M7 2h10a5 5 0 0 1 5 5v10a5 5 0 0 1-5 5H7a5 5 0 0 1-5-5V7a5 5 0 0 1 5-5Zm10 2H7a3 3 0 0 0-3 3v10a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3V7a3 3 0 0 0-3-3Zm-5 4.5A5.5 5.5 0 1 1 6.5 14 5.5 5.5 0 0 1 12 8.5Zm0 2A3.5 3.5 0 1 0 15.5 14 3.5 3.5 0 0 0 12 10.5ZM18 6.8a1.2 1.2 0 1 1-1.2 1.2A1.2 1.2 0 0 1 18 6.8Z"
                  />
                </svg>
              </SocialIcon>

              <SocialIcon href="https://x.com/Axinte8542" label="X">
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden>
                  <path
                    fill="currentColor"
                    d="M18.9 2H22l-6.8 7.8L23 22h-6.2l-4.8-6.3L6.6 22H3.5l7.3-8.4L1 2h6.4l4.4 5.8L18.9 2Zm-1.1 18h1.7L7.1 3.9H5.3L17.8 20Z"
                  />
                </svg>
              </SocialIcon>

              <SocialIcon
                href="https://www.facebook.com/avrinte.rica/"
                label="Facebook"
              >
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden>
                  <path
                    fill="currentColor"
                    d="M13 22v-8h3l1-4h-4V7c0-1.1.4-2 2-2h2V1h-3c-3.3 0-5 2-5 5v4H8v4h3v8h2Z"
                  />
                </svg>
              </SocialIcon>

              <SocialIcon
                href="https://www.threads.com/@_axinte_"
                label="Threads"
              >
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden>
                  <path
                    fill="currentColor"
                    d="M12 2c5.5 0 10 4.5 10 10s-4.5 10-10 10S2 17.5 2 12 6.5 2 12 2Zm0 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16Zm.2 4.2c1.9 0 3.4.8 4.3 2.1l-1.6 1c-.6-.9-1.5-1.3-2.7-1.3-1.8 0-3 1.1-3 2.9 0 1.9 1.2 3 3.1 3 1.6 0 2.6-.7 2.9-1.9-.8-.5-1.8-.7-3-.7v-1.8c1.7 0 3.1.4 4.2 1.2v.8c0 2.4-1.8 4.1-4.2 4.1-3 0-5-2-5-4.8 0-2.8 2-4.6 5-4.6Z"
                  />
                </svg>
              </SocialIcon>

              <SocialIcon
                href="https://bsky.app/profile/axinte8542.bsky.social"
                label="Bluesky"
              >
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden>
                  <path
                    fill="currentColor"
                    d="M12 2c2.6 0 5.8 2 7.6 3.7.8.7 1.2 1.7 1.2 2.7 0 3.1-1.8 5.3-4.6 6.1 1.5.8 2.4 2.1 2.4 3.8 0 2.3-2 3.7-4 3.7-1.1 0-2.2-.4-3-1.1-.4-.3-.7-.7-1-1.1-.3.4-.6.8-1 1.1-.8.7-1.9 1.1-3 1.1-2 0-4-1.4-4-3.7 0-1.7.9-3 2.4-3.8C3.2 13.7 1.4 11.5 1.4 8.4c0-1 .4-2 1.2-2.7C4.4 4 7.4 2 10 2h2Zm-2 .8c-2.2 0-5.1 1.9-6.6 3.3-.4.4-.7 1-.7 1.6 0 3.1 2.2 5.1 5.6 5.6.3 0 .5.3.5.6 0 .3-.2.6-.5.7-1.9.6-3.2 1.8-3.2 3.6 0 1.5 1.3 2.4 2.6 2.4.8 0 1.6-.3 2.2-.8.6-.5 1-1.2 1.2-2 0-.3.3-.5.6-.5s.6.2.6.5c.2.8.6 1.5 1.2 2 .6.5 1.4.8 2.2.8 1.3 0 2.6-.9 2.6-2.4 0-1.8-1.3-3-3.2-3.6-.3-.1-.5-.4-.5-.7 0-.3.2-.6.5-.6 3.4-.5 5.6-2.5 5.6-5.6 0-.6-.3-1.2-.7-1.6C17.1 4.7 14.2 2.8 12 2.8h-2Z"
                  />
                </svg>
              </SocialIcon>
            </div>
          </div>
        </div>

        <div className="siteFooter__bottom">© {year} roMusic</div>
      </div>
    </footer>
  );
}
