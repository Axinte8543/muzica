import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../api/apiClient.js";
import { ui } from "../ui/ui.js";

function formatRating(value) {
  if (value === null || value === undefined) return "—";
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  return num.toFixed(1);
}

export default function HighestRatedArtistsPage() {
  const [page, setPage] = useState(1);

  const topArtistsQuery = useQuery({
    queryKey: ["topArtists", page],
    staleTime: 1000 * 60 * 30, // 30m
    gcTime: 1000 * 60 * 60, // 1h
    queryFn: async () => {
      const res = await apiClient.get(`/api/top-artists/`, {
        params: { page, page_size: 50 },
      });
      return res?.data || {};
    },
  });

  const artists = useMemo(() => {
    const data = topArtistsQuery.data;
    if (Array.isArray(data)) return data;
    return Array.isArray(data?.results) ? data.results : [];
  }, [topArtistsQuery.data]);
  const pageInfo = useMemo(() => {
    const data = topArtistsQuery.data;
    if (!data || Array.isArray(data)) {
      return { count: artists.length, next: null, previous: null };
    }
    return {
      count: Number(data.count) || 0,
      next: data.next || null,
      previous: data.previous || null,
    };
  }, [artists.length, topArtistsQuery.data]);
  const isLoading = topArtistsQuery.isLoading;
  const error = topArtistsQuery.isError
    ? "Nu am putut încărca topul de artiști."
    : null;

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Top Artists</h1>

      {isLoading ? <p>Se încarcă...</p> : null}
      {error ? <p style={ui.errorText}>{error}</p> : null}

      {!isLoading && !error && artists.length === 0 ? (
        <p style={{ opacity: 0.85 }}>Nu există artiști cu rating-uri încă.</p>
      ) : null}

      {!isLoading && !error && artists.length > 0 ? (
        <ol style={{ marginTop: "16px", paddingLeft: "20px" }}>
          {artists.map((artist) => (
            <li
              key={artist.id}
              style={{ marginBottom: "12px", lineHeight: 1.3 }}
            >
              <div
                style={{ display: "flex", gap: "12px", alignItems: "center" }}
              >
                {artist.image_url ? (
                  <img
                    src={artist.image_url}
                    alt={artist.name}
                    style={{
                      width: "44px",
                      height: "44px",
                      borderRadius: "8px",
                      objectFit: "cover",
                      border: `1px solid ${ui.colors.border}`,
                      flex: "0 0 auto",
                    }}
                  />
                ) : (
                  <div
                    style={{
                      width: "44px",
                      height: "44px",
                      borderRadius: "8px",
                      background: ui.colors.mutedBg,
                      border: `1px solid ${ui.colors.border}`,
                      flex: "0 0 auto",
                    }}
                  />
                )}

                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "2px",
                  }}
                >
                  <div style={{ fontWeight: 700 }}>
                    <Link to={`/artists/${artist.slug}`}>{artist.name}</Link>
                  </div>
                  <div style={{ opacity: 0.85 }}>
                    ⭐ {formatRating(artist.average_rating)}
                    {Number.isFinite(Number(artist.ratings_count)) ? (
                      <> · {artist.ratings_count} rating-uri</>
                    ) : null}
                    {Number.isFinite(Number(artist.albums_count)) ? (
                      <> · {artist.albums_count} albume</>
                    ) : null}
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ol>
      ) : null}

      {!isLoading && !error && pageInfo.count > 50 ? (
        <div
          style={{
            marginTop: "16px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "12px",
          }}
        >
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, Number(p || 1) - 1))}
            disabled={!pageInfo.previous || page <= 1}
            style={ui.button}
          >
            Prev
          </button>

          <div style={{ opacity: 0.85 }}>
            Pagina {page} · {pageInfo.count} artiști
          </div>

          <button
            type="button"
            onClick={() => setPage((p) => Number(p || 1) + 1)}
            disabled={!pageInfo.next}
            style={ui.button}
          >
            Next
          </button>
        </div>
      ) : null}
    </div>
  );
}
