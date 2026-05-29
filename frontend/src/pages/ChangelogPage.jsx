import { ui } from "../ui/ui.js";

export default function ChangelogPage() {
  const entries = [
    {
      version: "0.3.0",
      date: "2026-04-18",
      changes: [
        "Adăugat Chat global (autentificare necesară)",
        "Adăugată pagina Corrections (raportare corecții)",
        "Pagini More: User Updates / Site Updates / Newsworthy",
      ],
    },
    {
      version: "0.2.0",
      date: "2026-04-10",
      changes: [
        "Îmbunătățiri la profil: listens, ratings, liked albums, following",
        "Top albums și statistici muzicale",
      ],
    },
    {
      version: "0.1.0",
      date: "2026-03-20",
      changes: [
        "Bază aplicație: albume/artiști/piese, autentificare, liste, review-uri",
      ],
    },
  ];

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Changelog</h1>
      <div style={{ maxWidth: "920px", opacity: 0.9 }}>
        <p>Istoric scurt al modificărilor și funcționalităților adăugate.</p>
      </div>

      <div style={{ maxWidth: "920px", marginTop: 14 }}>
        {entries.map((e) => (
          <div key={e.version} style={{ ...ui.card, marginTop: 12 }}>
            <div style={{ display: "flex", gap: 10, alignItems: "baseline" }}>
              <h3 style={{ marginTop: 0, marginBottom: 8 }}>{e.version}</h3>
              <span style={{ opacity: 0.75 }}>{e.date}</span>
            </div>
            <ul style={{ margin: 0, paddingLeft: 18, opacity: 0.9 }}>
              {e.changes.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
