import { Link } from "react-router-dom";

import { ui } from "../ui/ui.js";

const UPDATES = [
  {
    title: "Feed de activitate (User Updates)",
    body: "Poți vedea ultimele acțiuni ale utilizatorilor (ascultări, note, review-uri, follow, liste).",
  },
  {
    title: "Random Artist",
    body: "Poți descoperi rapid un artist aleator din baza de date.",
  },
  {
    title: "On This Day",
    body: "Vezi albumele lansate în această zi (după data de release).",
  },
];

export default function SiteUpdatesPage() {
  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Site Updates</h1>

      <div style={{ ...ui.card, marginTop: "14px" }}>
        <div style={{ opacity: 0.95, marginBottom: "10px" }}>
          Ultimele noutăți și îmbunătățiri ale aplicației.
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {UPDATES.map((u) => (
            <div key={u.title}>
              <div style={{ fontWeight: 700, marginBottom: "2px" }}>
                {u.title}
              </div>
              <div style={{ opacity: 0.95 }}>{u.body}</div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: "12px", opacity: 0.9 }}>
          Mai multe detalii: <Link to="/site/changelog">Changelog</Link>
        </div>
      </div>
    </div>
  );
}
