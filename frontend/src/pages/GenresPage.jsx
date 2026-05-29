import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../api/apiClient.js";
import { ui } from "../ui/ui.js";

export default function GenresPage() {
  const filtersQuery = useQuery({
    queryKey: ["albumsFilters"],
    staleTime: 1000 * 60 * 60, // 1h
    gcTime: 1000 * 60 * 60 * 2, // 2h
    queryFn: async () => {
      const res = await apiClient.get(`/api/albums/filters/`);
      return res?.data || {};
    },
  });

  const genres = useMemo(() => {
    const payload = filtersQuery.data || {};
    return Array.isArray(payload?.genres) ? payload.genres : [];
  }, [filtersQuery.data]);

  const isLoading = filtersQuery.isLoading;
  const error = filtersQuery.isError ? "Nu am putut încărca genurile." : null;

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Genuri</h1>

      {isLoading ? <p>Loading...</p> : null}
      {error ? <p style={ui.errorText}>{error}</p> : null}

      {!isLoading && !error ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
            gap: "12px",
            marginTop: "12px",
          }}
        >
          {genres.map((g) => (
            <Link
              key={g.slug}
              to={`/albums?genre=${encodeURIComponent(g.slug)}`}
              style={{
                ...ui.card,
                color: "inherit",
                textDecoration: "none",
              }}
            >
              <div style={{ fontWeight: 700 }}>{g.name}</div>
              <div style={{ opacity: 0.75, marginTop: "4px" }}>{g.slug}</div>
            </Link>
          ))}
        </div>
      ) : null}

      {!isLoading && !error && genres.length === 0 ? (
        <p style={{ opacity: 0.85 }}>Nu există genuri disponibile.</p>
      ) : null}
    </div>
  );
}
