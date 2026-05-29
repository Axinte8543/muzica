import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../api/apiClient.js";
import { ui } from "../ui/ui.js";

const pageStyle = { padding: "24px" };

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

export default function ArtistReleasesPage() {
  const { slug, section } = useParams();
  const sectionKey = (section || "singles").toLowerCase();

  const discographyQuery = useQuery({
    queryKey: ["artistDiscography", slug],
    enabled: Boolean(slug),
    queryFn: async () => {
      const res = await apiClient.get(`/api/artists/${slug}/discography/`);
      return res.data;
    },
  });

  const items = useMemo(() => {
    const discography = discographyQuery.data || {};
    if (!discography) return [];
    if (sectionKey === "appearson") {
      return asArray(discography.appears_on);
    }
    return asArray(discography[sectionKey]);
  }, [discographyQuery.data, sectionKey]);

  const title = useMemo(() => {
    const map = {
      albums: "Albume",
      singles: "Single",
      eps: "EPs",
      compilations: "Compilatii",
      other: "Altele",
      appearson: "Aparitii",
    };
    return map[sectionKey] || "Releases";
  }, [sectionKey]);

  return (
    <div style={pageStyle}>
      <p style={{ marginTop: 0, display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Link to={`/artists/${slug}`}>← Înapoi la artist</Link>
        <span style={{ opacity: 0.6 }}>|</span>
        <Link to="/search">Caută</Link>
      </p>

      <h1 style={{ marginTop: 16, marginBottom: 24 }}>
        {title} <span style={{ opacity: 0.65 }}>({items.length})</span>
      </h1>

      {discographyQuery.isLoading ? (
        <div
          style={{
            ...ui.card,
            marginTop: 12,
            textAlign: "center",
            opacity: 0.85,
          }}
        >
          Se încarcă...
        </div>
      ) : discographyQuery.isError ? (
        <div style={{ ...ui.card, ...ui.errorText, marginTop: 12 }}>
          Nu am putut încărca discografia.
        </div>
      ) : items.length ? (
        <div style={{ marginTop: 12, display: "grid", gap: "12px" }}>
          {items.map((it, idx) => (
            <Link
              key={it.id || it.slug || `${title}-${idx}`}
              to={it.slug ? `/albums/${it.slug}` : "#"}
              style={{
                ...ui.card,
                padding: "14px 16px",
                textDecoration: "none",
                color: "inherit",
                transition: "all 0.2s ease",
                cursor: it.slug ? "pointer" : "default",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 12,
                  alignItems: "start",
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontWeight: 700,
                      fontSize: "1.05rem",
                      marginBottom: 6,
                    }}
                  >
                    {it.title || it.name || "Untitled"}
                  </div>
                  {it.artist_name ? (
                    <div
                      style={{
                        opacity: 0.7,
                        marginBottom: 4,
                        fontSize: "0.95rem",
                      }}
                    >
                      {it.artist_name}
                    </div>
                  ) : null}
                  {it.release_date ? (
                    <div style={{ opacity: 0.6, fontSize: "0.9rem" }}>
                      {it.release_date}
                    </div>
                  ) : null}
                </div>
                {it.average_rating !== null &&
                it.average_rating !== undefined ? (
                  <div
                    style={{
                      opacity: 0.75,
                      fontSize: "0.95rem",
                      textAlign: "right",
                    }}
                  >
                    ⭐ {Number(it.average_rating).toFixed(1)}
                  </div>
                ) : null}
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div
          style={{
            ...ui.card,
            marginTop: 12,
            textAlign: "center",
            opacity: 0.85,
          }}
        >
          Nu există elemente.
        </div>
      )}
    </div>
  );
}
