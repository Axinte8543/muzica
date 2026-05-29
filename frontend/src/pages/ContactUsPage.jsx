import { Link } from "react-router-dom";

import { ui } from "../ui/ui.js";

export default function ContactUsPage() {
  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Contact Us</h1>

      <div style={{ maxWidth: "920px", opacity: 0.9 }}>
        <p>
          Pentru feedback, probleme tehnice sau propuneri, te rugăm să folosești
          opțiunile de mai jos.
        </p>
      </div>

      <div style={{ maxWidth: "920px", marginTop: 14 }}>
        <div style={ui.card}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>
            Raportează o problemă
          </h3>
          <p style={{ marginTop: 0, opacity: 0.9 }}>
            Pentru informații greșite pe pagini (albume, artiști, detalii),
            folosește pagina de corecții:
          </p>
          <p style={{ margin: 0 }}>
            <Link to="/more/corrections">More → Corrections</Link>
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>
            Publicitate / colaborări
          </h3>
          <p style={{ marginTop: 0, opacity: 0.9 }}>
            Pentru campanii, sponsorizări sau promovare, vezi pagina
            Advertising:
          </p>
          <p style={{ margin: 0 }}>
            <Link to="/site/advertising">Site Details → Advertising</Link>
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>Ce să incluzi</h3>
          <ul style={{ margin: 0, paddingLeft: 18, opacity: 0.9 }}>
            <li>link-ul paginii unde apare problema (dacă există)</li>
            <li>pașii de reproducere (ce ai apăsat / ce ai făcut)</li>
            <li>mesajul de eroare (dacă apare)</li>
            <li>browser + sistem (opțional)</li>
          </ul>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>Alte canale</h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Dacă proiectul are canale sociale active, le găsești în footer.
          </p>
        </div>
      </div>
    </div>
  );
}
