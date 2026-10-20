import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/apiClient.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";
import { prefetchAlbum } from "../query/prefetchAlbum.js";

function releaseTypeLabel(item) {
  const type = String(item?.release_type || item?.album_release_type || "").toLowerCase();
  if (type === "single") return "Single";
  if (type === "ep") return "EP";
  if (type === "compilation") return "Compilație";
  return "Album";
}

function isSingle(item) {
  return String(item?.release_type || item?.album_release_type || "")
    .toLowerCase()
    .includes("single");
}

function ResultSection({ title, count, children, empty }) {
  return (
    <section style={ui.card}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "10px",
          marginBottom: "12px",
        }}
      >
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>{title}</h2>
        <span
          style={{
            border: `1px solid ${ui.colors.border}`,
            borderRadius: "999px",
            padding: "2px 9px",
            opacity: 0.82,
          }}
        >
          {count}
        </span>
      </div>
      {count ? children : <p style={{ margin: 0, opacity: 0.82 }}>{empty}</p>}
    </section>
  );
}

function PaginationRow({ page, totalPages, total, label, onPrev, onNext }) {
  if (total <= 10) return null;
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "10px",
        marginTop: "12px",
      }}
    >
      <button type="button" style={ui.buttonSmall} onClick={onPrev} disabled={page <= 1}>
        Prev
      </button>
      <span style={{ opacity: 0.85 }}>
        Pagina {page} / {totalPages} · {total} {label}
      </span>
      <button
        type="button"
        style={ui.buttonSmall}
        onClick={onNext}
        disabled={page >= totalPages}
      >
        Next
      </button>
    </div>
  );
}

function AlbumResultCard({ item, queryClient, baseUrl, accessToken, isAuthVerified }) {
  const slug = String(item?.slug || "").trim();
  const title = String(item?.title || "Album");
  const artistSlug = String(item?.artist_slug || "").trim();
  const artistName = String(item?.artist_name || "Artist");
  const coverUrl = item?.cover_url || item?.album_cover_url || "";

  return (
    <article
      style={{
        border: `1px solid ${ui.colors.border}`,
        borderRadius: "8px",
        padding: "10px",
        display: "grid",
        gridTemplateColumns: "56px minmax(0, 1fr)",
        gap: "10px",
        alignItems: "center",
        background: "rgba(15, 23, 42, 0.22)",
      }}
    >
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: "6px",
          overflow: "hidden",
          background: ui.colors.mutedBg,
          border: `1px solid ${ui.colors.border}`,
        }}
      >
        {coverUrl ? (
          <img
            src={coverUrl}
            alt={`Coperta ${title}`}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : null}
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontWeight: 800, overflowWrap: "anywhere" }}>
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
            title
          )}
        </div>
        <div style={{ opacity: 0.84, marginTop: "3px" }}>
          {artistSlug ? (
            <Link to={`/artists/${encodeURIComponent(artistSlug)}`}>
              {artistName}
            </Link>
          ) : (
            artistName
          )}
        </div>
        <div style={{ opacity: 0.72, marginTop: "4px" }}>
          {releaseTypeLabel(item)}
          {item?.release_date ? ` · ${String(item.release_date).slice(0, 4)}` : ""}
        </div>
      </div>
    </article>
  );
}

function SimpleLinkCard({ to, title, subtitle, badge }) {
  return (
    <article
      style={{
        border: `1px solid ${ui.colors.border}`,
        borderRadius: "8px",
        padding: "10px 12px",
        background: "rgba(15, 23, 42, 0.2)",
      }}
    >
      <div style={{ fontWeight: 800 }}>
        {to ? <Link to={to}>{title}</Link> : title}
      </div>
      {subtitle ? (
        <div style={{ opacity: 0.8, marginTop: "4px" }}>{subtitle}</div>
      ) : null}
      {badge ? (
        <div style={{ opacity: 0.72, marginTop: "5px", fontSize: "0.92em" }}>
          {badge}
        </div>
      ) : null}
    </article>
  );
}

export default function SearchResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const q = (searchParams.get("q") || "").trim();

  const genre = (searchParams.get("genre") || "").trim();
  const year = (searchParams.get("year") || "").trim();
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
  const [albumsPage, setAlbumsPage] = useState(1);
  const [singlesPage, setSinglesPage] = useState(1);
  const [songsPage, setSongsPage] = useState(1);

  useEffect(() => {
    const delay = q ? 250 : 0;
    const timer = setTimeout(() => setDebouncedQ(q), delay);

    return () => clearTimeout(timer);
  }, [q]);

  useEffect(() => {
    setAlbumsPage(1);
    setSinglesPage(1);
    setSongsPage(1);
  }, [debouncedQ, genre, year, minRating, reviewedOnly, followedOnly]);

  const empty = useMemo(() => {
    return { artists: [], albums: [], songs: [], users: [] };
  }, []);

  const searchQuery = useQuery({
    queryKey: [
      "search",
      debouncedQ,
      genre,
      year,
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
        limit: 50,
      };

      if (genre) params.genre = genre;
      if (year) params.year = year;
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
  const albums = Array.isArray(results.albums) ? results.albums : [];
  const realAlbums = albums.filter((item) => !isSingle(item));
  const singles = albums.filter((item) => isSingle(item));
  const songs = Array.isArray(results.songs) ? results.songs : [];
  const albumsTotalPages = Math.max(1, Math.ceil(realAlbums.length / 10));
  const singlesTotalPages = Math.max(1, Math.ceil(singles.length / 10));
  const songsTotalPages = Math.max(1, Math.ceil(songs.length / 10));
  const safeAlbumsPage = Math.min(albumsPage, albumsTotalPages);
  const safeSinglesPage = Math.min(singlesPage, singlesTotalPages);
  const safeSongsPage = Math.min(songsPage, songsTotalPages);
  const visibleAlbums = realAlbums.slice(
    (safeAlbumsPage - 1) * 10,
    safeAlbumsPage * 10,
  );
  const visibleSingles = singles.slice(
    (safeSinglesPage - 1) * 10,
    safeSinglesPage * 10,
  );
  const visibleSongs = songs.slice(
    (safeSongsPage - 1) * 10,
    safeSongsPage * 10,
  );
  const isLoading = hasQuery ? isDebouncing || searchQuery.isLoading : false;
  const error =
    hasQuery && !isDebouncing && searchQuery.isError
      ? "Căutarea a eșuat."
      : null;

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Căutare</h1>

      <section style={{ marginTop: "12px" }}>
        <div style={ui.card}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "12px",
              flexWrap: "wrap",
            }}
          >
            <div>
              <div style={{ fontWeight: 800 }}>Filtre albume</div>
              <div style={{ opacity: 0.76, marginTop: "2px" }}>
                Rafinează rezultatele fără să pierzi căutarea curentă.
              </div>
            </div>
            <button
              type="button"
              style={ui.buttonSmall}
              onClick={() => {
                setParam("genre", "");
                setParam("year", "");
                setParam("min_rating", "");
                setParam("reviewed_only", "");
                setParam("followed_only", "");
              }}
            >
              Curăță
            </button>
          </div>
          <div
            style={{
              marginTop: "10px",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: "12px",
            }}
          >
            <label style={{ display: "grid", gap: 6 }}>
              <span>Gen</span>
              <input
                value={genre}
                onChange={(e) => setParam("genre", e.target.value)}
                placeholder="ex: rock"
                style={ui.input}
              />
            </label>

            <label style={{ display: "grid", gap: 6 }}>
              <span>An</span>
              <input
                value={year}
                onChange={(e) => setParam("year", e.target.value)}
                placeholder="ex: 1999"
                inputMode="numeric"
                style={ui.input}
              />
            </label>

            <label style={{ display: "grid", gap: 6 }}>
              <span>Rating minim</span>
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
          </div>

          <div
            style={{
              display: "flex",
              gap: "12px",
              flexWrap: "wrap",
              marginTop: "12px",
            }}
          >
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
        </div>
      </section>

      {q ? (
        <div style={{ ...ui.card, marginTop: "12px", padding: "12px" }}>
          Rezultate pentru <strong>{q}</strong>
        </div>
      ) : null}

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

      {!q && !isLoading ? (
        <div style={{ ...ui.card, marginTop: "14px", textAlign: "center" }}>
          <h2 style={{ marginTop: 0 }}>Începe o căutare</h2>
          <p style={{ marginBottom: 0, opacity: 0.82 }}>
            Caută utilizatori, artiști, albume, single-uri sau piese din bara de sus.
          </p>
        </div>
      ) : null}

      {q && !isLoading && !error ? (
        <div style={{ marginTop: "16px", display: "grid", gap: "14px" }}>
          <ResultSection
            title="Users"
            count={isAuthenticated ? results.users?.length || 0 : 0}
            empty={
              isAuthenticated
                ? "Niciun utilizator găsit."
                : "Loghează-te ca să cauți utilizatori."
            }
          >
            {!isAuthenticated ? (
              <p style={{ margin: 0 }}>Loghează-te ca să cauți utilizatori.</p>
            ) : results.users?.length ? (
              <div style={{ display: "grid", gap: "8px" }}>
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
                    <SimpleLinkCard
                      key={`${username}-${String(id ?? "")}`}
                      to={to}
                      title={username}
                      subtitle="Utilizator"
                    />
                  );
                })}
              </div>
            ) : null}
          </ResultSection>

          <ResultSection
            title="Artists"
            count={results.artists?.length || 0}
            empty="Niciun artist găsit."
          >
            {results.artists?.length ? (
              <div style={{ display: "grid", gap: "8px" }}>
                {results.artists.map((a) => (
                  <SimpleLinkCard
                    key={a.id}
                    to={`/artists/${a.slug}`}
                    title={a.name}
                    subtitle="Artist"
                  />
                ))}
              </div>
            ) : null}
          </ResultSection>

          <ResultSection
            title="Albums"
            count={realAlbums.length}
            empty={
              genre || year || minRating || reviewedOnly || followedOnly
                ? "Niciun album găsit pentru filtrele selectate. Încearcă să ștergi sau să ajustezi filtrele."
                : "Niciun album găsit."
            }
          >
            {realAlbums.length ? (
              <div style={{ display: "grid", gap: "8px" }}>
                {visibleAlbums.map((a) => {
                  if (!a?.id) return null;
                  return (
                    <AlbumResultCard
                      key={a.id}
                      item={a}
                      queryClient={queryClient}
                      baseUrl={baseUrl}
                      accessToken={accessToken}
                      isAuthVerified={isAuthVerified}
                    />
                  );
                })}
              </div>
            ) : null}
            <PaginationRow
              page={safeAlbumsPage}
              totalPages={albumsTotalPages}
              total={realAlbums.length}
              label="albume"
              onPrev={() => setAlbumsPage((value) => Math.max(1, value - 1))}
              onNext={() =>
                setAlbumsPage((value) => Math.min(albumsTotalPages, value + 1))
              }
            />
          </ResultSection>

          <ResultSection
            title="Singles"
            count={singles.length}
            empty="Niciun single găsit."
          >
            {singles.length ? (
              <div style={{ display: "grid", gap: "8px" }}>
                {visibleSingles.map((a) => (
                  <AlbumResultCard
                    key={a.id}
                    item={a}
                    queryClient={queryClient}
                    baseUrl={baseUrl}
                    accessToken={accessToken}
                    isAuthVerified={isAuthVerified}
                  />
                ))}
              </div>
            ) : null}
            <PaginationRow
              page={safeSinglesPage}
              totalPages={singlesTotalPages}
              total={singles.length}
              label="single-uri"
              onPrev={() => setSinglesPage((value) => Math.max(1, value - 1))}
              onNext={() =>
                setSinglesPage((value) => Math.min(singlesTotalPages, value + 1))
              }
            />
          </ResultSection>

          <ResultSection title="Songs" count={songs.length} empty="Nicio melodie găsită.">
            {songs.length ? (
              <>
              <div style={{ display: "grid", gap: "8px" }}>
                {visibleSongs.map((s) => (
                  <SimpleLinkCard
                    key={s.id}
                    to={`/songs/${s.slug}`}
                    title={s.title}
                    subtitle={
                      s.artist_slug ? (
                        <span>
                          de <Link to={`/artists/${s.artist_slug}`}>{s.artist_name}</Link>
                        </span>
                      ) : null
                    }
                    badge={
                      s.album_slug ? (
                        <span>
                          din {releaseTypeLabel(s).toLowerCase()}{" "}
                          <Link to={`/albums/${s.album_slug}`}>{s.album_title}</Link>
                        </span>
                      ) : null
                    }
                  />
                ))}
              </div>
              <PaginationRow
                page={safeSongsPage}
                totalPages={songsTotalPages}
                total={songs.length}
                label="melodii"
                onPrev={() => setSongsPage((value) => Math.max(1, value - 1))}
                onNext={() =>
                  setSongsPage((value) =>
                    Math.min(songsTotalPages, value + 1),
                  )
                }
              />
              </>
            ) : null}
          </ResultSection>
        </div>
      ) : null}
    </div>
  );
}
