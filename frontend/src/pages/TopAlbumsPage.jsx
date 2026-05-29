import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/apiClient.js";
import { useAuth } from "../context/useAuth.js";
import { prefetchAlbum } from "../query/prefetchAlbum.js";

function formatRating(value) {
  if (value === null || value === undefined) return "—";
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  return num.toFixed(1);
}

export default function TopAlbumsPage() {
  const [searchParams] = useSearchParams();
  const year = (searchParams.get("year") || "").trim();
  const decade = (searchParams.get("decade") || "").trim();

  const queryClient = useQueryClient();
  const { baseUrl, isAuthVerified, accessToken } = useAuth();

  const topAlbumsQuery = useQuery({
    queryKey: ["topAlbums", year || "", decade || ""],
    staleTime: 1000 * 60 * 15, // 15m
    gcTime: 1000 * 60 * 60, // 1h
    placeholderData: (prev) => prev,
    queryFn: async () => {
      const params = {};
      if (year) params.year = year;
      if (decade) params.decade = decade;
      const response = await apiClient.get(`/api/top-albums/`, { params });
      return Array.isArray(response.data) ? response.data : [];
    },
  });

  const albums = useMemo(() => {
    return Array.isArray(topAlbumsQuery.data) ? topAlbumsQuery.data : [];
  }, [topAlbumsQuery.data]);
  const isLoading = topAlbumsQuery.isLoading;
  const error = topAlbumsQuery.isError
    ? "Nu am putut încărca topul de albume."
    : null;

  return (
    <div style={{ padding: "24px" }}>
      <h1>Top Albums</h1>

      {isLoading ? <p>Se încarcă...</p> : null}
      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}

      {!isLoading && !error && albums.length === 0 ? (
        <p>No albums found</p>
      ) : null}

      {!isLoading && !error && albums.length > 0 ? (
        <ol style={{ marginTop: "16px", paddingLeft: "20px" }}>
          {albums.map((album) => (
            <li key={album.id} style={{ marginBottom: "10px" }}>
              <Link
                to={`/albums/${album.slug}`}
                onMouseEnter={() =>
                  prefetchAlbum({
                    queryClient,
                    baseUrl,
                    slug: album.slug,
                    accessToken,
                    isAuthVerified,
                  })
                }
              >
                {album.title}
              </Link>{" "}
              <span style={{ opacity: 0.85 }}>
                ⭐ {formatRating(album.average_rating)}
              </span>
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}
