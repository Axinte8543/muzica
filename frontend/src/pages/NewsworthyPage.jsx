import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { apiClient } from "../api/apiClient.js";
import { ui } from "../ui/ui.js";

function truncate(text, maxLen) {
  const value = String(text || "").trim();
  if (!value) return "";
  if (value.length <= maxLen) return value;
  return `${value.slice(0, Math.max(0, maxLen - 1))}…`;
}

export default function NewsworthyPage() {
  const [recentAlbums, setRecentAlbums] = useState([]);
  const [popularReviews, setPopularReviews] = useState([]);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isCancelled = false;

    async function load() {
      if (!isCancelled) {
        setIsLoading(true);
        setError(null);
      }

      try {
        const [recentRes, popularRes] = await Promise.all([
          apiClient.get(`/api/recent-albums/`, { params: { limit: 12 } }),
          apiClient.get(`/api/popular-reviews/`, {
            params: { limit: 10, days: 7 },
          }),
        ]);

        if (isCancelled) return;
        setRecentAlbums(Array.isArray(recentRes.data) ? recentRes.data : []);
        setPopularReviews(
          Array.isArray(popularRes.data) ? popularRes.data : [],
        );
      } catch (err) {
        console.error(err);
        if (!isCancelled) setError("Nu am putut încărca noutățile.");
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      isCancelled = true;
    };
  }, []);

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Newsworthy</h1>

      {isLoading && <p style={{ marginTop: "14px" }}>Se încarcă...</p>}

      {error && (
        <p style={{ ...ui.errorText, marginTop: "14px" }} role="alert">
          {error}
        </p>
      )}

      {!isLoading && !error && (
        <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          <div style={ui.card}>
            <div style={{ fontWeight: 800, marginBottom: "10px" }}>
              Albume recente (ultimele 7 zile)
            </div>

            {recentAlbums.length ? (
              <div
                style={{ display: "flex", flexDirection: "column", gap: "8px" }}
              >
                {recentAlbums.map((a) => (
                  <div
                    key={a.id}
                    style={{
                      display: "flex",
                      gap: "10px",
                      alignItems: "center",
                    }}
                  >
                    {a.cover_url ? (
                      <img
                        src={a.cover_url}
                        alt={a.title}
                        style={{ width: 44, height: 44, borderRadius: 6 }}
                        loading="lazy"
                      />
                    ) : (
                      <div
                        style={{
                          width: 44,
                          height: 44,
                          borderRadius: 6,
                          background: ui.colors.mutedBg,
                          border: `1px solid ${ui.colors.border}`,
                        }}
                      />
                    )}

                    <div style={{ display: "flex", flexDirection: "column" }}>
                      <Link to={`/albums/${a.slug}`}>{a.title}</Link>
                      <div style={{ opacity: 0.85 }}>{a.artist_name}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ opacity: 0.9 }}>Nu sunt albume recente.</div>
            )}
          </div>

          <div style={ui.card}>
            <div style={{ fontWeight: 800, marginBottom: "10px" }}>
              Review-uri populare (ultimele 7 zile)
            </div>

            {popularReviews.length ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                }}
                aria-live="polite"
              >
                {popularReviews.map((r) => (
                  <div key={r.id} style={{ paddingBottom: 8 }}>
                    <div
                      style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}
                    >
                      <Link to={`/albums/${r.album_slug}`}>
                        {r.album_title}
                      </Link>
                      <span style={{ opacity: 0.85 }}>— {r.artist_name}</span>
                    </div>

                    <div style={{ opacity: 0.9, marginTop: 2 }}>
                      <Link to={`/users/${r.user_username}`}>
                        {r.user_username}
                      </Link>
                      <span style={{ opacity: 0.85 }}>
                        {" "}
                        · ❤ {r.likes_count}
                      </span>
                    </div>

                    {r.title ? (
                      <div style={{ fontWeight: 700, marginTop: 4 }}>
                        {truncate(r.title, 90)}
                      </div>
                    ) : null}

                    <div style={{ opacity: 0.95, marginTop: 4 }}>
                      {truncate(r.content, 220)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ opacity: 0.9 }}>Nu sunt review-uri populare.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
