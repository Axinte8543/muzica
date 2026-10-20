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
  const [searchParams, setSearchParams] = useSearchParams();
  const year = (searchParams.get("year") || "").trim();
  const decade = (searchParams.get("decade") || "").trim();
  const page = Math.max(1, Number(searchParams.get("page") || 1) || 1);

  const queryClient = useQueryClient();
  const { baseUrl, isAuthVerified, accessToken } = useAuth();

  const topAlbumsQuery = useQuery({
    queryKey: ["topAlbums", year || "", decade || "", page],
    staleTime: 1000 * 60 * 15, // 15m
    gcTime: 1000 * 60 * 60, // 1h
    placeholderData: (prev) => prev,
    queryFn: async () => {
      const params = { page, page_size: 50 };
      if (year) params.year = year;
      if (decade) params.decade = decade;
      const response = await apiClient.get(`/api/top-albums/`, { params });
      return response.data;
    },
  });

  const data = topAlbumsQuery.data;
  const albums = useMemo(() => {
    if (Array.isArray(data)) return data;
    return Array.isArray(data?.results) ? data.results : [];
  }, [data]);
  const count = Number(data?.count ?? albums.length) || 0;
  const totalPages = Math.max(1, Math.ceil(count / 50));
  const hasNext = Boolean(data?.next) || page < totalPages;
  const hasPrevious = Boolean(data?.previous) || page > 1;
  const isLoading = topAlbumsQuery.isLoading;
  const error = topAlbumsQuery.isError
    ? "Nu am putut încărca topul de albume."
    : null;

  function goToPage(nextPage) {
    const params = new URLSearchParams(searchParams);
    const safePage = Math.max(1, nextPage);
    if (safePage === 1) {
      params.delete("page");
    } else {
      params.set("page", String(safePage));
    }
    setSearchParams(params);
  }

  return (
    <div style={{ padding: "24px" }}>
      <h1>Top Albums</h1>
      <p style={{ opacity: 0.82, marginTop: 0 }}>
        Se afișează câte 50 de albume pe pagină.
      </p>

      {isLoading ? <p>Se încarcă...</p> : null}
      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}

      {!isLoading && !error && albums.length === 0 ? (
        <p>Nu am găsit albume.</p>
      ) : null}

      {!isLoading && !error && albums.length > 0 ? (
        <ol
          start={(page - 1) * 50 + 1}
          style={{ marginTop: "16px", paddingLeft: "20px" }}
        >
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

      {!isLoading && !error && albums.length > 0 ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            marginTop: "20px",
          }}
        >
          <button
            type="button"
            onClick={() => goToPage(page - 1)}
            disabled={!hasPrevious}
          >
            Previous
          </button>
          <span>
            Page {page} / {totalPages}
          </span>
          <button
            type="button"
            onClick={() => goToPage(page + 1)}
            disabled={!hasNext}
          >
            Next
          </button>
        </div>
      ) : null}
    </div>
  );
}
