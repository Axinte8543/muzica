import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import {
  followArtist,
  getArtistFollowStatus,
  unfollowArtist,
} from "../api/follows.js";
import { createMetadataSuggestion } from "../api/moderation.js";
import { apiClient } from "../api/apiClient.js";
import RatingWidget from "../components/RatingWidget.jsx";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

const FILTER_OPTIONS = [
  ["albums", "Albume"],
  ["singles", "Single"],
  ["appearsOn", "Aparitii"],
];

const pageStyle = {
  ...ui.container,
  maxWidth: "1200px",
  margin: "0 auto",
};

const stateCardStyle = {
  ...ui.card,
  marginTop: "12px",
  maxWidth: "720px",
};

const heroCardStyle = {
  ...ui.card,
  padding: "20px",
};

const panelStyle = {
  ...ui.card,
  padding: "18px",
};

const compactPanelStyle = {
  ...ui.card,
  padding: "16px",
};

const heroGridStyle = {
  display: "flex",
  gap: "20px",
  flexWrap: "wrap",
  alignItems: "flex-start",
};

const heroImageShellStyle = {
  width: "180px",
  flex: "0 0 180px",
  borderRadius: "20px",
  overflow: "hidden",
  border: "1px solid var(--border-color)",
  backgroundColor: "var(--input-bg)",
  boxShadow: "var(--shadow-soft)",
};

const heroImageStyle = {
  width: "100%",
  aspectRatio: "1 / 1",
  objectFit: "cover",
  display: "block",
};

const chipRowStyle = {
  display: "flex",
  flexWrap: "wrap",
  gap: "8px",
};

const chipStyle = {
  display: "inline-flex",
  alignItems: "center",
  gap: "6px",
  padding: "6px 10px",
  borderRadius: "999px",
  border: "1px solid var(--border-color)",
  backgroundColor: "var(--button-bg)",
  color: "var(--text-color)",
  fontSize: "0.9rem",
};

const twoColumnStyle = {
  display: "flex",
  gap: "18px",
  flexWrap: "wrap",
  alignItems: "flex-start",
};

const mainColumnStyle = {
  flex: "1 1 640px",
  minWidth: 0,
  display: "grid",
  gap: "18px",
};

const sideColumnStyle = {
  flex: "0 0 330px",
  minWidth: "280px",
  display: "grid",
  gap: "18px",
  position: "sticky",
  top: "92px",
};

const discographyGridStyle = {
  display: "grid",
  gap: "14px",
  gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
  marginTop: "14px",
};

const communityGridStyle = {
  display: "grid",
  gap: "14px",
  gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
  marginTop: "14px",
};

const itemListStyle = {
  listStyle: "none",
  padding: 0,
  margin: 0,
  display: "grid",
  gap: "10px",
};

const itemCardStyle = {
  border: "1px solid var(--border-color)",
  borderRadius: "12px",
  padding: "10px 12px",
  backgroundColor: "var(--input-bg)",
  boxShadow: "var(--shadow-soft)",
};

const rankBadgeStyle = {
  width: "30px",
  height: "30px",
  borderRadius: "999px",
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  backgroundColor: "var(--button-bg)",
  border: "1px solid var(--border-color)",
  fontWeight: 700,
  flex: "0 0 30px",
};

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function formatAvg(value) {
  if (value === null || value === undefined) return "-";
  const numberValue = Number(value);
  if (Number.isNaN(numberValue)) return "-";
  return numberValue.toFixed(1);
}

function getDisplaySongTitle(song) {
  const rawTitle = String(song?.title || "").trim();
  if (rawTitle && !/^\[?unknown\]?$/i.test(rawTitle)) {
    return rawTitle;
  }

  const albumTitle = String(song?.album_title || "").trim();
  if (albumTitle) {
    return `Piesa de pe ${albumTitle}`;
  }

  return "Titlu necunoscut";
}

function LinkLabel({ to, children }) {
  if (!to) return children;
  return <Link to={to}>{children}</Link>;
}

function DiscographyGroup({
  title,
  items,
  renderItem,
  emptyText = "Nu exista inca elemente.",
  totalCount = null,
  viewMoreLink = null,
}) {
  const count = Array.isArray(items) ? items.length : 0;
  const displayCount = Number.isFinite(Number(totalCount))
    ? Number(totalCount)
    : count;

  return (
    <section style={compactPanelStyle}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
          marginBottom: "10px",
        }}
      >
        <h3 style={{ margin: 0 }}>{title}</h3>
        <span style={chipStyle}>{displayCount}</span>
      </div>

      {count ? (
        <>
          <ul style={itemListStyle}>{items.map(renderItem)}</ul>
          {viewMoreLink && displayCount > count ? (
            <div
              style={{
                marginTop: "12px",
                display: "flex",
                justifyContent: "flex-end",
              }}
            >
              <Link to={viewMoreLink} style={{ textDecoration: "none" }}>
                <button
                  type="button"
                  style={{
                    ...ui.buttonSmall,
                    backgroundColor: "rgba(245, 158, 11, 0.16)",
                    borderColor: "rgba(245, 158, 11, 0.34)",
                    fontWeight: 600,
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  Vezi toate ({displayCount}) →
                </button>
              </Link>
            </div>
          ) : null}
        </>
      ) : (
        <p style={{ margin: 0, opacity: 0.78 }}>{emptyText}</p>
      )}
    </section>
  );
}

function filterButtonStyle(active) {
  return {
    ...ui.buttonSmall,
    borderRadius: "999px",
    fontWeight: active ? 700 : 600,
    backgroundColor: active ? "rgba(245, 158, 11, 0.16)" : "var(--button-bg)",
    borderColor: active ? "rgba(245, 158, 11, 0.34)" : "var(--border-color)",
  };
}

export default function ArtistPage({ slug }) {
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken, logout } =
    useAuth();
  const queryClient = useQueryClient();

  const [artist, setArtist] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [discography, setDiscography] = useState(null);
  const [discographyError, setDiscographyError] = useState(null);
  const [topSongs, setTopSongs] = useState([]);
  const [topSongsError, setTopSongsError] = useState(null);
  const [similarArtists, setSimilarArtists] = useState([]);
  const [similarArtistsError, setSimilarArtistsError] = useState(null);

  const [filters, setFilters] = useState({
    albums: true,
    singles: true,
    appearsOn: true,
  });

  const [isSubmittingFollow, setIsSubmittingFollow] = useState(false);
  const [followActionError, setFollowActionError] = useState(null);

  const [suggestKind, setSuggestKind] = useState(null);
  const [suggestImageUrl, setSuggestImageUrl] = useState("");
  const [suggestBio, setSuggestBio] = useState("");
  const [isSubmittingSuggestion, setIsSubmittingSuggestion] = useState(false);
  const [suggestionError, setSuggestionError] = useState(null);
  const [suggestionSuccess, setSuggestionSuccess] = useState(null);

  useEffect(() => {
    if (!slug) {
      queueMicrotask(() => {
        setIsLoading(false);
        setError("Artistul nu a putut fi incarcat.");
      });
      return;
    }

    let cancelled = false;

    async function loadAll() {
      queueMicrotask(() => {
        setIsLoading(true);
        setError(null);
        setDiscography(null);
        setDiscographyError(null);
        setTopSongs([]);
        setTopSongsError(null);
        setSimilarArtists([]);
        setSimilarArtistsError(null);
      });

      try {
        const [artistResult, discographyResult, topSongsResult, similarResult] =
          await Promise.allSettled([
            apiClient.get(`/api/artists/${slug}/`),
            apiClient.get(`/api/artists/${slug}/discography/`),
            apiClient.get(`/api/artists/${slug}/top-songs/`, {
              params: { limit: 10 },
            }),
            apiClient.get(`/api/artists/${slug}/similar-artists/`, {
              params: { limit: 12 },
            }),
          ]);

        if (cancelled) return;

        if (artistResult.status !== "fulfilled") {
          const status = artistResult.reason?.response?.status;
          setError(
            status === 404
              ? "Artistul nu a fost gasit."
              : "Artistul nu a putut fi incarcat.",
          );
          return;
        }

        setArtist(artistResult.value.data);

        if (discographyResult.status === "fulfilled") {
          setDiscography(discographyResult.value.data);
        } else {
          setDiscographyError("Discografia nu a putut fi incarcata.");
        }

        if (topSongsResult.status === "fulfilled") {
          setTopSongs(asArray(topSongsResult.value.data));
        } else {
          setTopSongsError("Top songs nu a putut fi incarcat.");
        }

        if (similarResult.status === "fulfilled") {
          setSimilarArtists(asArray(similarResult.value.data));
        } else {
          setSimilarArtistsError("Similar artists nu au putut fi incarcati.");
        }
      } catch (err) {
        if (cancelled) return;
        console.error(err);
        setError("Artistul nu a putut fi incarcat.");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadAll();

    return () => {
      cancelled = true;
    };
  }, [slug]);

  useEffect(() => {
    if (!artist) return;
    const t = setTimeout(() => {
      setSuggestImageUrl(String(artist.image_url || ""));
      setSuggestBio(String(artist.bio || ""));
    }, 0);
    return () => clearTimeout(t);
  }, [artist]);

  const followStatusQueryKey = useMemo(() => {
    return [
      "artistFollowStatus",
      baseUrl || "",
      artist?.id ?? null,
      accessToken || "",
    ];
  }, [accessToken, artist?.id, baseUrl]);

  const followStatusQuery = useQuery({
    queryKey: followStatusQueryKey,
    enabled: Boolean(isAuthVerified && accessToken && artist?.id),
    queryFn: async () => {
      const status = await getArtistFollowStatus({
        baseUrl,
        artistId: artist.id,
        accessToken,
      });
      return Boolean(status);
    },
  });

  const isFollowing = Boolean(followStatusQuery.data);
  const isLoadingFollow = followStatusQuery.isLoading || isSubmittingFollow;
  const followError =
    followActionError ||
    (followStatusQuery.isError
      ? "Nu am putut verifica follow status-ul."
      : null);

  const followersCount = Number(artist?.followers_count ?? 0);
  const aliasesText = String(artist?.aliases || "").trim();
  const genres = asArray(artist?.genres);
  const hasAnyDiscographyFilter = FILTER_OPTIONS.some(([key]) => filters[key]);

  const discographySummary = useMemo(() => {
    const getCount = (items) => asArray(items).length;

    return [
      ["Albume", getCount(discography?.albums)],
      ["Single", getCount(discography?.singles)],
      ["Aparitii", getCount(discography?.appears_on)],
    ];
  }, [discography]);

  function toggleFilter(key) {
    setFilters((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function toggleSuggest(nextKind) {
    setSuggestionError(null);
    setSuggestionSuccess(null);
    setSuggestKind((current) => (current === nextKind ? null : nextKind));
  }

  async function handleToggleFollow() {
    if (!artist?.id || !isAuthVerified || !accessToken) return;

    setIsSubmittingFollow(true);
    setFollowActionError(null);

    try {
      const next = isFollowing
        ? await unfollowArtist({ baseUrl, artistId: artist.id, accessToken })
        : await followArtist({ baseUrl, artistId: artist.id, accessToken });

      queryClient.setQueryData(followStatusQueryKey, next);
      queryClient.invalidateQueries({ queryKey: ["followedArtists"] });

      setArtist((prev) => {
        if (!prev) return prev;
        const currentFollowers = Number(prev.followers_count ?? 0);
        const delta = next ? 1 : -1;
        return {
          ...prev,
          followers_count: Math.max(0, currentFollowers + delta),
        };
      });
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setFollowActionError(
        isFollowing ? "Nu am putut scoate follow." : "Nu am putut da follow.",
      );
    } finally {
      setIsSubmittingFollow(false);
    }
  }

  async function submitSuggestion() {
    if (!isAuthVerified || !accessToken) return;
    if (!artist?.id || !suggestKind) return;

    const rawValue = suggestKind === "image_url" ? suggestImageUrl : suggestBio;
    const trimmedValue = String(rawValue || "").trim();

    if (!trimmedValue) {
      setSuggestionError("Completeaza campul inainte sa trimiti.");
      return;
    }

    setIsSubmittingSuggestion(true);
    setSuggestionError(null);
    setSuggestionSuccess(null);

    try {
      const payload =
        suggestKind === "image_url"
          ? { image_url: trimmedValue }
          : { bio: trimmedValue };

      await createMetadataSuggestion({
        baseUrl,
        targetType: "artist",
        targetId: artist.id,
        kind: suggestKind,
        payload,
        note: "",
        accessToken,
      });

      setSuggestionSuccess("Sugestia a fost trimisa. Va aparea ca pending.");
      setSuggestKind(null);
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      const httpStatus = err?.response?.status;
      const data = err?.response?.data;
      let details = "";
      if (data) {
        try {
          details =
            typeof data === "string" ? data : JSON.stringify(data, null, 2);
        } catch {
          details = "";
        }
      }
      const message =
        `Nu am putut trimite sugestia${httpStatus ? ` (HTTP ${httpStatus})` : ""}.` +
        (details ? `\n${details}` : "");
      setSuggestionError(message.slice(0, 1200));
    } finally {
      setIsSubmittingSuggestion(false);
    }
  }

  if (isLoading) {
    return (
      <div style={pageStyle}>
        <div style={stateCardStyle}>
          <p style={{ margin: 0 }}>Se incarca...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={pageStyle}>
        <div style={stateCardStyle}>
          <p
            style={{ marginTop: 0, display: "flex", gap: 8, flexWrap: "wrap" }}
          >
            <Link to="/albums">← Inapoi la albume</Link>
            <span style={{ opacity: 0.55 }}>|</span>
            <Link to="/search">Cauta</Link>
          </p>
          <p style={ui.errorText}>{error}</p>
        </div>
      </div>
    );
  }

  if (!artist) {
    return (
      <div style={pageStyle}>
        <div style={stateCardStyle}>
          <p
            style={{ marginTop: 0, display: "flex", gap: 8, flexWrap: "wrap" }}
          >
            <Link to="/albums">← Inapoi la albume</Link>
            <span style={{ opacity: 0.55 }}>|</span>
            <Link to="/search">Cauta</Link>
          </p>
          <p style={{ margin: 0 }}>Artist indisponibil.</p>
        </div>
      </div>
    );
  }

  return (
    <div style={pageStyle}>
      <p style={{ marginTop: 0, display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Link to="/albums">← Inapoi la albume</Link>
        <span style={{ opacity: 0.55 }}>|</span>
        <Link to="/search">Cauta</Link>
      </p>

      <div style={heroCardStyle}>
        <div style={heroGridStyle}>
          {artist.image_url ? (
            <div style={heroImageShellStyle}>
              <img
                src={artist.image_url}
                alt={`Imagine artist ${artist.name}`}
                style={heroImageStyle}
              />
            </div>
          ) : (
            <div
              style={{
                ...heroImageShellStyle,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                minHeight: "180px",
                padding: "12px",
                textAlign: "center",
                color: "var(--text-color)",
                opacity: 0.72,
              }}
            >
              Fara imagine
            </div>
          )}

          <div style={{ flex: "1 1 360px", minWidth: 0 }}>
            <div style={chipRowStyle}>
              <span style={{ ...chipStyle, fontWeight: 700 }}>Artist</span>
              <span style={chipStyle}>{followersCount} urmaritori</span>
              <span style={chipStyle}>
                ⭐ {formatAvg(artist.average_rating)} ·{" "}
                {artist.ratings_count ?? 0} voturi
              </span>
            </div>

            <h1
              style={{
                margin: "10px 0 0",
                fontSize: "clamp(2.2rem, 4vw, 3.6rem)",
                lineHeight: 1.05,
              }}
            >
              {artist.name}
            </h1>

            <div style={{ ...chipRowStyle, marginTop: "14px" }}>
              {isAuthenticated ? (
                <button
                  type="button"
                  onClick={handleToggleFollow}
                  disabled={isLoadingFollow}
                  style={{
                    ...ui.buttonSmall,
                    borderRadius: "999px",
                    fontWeight: 700,
                    backgroundColor: isFollowing
                      ? "rgba(34, 197, 94, 0.14)"
                      : "rgba(245, 158, 11, 0.16)",
                    borderColor: isFollowing
                      ? "rgba(34, 197, 94, 0.28)"
                      : "rgba(245, 158, 11, 0.3)",
                  }}
                >
                  {isLoadingFollow
                    ? "Se actualizeaza..."
                    : isFollowing
                      ? "Unfollow"
                      : "Follow"}
                </button>
              ) : (
                <span style={chipStyle}>
                  <Link to="/login">Login</Link> ca sa urmaresti artistul.
                </span>
              )}

              {artist.spotify_url ? (
                <a
                  href={artist.spotify_url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ ...chipStyle, textDecoration: "none" }}
                >
                  Deschide Spotify
                </a>
              ) : null}
            </div>

            {genres.length ? (
              <div style={{ ...chipRowStyle, marginTop: "14px" }}>
                {genres.map((genre) => (
                  <span
                    key={genre.id || genre.slug || genre.name}
                    style={chipStyle}
                  >
                    {genre.name || genre.slug || "Genre"}
                  </span>
                ))}
              </div>
            ) : null}

            {aliasesText ? (
              <p style={{ margin: "14px 0 0", opacity: 0.82 }}>
                Alias-uri: {aliasesText}
              </p>
            ) : null}

            {followError ? (
              <div style={{ ...ui.errorText, marginTop: "10px" }}>
                {followError}
              </div>
            ) : null}

            <RatingWidget
              kind="artist"
              itemId={artist.id}
              onRated={async () => {
                try {
                  const refreshed = await apiClient.get(`/api/artists/${slug}/`);
                  setArtist(refreshed.data);
                } catch {
                  // Keep the saved user rating even if the aggregate refresh fails.
                }
              }}
            />
          </div>
        </div>

        {artist.bio ? (
          <div
            style={{
              marginTop: "18px",
              paddingTop: "18px",
              borderTop: "1px solid var(--border-color)",
            }}
          >
            <h3 style={{ margin: "0 0 8px" }}>Bio</h3>
            <p style={{ margin: 0, whiteSpace: "pre-wrap", lineHeight: 1.7 }}>
              {artist.bio}
            </p>
          </div>
        ) : null}
      </div>

      <div style={twoColumnStyle}>
        <div style={mainColumnStyle}>
          <section style={panelStyle}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "12px",
                flexWrap: "wrap",
                alignItems: "flex-start",
              }}
            >
              <div>
                <h2 style={{ margin: 0 }}>Discografie</h2>
                <p style={{ margin: "6px 0 0", opacity: 0.78 }}>
                  Vezi rapid lansarile si aparitiile artistului.
                </p>
              </div>

              <div style={chipRowStyle}>
                {discographySummary.map(([label, value]) => (
                  <span key={label} style={chipStyle}>
                    {label}: {value}
                  </span>
                ))}
              </div>
            </div>

            {discographyError ? (
              <p style={{ ...ui.errorText, marginTop: "12px" }}>
                {discographyError}
              </p>
            ) : null}

            <div style={{ marginTop: "14px" }}>
              <div style={chipRowStyle}>
                {FILTER_OPTIONS.map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => toggleFilter(key)}
                    aria-pressed={Boolean(filters[key])}
                    style={filterButtonStyle(Boolean(filters[key]))}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <p style={{ margin: "10px 0 0", opacity: 0.75 }}>
                Apasa pe filtre ca sa ascunzi sau sa afisezi sectiuni.
              </p>
            </div>

            {discography ? (
              <div style={discographyGridStyle}>
                {filters.albums ? (
                  <DiscographyGroup
                    title="Albume"
                    items={
                      Array.isArray(discography.albums)
                        ? discography.albums.slice(0, 10)
                        : []
                    }
                    totalCount={
                      Array.isArray(discography.albums)
                        ? discography.albums.length
                        : 0
                    }
                    viewMoreLink={`/artists/${artist?.slug || slug}/releases/albums`}
                    renderItem={(album) => (
                      <li key={album.id} style={itemCardStyle}>
                        <div style={{ fontWeight: 700 }}>
                          <LinkLabel
                            to={album.slug ? `/albums/${album.slug}` : null}
                          >
                            {album.title}
                          </LinkLabel>
                        </div>
                      </li>
                    )}
                  />
                ) : null}

                {filters.singles ? (
                  <DiscographyGroup
                    title="Single"
                    items={
                      Array.isArray(discography.singles)
                        ? discography.singles.slice(0, 10)
                        : []
                    }
                    totalCount={
                      Array.isArray(discography.singles)
                        ? discography.singles.length
                        : 0
                    }
                    viewMoreLink={`/artists/${artist?.slug || slug}/releases/singles`}
                    renderItem={(release) => (
                      <li key={release.id} style={itemCardStyle}>
                        <div style={{ fontWeight: 700 }}>
                          <LinkLabel
                            to={release.slug ? `/albums/${release.slug}` : null}
                          >
                            {release.title}
                          </LinkLabel>
                        </div>
                      </li>
                    )}
                  />
                ) : null}

                {/* EPs section removed */}

                {/* compilations removed */}

                {/* 'other' section removed */}

                {filters.appearsOn ? (
                  <DiscographyGroup
                    title="Aparitii"
                    items={discography.appears_on}
                    renderItem={(song) => (
                      <li key={song.id} style={itemCardStyle}>
                        <div style={{ fontWeight: 700 }}>
                          <LinkLabel
                            to={song.slug ? `/songs/${song.slug}` : null}
                          >
                            {song.title}
                          </LinkLabel>
                        </div>
                        {song.album_slug ? (
                          <div style={{ opacity: 0.78, marginTop: "4px" }}>
                            pe{" "}
                            <Link to={`/albums/${song.album_slug}`}>
                              {song.album_title}
                            </Link>
                          </div>
                        ) : null}
                      </li>
                    )}
                  />
                ) : null}
              </div>
            ) : (
              <p style={{ margin: "14px 0 0", opacity: 0.78 }}>
                Se incarca discografia...
              </p>
            )}

            {!hasAnyDiscographyFilter ? (
              <p style={{ margin: "14px 0 0", opacity: 0.78 }}>
                Selecteaza cel putin o sectiune pentru a vedea rezultate.
              </p>
            ) : null}
          </section>

          <section style={panelStyle}>
            <div>
              <h2 style={{ margin: 0 }}>Community</h2>
              <p style={{ margin: "6px 0 0", opacity: 0.78 }}>
                Top melodii si artisti asemanatori, fara sa fie inghesuit totul
                pe o singura coloana.
              </p>
            </div>

            <div style={communityGridStyle}>
              <section style={compactPanelStyle}>
                <h3 style={{ margin: 0 }}>Top songs</h3>
                {topSongsError ? (
                  <p style={{ ...ui.errorText, marginTop: "10px" }}>
                    {topSongsError}
                  </p>
                ) : topSongs.length ? (
                  <ol style={{ ...itemListStyle, marginTop: "12px" }}>
                    {topSongs.map((song, index) => (
                      <li
                        key={song.id}
                        style={{ display: "flex", gap: "12px" }}
                      >
                        <div style={rankBadgeStyle}>{index + 1}</div>
                        <div style={{ minWidth: 0, flex: 1 }}>
                          <div style={{ fontWeight: 700 }}>
                            <LinkLabel
                              to={song.slug ? `/songs/${song.slug}` : null}
                            >
                              {getDisplaySongTitle(song)}
                            </LinkLabel>
                          </div>
                          <div style={{ opacity: 0.78, marginTop: "4px" }}>
                            Nota medie: {formatAvg(song.average_rating)} ·
                            voturi: {song.ratings_count ?? 0}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p style={{ margin: "10px 0 0", opacity: 0.78 }}>—</p>
                )}
              </section>

              <section style={compactPanelStyle}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "10px",
                  }}
                >
                  <h3 style={{ margin: 0 }}>Similar artists</h3>
                  {artist?.slug ? (
                    <Link
                      to={`/similar-artists?artist=${encodeURIComponent(artist.slug)}`}
                      style={{ color: "inherit" }}
                    >
                      Deschide pagina
                    </Link>
                  ) : null}
                </div>
                {similarArtistsError ? (
                  <p style={{ ...ui.errorText, marginTop: "10px" }}>
                    {similarArtistsError}
                  </p>
                ) : similarArtists.length ? (
                  <ul style={{ ...itemListStyle, marginTop: "12px" }}>
                    {similarArtists.map((similarArtist) => {
                      const matchValue = Number(similarArtist.match);
                      const hasMatch = Number.isFinite(matchValue);

                      return (
                        <li
                          key={similarArtist.id}
                          style={{
                            ...itemCardStyle,
                            display: "flex",
                            justifyContent: "space-between",
                            gap: "10px",
                            alignItems: "center",
                          }}
                        >
                          <div style={{ minWidth: 0 }}>
                            <div style={{ fontWeight: 700 }}>
                              <LinkLabel
                                to={
                                  similarArtist.slug
                                    ? `/artists/${similarArtist.slug}`
                                    : null
                                }
                              >
                                {similarArtist.name}
                              </LinkLabel>
                            </div>
                            {hasMatch ? (
                              <div style={{ opacity: 0.78, marginTop: "4px" }}>
                                Potrivire estimata
                              </div>
                            ) : null}
                          </div>
                          {hasMatch ? (
                            <span style={chipStyle}>
                              {Math.round(matchValue * 100)}%
                            </span>
                          ) : null}
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <p style={{ margin: "10px 0 0", opacity: 0.78 }}>—</p>
                )}
              </section>
            </div>
          </section>
        </div>

        <aside style={sideColumnStyle}>
          <section style={panelStyle}>
            <h3 style={{ margin: 0 }}>Sugestii rapide</h3>
            <p style={{ margin: "6px 0 0", opacity: 0.78 }}>
              Corecteaza imaginea sau bio-ul dintr-un card simplu, fara sa cauti
              prin mai multe ecrane.
            </p>

            {!isAuthenticated ? (
              <div style={{ marginTop: "12px", opacity: 0.92 }}>
                <Link to="/login">Login</Link> ca sa trimiti o sugestie.
              </div>
            ) : (
              <>
                <div style={{ ...chipRowStyle, marginTop: "12px" }}>
                  <button
                    type="button"
                    onClick={() => toggleSuggest("image_url")}
                    style={filterButtonStyle(suggestKind === "image_url")}
                  >
                    Imagine
                  </button>
                  <button
                    type="button"
                    onClick={() => toggleSuggest("bio")}
                    style={filterButtonStyle(suggestKind === "bio")}
                  >
                    Bio
                  </button>
                </div>

                {suggestKind === "image_url" ? (
                  <div
                    style={{ marginTop: "12px", display: "grid", gap: "8px" }}
                  >
                    <input
                      value={suggestImageUrl}
                      onChange={(e) => setSuggestImageUrl(e.target.value)}
                      placeholder="URL imagine artist"
                      style={{ ...ui.input, width: "100%" }}
                    />
                    <button
                      type="button"
                      onClick={submitSuggestion}
                      disabled={isSubmittingSuggestion}
                      style={ui.button}
                    >
                      {isSubmittingSuggestion
                        ? "Trimit..."
                        : "Trimite sugestia"}
                    </button>
                  </div>
                ) : null}

                {suggestKind === "bio" ? (
                  <div
                    style={{ marginTop: "12px", display: "grid", gap: "8px" }}
                  >
                    <textarea
                      value={suggestBio}
                      onChange={(e) => setSuggestBio(e.target.value)}
                      placeholder="Propune un bio mai bun"
                      rows={6}
                      style={{ ...ui.input, width: "100%" }}
                    />
                    <button
                      type="button"
                      onClick={submitSuggestion}
                      disabled={isSubmittingSuggestion}
                      style={ui.button}
                    >
                      {isSubmittingSuggestion
                        ? "Trimit..."
                        : "Trimite sugestia"}
                    </button>
                  </div>
                ) : null}
              </>
            )}

            {suggestionError ? (
              <div
                style={{
                  ...ui.errorText,
                  marginTop: "10px",
                  whiteSpace: "pre-wrap",
                }}
              >
                {suggestionError}
              </div>
            ) : null}
            {suggestionSuccess ? (
              <div style={{ marginTop: "10px", opacity: 0.9 }}>
                {suggestionSuccess}
              </div>
            ) : null}
          </section>

          <section style={panelStyle}>
            <h3 style={{ margin: 0 }}>Filtre discografie</h3>
            <p style={{ margin: "6px 0 0", opacity: 0.78 }}>
              Alege doar sectiunile care te intereseaza.
            </p>

            <div style={{ ...chipRowStyle, marginTop: "12px" }}>
              {FILTER_OPTIONS.map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => toggleFilter(key)}
                  aria-pressed={Boolean(filters[key])}
                  style={filterButtonStyle(Boolean(filters[key]))}
                >
                  {label}
                </button>
              ))}
            </div>

            {discographySummary.length ? (
              <div style={{ ...chipRowStyle, marginTop: "12px" }}>
                {discographySummary.map(([label, value]) => (
                  <span key={label} style={chipStyle}>
                    {label}: {value}
                  </span>
                ))}
              </div>
            ) : null}
          </section>
        </aside>
      </div>
    </div>
  );
}
