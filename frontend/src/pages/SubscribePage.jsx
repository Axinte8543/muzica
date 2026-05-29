import { Link } from "react-router-dom";

import { ui } from "../ui/ui.js";

export default function SubscribePage() {
  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Subscribe</h1>

      <div style={{ maxWidth: "920px", opacity: 0.9 }}>
        <p>
          În acest moment, aplicația nu are un newsletter automat. Totuși, poți
          rămâne la curent cu modificările din paginile de mai jos.
        </p>
      </div>

      <div style={{ maxWidth: "920px", marginTop: 14 }}>
        <div style={ui.card}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>
            Unde vezi update-urile
          </h3>
          <ul style={{ margin: 0, paddingLeft: 18, opacity: 0.9 }}>
            <li>
              <Link to="/site/changelog">Changelog</Link> — listă cu schimbări
              și versiuni
            </li>
            <li>
              <Link to="/more/site-updates">More → Site Updates</Link> —
              update-uri despre site
            </li>
            <li>
              <Link to="/more/user-updates">More → User Updates</Link> —
              update-uri legate de cont și utilizatori
            </li>
          </ul>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>Follow</h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Dacă există canale sociale active, le găsești în footer
            (Instagram/X/ Facebook).
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>Contact</h3>
          <p style={{ marginTop: 0, opacity: 0.9 }}>
            Pentru propuneri (inclusiv newsletter), scrie-ne din pagina Contact
            Us.
          </p>
          <p style={{ margin: 0 }}>
            <Link to="/site/contact">Site Details → Contact Us</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
