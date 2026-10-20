import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import PaginationControls from "../components/PaginationControls.jsx";
import { getFollowedArtists, unfollowArtist } from "../api/follows.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

function getErrorMessage(err, fallback) {
  const data = err?.response?.data;
  if (typeof data === "string" && data.trim()) return data;
  if (data && typeof data === "object") {
    const firstKey = Object.keys(data)[0];
    const val = data[firstKey];
    if (Array.isArray(val) && val[0]) return String(val[0]);
    if (typeof val === "string" && val.trim()) return val;
  }
  return fallback;
}

export default function FollowedArtistsPage() {
  const { isAuthenticated, isAuthVerified, accessToken } = useAuth();
  const queryClient = useQueryClient();

  const [error, setError] = useState(null);
  const [unfollowBusyId, setUnfollowBusyId] = useState(null);
  const [page, setPage] = useState(1);
  const itemsPerPage = 10;

  const followedArtistsQueryKey = useMemo(() => {
    return ["followedArtists", accessToken || ""];
  }, [accessToken]);

  const followedArtistsQuery = useQuery({
    queryKey: followedArtistsQueryKey,
    enabled: Boolean(isAuthVerified && accessToken),
    staleTime: 1000 * 30, // 30s
    queryFn: async () => {
      const data = await getFollowedArtists({ accessToken });
      return Array.isArray(data) ? data : [];
    },
  });

  const artists = useMemo(
    () =>
      Array.isArray(followedArtistsQuery.data) ? followedArtistsQuery.data : [],
    [followedArtistsQuery.data],
  );
  const totalPages = useMemo(() => {
    return Math.max(1, Math.ceil(artists.length / itemsPerPage));
  }, [artists.length, itemsPerPage]);

  const pageArtists = useMemo(() => {
    const start = (page - 1) * itemsPerPage;
    return artists.slice(start, start + itemsPerPage);
  }, [artists, itemsPerPage, page]);

  const isLoading = followedArtistsQuery.isLoading;
  const queryError = followedArtistsQuery.isError
    ? "Nu am putut încărca artiștii urmăriți."
    : null;

  useEffect(() => {
    // Defer setPage to avoid calling setState synchronously within effect
    const t = setTimeout(() => {
      setPage((prev) => Math.min(prev, totalPages));
    }, 0);
    return () => clearTimeout(t);
  }, [totalPages]);

  async function handleUnfollow(artistId) {
    if (!artistId) return;

    setUnfollowBusyId(artistId);
    setError(null);

    try {
      await unfollowArtist({ artistId, accessToken });
      queryClient.setQueryData(followedArtistsQueryKey, (prev) => {
        const prevArr = Array.isArray(prev) ? prev : [];
        return prevArr.filter((a) => a.artist_id !== artistId);
      });
      queryClient.invalidateQueries({ queryKey: ["followedArtists"] });
    } catch (err) {
      console.error(err);
      setError(getErrorMessage(err, "Nu am putut scoate follow."));
    } finally {
      setUnfollowBusyId(null);
    }
  }

  if (!isAuthenticated) {
    return (
      <div style={{ padding: "24px" }}>
        <h1 style={{ marginTop: 0 }}>Artiști urmăriți</h1>
        <p>Trebuie să fii logat ca să vezi artiștii urmăriți.</p>
        <p>
          <Link to="/login">Mergi la Login</Link>
        </p>
      </div>
    );
  }

  if (isAuthenticated && !isAuthVerified) {
    return (
      <div style={{ padding: "24px" }}>
        <h1 style={{ marginTop: 0 }}>Artiști urmăriți</h1>
        <p style={{ marginTop: "14px" }}>Se încarcă...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: "24px" }}>
      <h1 style={{ marginTop: 0 }}>Artiști urmăriți</h1>

      {isLoading ? <p>Se încarcă...</p> : null}
      {error || queryError ? (
        <p style={ui.errorText}>{error || queryError}</p>
      ) : null}

      {!isLoading && !(error || queryError) ? (
        artists.length ? (
          <ul style={{ paddingLeft: "18px" }}>
            {pageArtists.map((a) => (
              <li key={a.id} style={{ marginBottom: "10px" }}>
                <div
                  style={{ display: "flex", gap: "10px", alignItems: "center" }}
                >
                  <Link to={`/artists/${a.artist_slug}`}>{a.artist_name}</Link>
                  <button
                    onClick={() => handleUnfollow(a.artist_id)}
                    disabled={unfollowBusyId === a.artist_id}
                    style={ui.buttonSmall}
                  >
                    {unfollowBusyId === a.artist_id ? "..." : "Unfollow"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p>Nu urmărești încă niciun artist.</p>
        )
      ) : null}

      <PaginationControls
        page={page}
        totalPages={totalPages}
        totalCount={artists.length}
        onPrev={() => setPage((prev) => Math.max(1, prev - 1))}
        onNext={() => setPage((prev) => Math.min(totalPages, prev + 1))}
      />
    </div>
  );
}
