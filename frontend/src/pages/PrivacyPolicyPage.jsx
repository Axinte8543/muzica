import { ui } from "../ui/ui.js";

export default function PrivacyPolicyPage() {
  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Privacy Policy</h1>

      <div style={{ maxWidth: "920px", opacity: 0.9 }}>
        <p>
          Aceasta este o politică de confidențialitate (variantă informativă)
          pentru aplicația Licenta Muzica. Dacă ai nevoie de un document complet
          conform cerințelor legale specifice (ex: GDPR), recomand consultarea
          unui specialist.
        </p>
      </div>

      <div style={{ maxWidth: "920px", marginTop: 14 }}>
        <div style={ui.card}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>1. Ce date colectăm</h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Putem colecta date furnizate de tine (de exemplu: username, email,
            conținut trimis în aplicație precum review-uri, liste, mesaje în
            chat, rapoarte de corecții) și date tehnice necesare funcționării
            (de exemplu: jurnale de eroare, adresa IP, informații despre
            browser).
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>
            2. Cum folosim datele
          </h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Folosim datele pentru a crea și gestiona contul tău, a furniza
            funcționalitățile aplicației (rating-uri, review-uri, follow, chat),
            a preveni abuzuri și a îmbunătăți produsul.
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>
            3. Cookie-uri și stocare locală
          </h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Aplicația poate folosi cookie-uri și/sau stocare locală pentru
            autentificare (token-uri) și preferințe. Poți controla cookie-urile
            din setările browserului.
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>4. Cu cine partajăm</h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Nu vindem date personale. Putem partaja date strict cu furnizori
            tehnici (hosting, baze de date, monitorizare) doar în măsura
            necesară funcționării aplicației.
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>
            5. Păstrarea datelor
          </h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Păstrăm datele cât timp este necesar pentru a furniza serviciul și
            pentru scopurile descrise mai sus. La cerere, putem șterge contul și
            datele asociate, cu excepția situațiilor în care legea impune
            altfel.
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>6. Drepturile tale</h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            În funcție de jurisdicție, poți avea dreptul de acces, rectificare,
            ștergere, restricționare sau portabilitate. Pentru solicitări,
            folosește pagina Contact Us.
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>7. Securitate</h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Folosim măsuri rezonabile pentru protecția datelor, însă nicio
            metodă de transmitere/stocare nu este 100% sigură.
          </p>
        </div>

        <div style={{ ...ui.card, marginTop: 12 }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>8. Modificări</h3>
          <p style={{ margin: 0, opacity: 0.9 }}>
            Putem actualiza această politică periodic. Data ultimei actualizări:
            2026-04-18.
          </p>
        </div>
      </div>
    </div>
  );
}
