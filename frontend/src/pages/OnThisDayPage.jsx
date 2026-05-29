import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { apiClient } from "../api/apiClient.js";
import { ui } from "../ui/ui.js";

function formatDate(value) {
  if (!value) return "";
  // API returns ISO date string (YYYY-MM-DD)
  try {
    const d = new Date(value);
    if (!Number.isFinite(d.getTime())) return String(value);
    return d.toLocaleDateString("ro-RO", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return String(value);
  }
}

export default function OnThisDayPage() {
  const [albums, setAlbums] = useState([]);
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
        const res = await apiClient.get(`/api/released-on-this-day/`, {
          params: { limit: 50 },
        });
        if (isCancelled) return;
        setAlbums(Array.isArray(res?.data) ? res.data : []);
      } catch (err) {
        if (isCancelled) return;
        console.error(err);
        setError("Nu am putut încărca albumele lansate azi.");
        setAlbums([]);
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
      <h1 style={{ marginTop: 0 }}>On This Day</h1>
      <p style={{ marginTop: 0, opacity: 0.85 }}>
        Albume lansate în această zi (după data din sistem).
      </p>

      {isLoading ? <p>Se încarcă...</p> : null}
      {error ? <p style={ui.errorText}>{error}</p> : null}

      {!isLoading && !error && albums.length === 0 ? (
        <p style={{ opacity: 0.85 }}>
          Nu există albume lansate azi în baza de date.
        </p>
      ) : null}

      {!isLoading && !error && albums.length > 0 ? (
        <ul style={{ listStyle: "none", padding: 0, marginTop: "16px" }}>
          {albums.map((album) => (
            <li
              key={album.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                padding: "10px 0",
                borderBottom: `1px solid ${ui.colors.border}`,
              }}
            >
              {album.cover_url ? (
                <img
                  src={album.cover_url}
                  alt={album.title}
                  style={{
                    width: "52px",
                    height: "52px",
                    borderRadius: "10px",
                    objectFit: "cover",
                    border: `1px solid ${ui.colors.border}`,
                    flex: "0 0 auto",
                  }}
                />
              ) : (
                <div
                  style={{
                    width: "52px",
                    height: "52px",
                    borderRadius: "10px",
                    background: ui.colors.mutedBg,
                    border: `1px solid ${ui.colors.border}`,
                    flex: "0 0 auto",
                  }}
                />
              )}

              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <div style={{ fontWeight: 700 }}>
                  <Link to={`/albums/${album.slug}`}>{album.title}</Link>
                </div>
                <div style={{ opacity: 0.85 }}>
                  {album.artist_name ? <>{album.artist_name}</> : null}
                  {album.release_date ? (
                    <> · {formatDate(album.release_date)}</>
                  ) : null}
                </div>
                {Array.isArray(album.genres) && album.genres.length > 0 ? (
                  <div style={{ opacity: 0.75, fontSize: 13 }}>
                    {(album.genres || [])
                      .map((g) => g?.name)
                      .filter(Boolean)
                      .join(", ")}
                  </div>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
