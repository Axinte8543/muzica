import { ui } from "../ui/ui.js";

export default function TermsOfUsePage() {
  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Terms of Use</h1>

      <div style={{ maxWidth: "920px", opacity: 0.9 }}>
        <p>
          Acești termeni (variantă informativă) descriu regulile de utilizare
          pentru aplicația Licenta Muzica. Pentru un document complet adaptat
          unui context legal specific, recomand consultarea unui specialist.
        </p>
      </div>

      <div style={{ maxWidth: "920px", marginTop: 14 }}>
        <div style={ui.card}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>
            1. Acceptarea termenilor
          </h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Prin folosirea aplicației, ești de acord cu acești termeni și cu
            politica de confidențialitate.
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>
            2. Conturi și securitate
          </h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Ești responsabil pentru activitatea contului tău și pentru păstrarea
            confidențialității credențialelor. Nu partaja token-uri sau parole.
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>
            3. Conținut generat de utilizatori
          </h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Poți publica conținut precum review-uri, comentarii, liste și mesaje
            în chat. Nu publica conținut ilegal, abuziv sau care încalcă
            drepturile altora.
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>
            4. Comportament și abuz
          </h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Este interzisă încercarea de a compromite securitatea aplicației, de
            a extrage date neautorizat, de a face spam sau de a perturba
            serviciul.
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>5. Disponibilitate</h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Serviciul poate fi modificat, întrerupt sau actualizat fără
            notificare. Nu garantăm disponibilitate 24/7.
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>
            6. Limitarea răspunderii
          </h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Aplicația este oferită „ca atare”. În măsura permisă de lege, nu ne
            asumăm răspunderea pentru pierderi indirecte sau rezultate din
            utilizarea serviciului.
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>7. Modificări</h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Putem actualiza acești termeni periodic. Continuarea utilizării după
            modificări înseamnă acceptarea versiunii noi. Data ultimei
            actualizări: 2026-04-18.
          </p>
        </div>
      </div>
    </div>
  );
}
