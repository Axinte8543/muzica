import { ui } from "../ui/ui.js";

export default function FAQPage() {
  const items = [
    {
      q: "Ce este site-ul ăsta?",
      a: "Este o aplicație pentru a descoperi muzică și a ține evidența albumelor/artiștilor preferați: rating-uri, review-uri, liste și activitate.",
    },
    {
      q: "Cum pot să las un rating sau un review?",
      a: "Intră pe pagina unui album și folosește widget-ul de rating. Pentru review, completează formularul de review (dacă ești logat).",
    },
    {
      q: "Cum funcționează listele?",
      a: "Poți crea liste cu albume și le poți ordona. Unele liste pot fi publice (vizibile pentru alți utilizatori), în funcție de setările aplicației.",
    },
    {
      q: "Pot să urmăresc artiști?",
      a: "Da. Pe pagina unui artist ai opțiunea de follow/unfollow. Apoi îi vezi în pagina de artiști urmăriți.",
    },
    {
      q: "Ce este pagina de Chat?",
      a: "Este un chat global (necesită cont). Mesajele sunt vizibile pentru toți utilizatorii autentificați.",
    },
    {
      q: "Cum raportez o corecție?",
      a: "Intră la More → Corrections și trimite un link (opțional) + descrierea corecției. Poți trimite și fără cont, dar dacă ești logat raportul se asociază contului.",
    },
    {
      q: "De ce nu văd anumite pagini sau acțiuni?",
      a: "Unele acțiuni necesită autentificare (de exemplu, chat, anumite interacțiuni). Dacă primești eroare 401/403, verifică dacă ești logat.",
    },
  ];

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>FAQ</h1>
      <div style={{ maxWidth: "920px", opacity: 0.9 }}>
        <p>
          Întrebări frecvente despre funcționalitățile de bază. Dacă nu găsești
          răspunsul, folosește pagina Contact Us.
        </p>
      </div>

      <div style={{ maxWidth: "920px", marginTop: 14 }}>
        {items.map((it) => (
          <div key={it.q} style={{ ...ui.card, marginTop: 12 }}>
            <h3 style={{ marginTop: 0, marginBottom: 8 }}>{it.q}</h3>
            <p style={{ margin: 0, opacity: 0.9 }}>{it.a}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
