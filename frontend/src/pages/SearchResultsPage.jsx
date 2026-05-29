import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/apiClient.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";
import { prefetchAlbum } from "../query/prefetchAlbum.js";

export default function SearchResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const q = (searchParams.get("q") || "").trim();

  const genre = (searchParams.get("genre") || "").trim();
  const year = (searchParams.get("year") || "").trim();
  const country = (searchParams.get("country") || "").trim();
  const minRating = (searchParams.get("min_rating") || "").trim();
  const reviewedOnly = (searchParams.get("reviewed_only") || "").trim();
  const followedOnly = (searchParams.get("followed_only") || "").trim();

  function setParam(key, value) {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        const trimmed = String(value || "").trim();
        if (!trimmed) next.delete(key);
        else next.set(key, trimmed);
        return next;
      },
      { replace: true },
    );
  }

  const { baseUrl, isAuthenticated, isAuthVerified, accessToken } = useAuth();
  const queryClient = useQueryClient();

  const [debouncedQ, setDebouncedQ] = useState(q);
  useEffect(() => {
    const delay = q ? 250 : 0;
    const timer = setTimeout(() => setDebouncedQ(q), delay);

    return () => clearTimeout(timer);
  }, [q]);

  const empty = useMemo(() => {
    return { artists: [], albums: [], songs: [], users: [] };
  }, []);

  const searchQuery = useQuery({
    queryKey: [
      "search",
      debouncedQ,
      genre,
      year,
      country,
      minRating,
      reviewedOnly,
      followedOnly,
      isAuthVerified ? "auth" : "anon",
      accessToken || "",
    ],
    enabled: Boolean(debouncedQ),
    placeholderData: (prev) => prev,
    queryFn: async () => {
      const params = {
        q: debouncedQ,
        limit: 30,
      };

      if (genre) params.genre = genre;
      if (year) params.year = year;
      if (country) params.country = country;
      if (minRating) params.min_rating = minRating;
      if (reviewedOnly) params.reviewed_only = reviewedOnly;
      if (followedOnly) params.followed_only = followedOnly;

      const musicReq = apiClient.get(`/api/search/`, { params });

      const usersReq =
        isAuthVerified && accessToken
          ? apiClient.get(`/api/users/search`, {
              params: { q: debouncedQ, limit: 15 },
            })
          : Promise.resolve({ data: [] });

      const [musicRes, usersRes] = await Promise.all([musicReq, usersReq]);

      return {
        artists: musicRes.data?.artists || [],
        albums: musicRes.data?.albums || [],
        songs: musicRes.data?.songs || [],
        users: Array.isArray(usersRes.data) ? usersRes.data : [],
      };
    },
  });

  const hasQuery = Boolean(q);
  const isDebouncing = hasQuery && q !== debouncedQ;

  const results = hasQuery && !isDebouncing ? searchQuery.data || empty : empty;
  const isLoading = hasQuery ? isDebouncing || searchQuery.isLoading : false;
  const error =
    hasQuery && !isDebouncing && searchQuery.isError
      ? "Căutarea a eșuat."
      : null;

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Search</h1>

      <section style={{ marginTop: "12px" }}>
        <div style={ui.card}>
          <div style={{ fontWeight: 700 }}>Filtre (albume)</div>
          <div
            style={{
              marginTop: "10px",
              display: "flex",
              flexWrap: "wrap",
              gap: "12px",
            }}
          >
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              Gen
              <input
                value={genre}
                onChange={(e) => setParam("genre", e.target.value)}
                placeholder="ex: rock"
                style={ui.input}
              />
            </label>

            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              An
              <input
                value={year}
                onChange={(e) => setParam("year", e.target.value)}
                placeholder="ex: 1999"
                inputMode="numeric"
                style={ui.input}
              />
            </label>

            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              Țară
              <select
                value={country}
                onChange={(e) => setParam("country", e.target.value)}
                style={ui.input}
              >
                <option value="">Toate</option>
                <option value="ro">România</option>
                <option value="intl">Internațional</option>
              </select>
            </label>

            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              Rating minim
              <select
                value={minRating}
                onChange={(e) => setParam("min_rating", e.target.value)}
                style={ui.input}
              >
                <option value="">—</option>
                <option value="1">1+</option>
                <option value="2">2+</option>
                <option value="3">3+</option>
                <option value="4">4+</option>
                <option value="5">5</option>
              </select>
            </label>

            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={reviewedOnly === "1"}
                onChange={(e) =>
                  setParam("reviewed_only", e.target.checked ? "1" : "")
                }
              />
              Doar albume cu review-uri
            </label>

            {isAuthenticated ? (
              <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={followedOnly === "1"}
                  onChange={(e) =>
                    setParam("followed_only", e.target.checked ? "1" : "")
                  }
                />
                Doar artiști urmăriți
              </label>
            ) : null}
          </div>
          <div style={{ marginTop: 8, fontSize: "0.9em", opacity: 0.85 }}>
            Notă: filtrul “Țară” folosește câmpul <b>artist român</b> din baza
            de date.
          </div>
        </div>
      </section>

      {q ? <p style={{ marginTop: "6px" }}>Rezultate pentru: {q}</p> : null}

      {isLoading ? (
        <div style={{ display: "grid", gap: "10px", marginTop: "12px" }}>
          <div
            style={{
              height: "18px",
              width: "40%",
              background: ui.colors.mutedBg,
              border: `1px solid ${ui.colors.border}`,
              borderRadius: "6px",
            }}
          />
          <div
            style={{
              height: "18px",
              width: "70%",
              background: ui.colors.mutedBg,
              border: `1px solid ${ui.colors.border}`,
              borderRadius: "6px",
            }}
          />
          <div
            style={{
              height: "18px",
              width: "55%",
              background: ui.colors.mutedBg,
              border: `1px solid ${ui.colors.border}`,
              borderRadius: "6px",
            }}
          />
        </div>
      ) : null}

      {error ? <p style={ui.errorText}>{error}</p> : null}

      {!q && !isLoading ? <p>Scrie ceva în bara de search.</p> : null}

      {q && !isLoading && !error ? (
        <div style={{ marginTop: "16px", display: "grid", gap: "18px" }}>
          <div>
            <h3 style={{ marginBottom: "8px" }}>Users</h3>
            {!isAuthenticated ? (
              <p style={{ margin: 0 }}>Loghează-te ca să cauți utilizatori.</p>
            ) : results.users?.length ? (
              <ul style={{ paddingLeft: "18px", margin: 0 }}>
                {results.users.map((u) => {
                  const username = String(u?.username || "").trim();
                  const id = u?.id;
                  if (!username) return null;

                  const to = id
                    ? `/users/${encodeURIComponent(username)}?id=${encodeURIComponent(
                        String(id),
                      )}`
                    : `/users/${encodeURIComponent(username)}`;

                  return (
                    <li key={`${username}-${String(id ?? "")}`}>
                      <Link to={to}>{username}</Link>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p style={{ margin: 0 }}>Niciun utilizator găsit.</p>
            )}
          </div>

          <div>
            <h3 style={{ marginBottom: "8px" }}>Artists</h3>
            {results.artists?.length ? (
              <ul style={{ paddingLeft: "18px", margin: 0 }}>
                {results.artists.map((a) => (
                  <li key={a.id}>
                    <Link to={`/artists/${a.slug}`}>{a.name}</Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p style={{ margin: 0 }}>Niciun artist găsit.</p>
            )}
          </div>

          <div>
            <h3 style={{ marginBottom: "8px" }}>Albums</h3>
            {results.albums?.length ? (
              <ul style={{ paddingLeft: "18px", margin: 0 }}>
                {results.albums.map((a) => {
                  const slug = String(a?.slug || "").trim();
                  const title = String(a?.title || "Album");
                  if (!a?.id) return null;
                  return (
                    <li key={a.id}>
                      {slug ? (
                        <Link
                          to={`/albums/${encodeURIComponent(slug)}`}
                          onMouseEnter={() =>
                            prefetchAlbum({
                              queryClient,
                              baseUrl,
                              slug,
                              accessToken,
                              isAuthVerified,
                            })
                          }
                        >
                          {title}
                        </Link>
                      ) : (
                        <span>{title}</span>
                      )}
                      {a?.artist_slug ? (
                        <span style={{ opacity: 0.85 }}>
                          {" "}
                          —{" "}
                          <Link
                            to={`/artists/${encodeURIComponent(String(a.artist_slug))}`}
                          >
                            {String(a?.artist_name || "Artist")}
                          </Link>
                        </span>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p style={{ margin: 0 }}>
                {genre ||
                year ||
                country ||
                minRating ||
                reviewedOnly ||
                followedOnly
                  ? "Niciun album găsit pentru filtrele selectate. Încearcă să ștergi sau să ajustezi filtrele."
                  : "Niciun album găsit."}
              </p>
            )}
          </div>

          <div>
            <h3 style={{ marginBottom: "8px" }}>Songs</h3>
            {results.songs?.length ? (
              <ul style={{ paddingLeft: "18px", margin: 0 }}>
                {results.songs.map((s) => (
                  <li key={s.id}>
                    <Link to={`/songs/${s.slug}`}>{s.title}</Link>
                    {s.artist_slug ? (
                      <span>
                        {" "}
                        —{" "}
                        <Link to={`/artists/${s.artist_slug}`}>
                          {s.artist_name}
                        </Link>
                      </span>
                    ) : null}
                    {s.album_slug ? (
                      <span>
                        {" "}
                        (din{" "}
                        <Link to={`/albums/${s.album_slug}`}>
                          {s.album_title}
                        </Link>
                        )
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p style={{ margin: 0 }}>Nicio melodie găsită.</p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
