import { ui } from "../ui/ui.js";

export default function AdvertisingPage() {
  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Advertising</h1>

      <div style={{ maxWidth: "920px", opacity: 0.9 }}>
        <p>
          Aceasta este o pagină informativă despre opțiunile de promovare în
          aplicația Licenta Muzica. Pentru cereri concrete, folosește pagina
          Contact Us.
        </p>
      </div>

      <div style={{ maxWidth: "920px", marginTop: 14 }}>
        <div style={ui.card}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>
            Ce tipuri de promovare
          </h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Putem discuta opțiuni precum bannere, mențiuni în pagini dedicate,
            integrarea de campanii sau sponsorizări pentru conținut (în limita
            spațiului și a regulilor platformei).
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>Cerințe minime</h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Materialele trebuie să fie relevante, legale și să respecte un ton
            adecvat comunității. Ne rezervăm dreptul de a refuza campanii care
            nu se aliniază cu aceste reguli.
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>Contact</h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Trimite detalii despre campanie (perioadă, buget, format dorit) prin
            pagina Contact Us.
          </p>
        </div>
      </div>
    </div>
  );
}
