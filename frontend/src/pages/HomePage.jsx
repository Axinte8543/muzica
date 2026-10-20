import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { trackAnalyticsEvent } from "../api/analytics.js";
import { getHome } from "../api/home.js";
import { getOnboardingStatus } from "../api/onboarding.js";
import { subscribeLiveFeed } from "../api/live.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";
import SimilarUsers from "../components/SimilarUsers.jsx";
import WeeklyChallengeRecapBanner from "../components/WeeklyChallengeRecapBanner.jsx";

function getYearFromDate(dateString) {
  if (!dateString) return "";
  const match = String(dateString).match(/^\d{4}/);
  return match ? match[0] : "";
}

function formatActivity(item) {
  const actor = item?.actor_username || "Utilizator";
  const name = item?.target_name || "";

  switch (item?.activity_type) {
    case "rate_album": {
      const rating = Number(item?.rating);
      const stars = Number.isFinite(rating) ? ` ⭐${rating}` : "";
      return `${actor} a notat ${name}${stars}`.trim();
    }
    case "review_album":
      return `${actor} a scris un review la ${name}`.trim();
    case "follow_artist":
      return `${actor} a urmărit ${name}`.trim();
    case "create_list":
      return `${actor} a creat lista ${name}`.trim();
    default:
      return `${actor} a făcut o acțiune`.trim();
  }
}

function scoreToPercent(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return null;
  const pct = num <= 1 ? num * 100 : num;
  return Math.max(0, Math.min(100, Math.round(pct)));
}

function pickVariant(seed, key) {
  const input = `${String(seed)}:${key}`;
  let hash = 0;
  for (let index = 0; index < input.length; index += 1) {
    hash = (hash * 31 + input.charCodeAt(index)) >>> 0;
  }
  return hash % 2 === 0 ? "A" : "B";
}

function AlbumGrid({ albums }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
        gap: "16px",
        marginTop: "12px",
      }}
    >
      {albums.map((album) => {
        const year = getYearFromDate(album.release_date);

        const CardInner = (
          <div style={ui.card}>
            {album.cover_url ? (
              <img
                src={album.cover_url}
                alt={`Coperta albumului ${album.title}`}
                style={{
                  width: "100%",
                  aspectRatio: "1 / 1",
                  objectFit: "cover",
                  borderRadius: "8px",
                  display: "block",
                }}
              />
            ) : (
              <div
                style={{
                  width: "100%",
                  aspectRatio: "1 / 1",
                  borderRadius: "8px",
                  background: ui.colors.mutedBg,
                }}
              />
            )}

            <div style={{ marginTop: "10px" }}>
              <div style={{ fontWeight: 700 }}>{album.title}</div>
              <div style={{ marginTop: "4px" }}>{album.artist_name}</div>
              <div style={{ marginTop: "4px", opacity: 0.8 }}>{year}</div>
            </div>
          </div>
        );

        return album.slug ? (
          <Link
            key={album.id}
            to={`/albums/${album.slug}`}
            style={{ color: "inherit", textDecoration: "none" }}
          >
            {CardInner}
          </Link>
        ) : (
          <div key={album.id}>{CardInner}</div>
        );
      })}
    </div>
  );
}

export default function HomePage() {
  const navigate = useNavigate();
  const { accessToken, isAuthVerified, user } = useAuth();
  const homeTrackedRef = useRef(false);

  const [searchValue, setSearchValue] = useState("");

  const [recommendations, setRecommendations] = useState([]);
  const [friendsRecommendations, setFriendsRecommendations] = useState([]);
  const [friendsActivity, setFriendsActivity] = useState([]);
  const [genres, setGenres] = useState([]);
  const [bestAlbums, setBestAlbums] = useState([]);
  const [popularAlbums, setPopularAlbums] = useState([]);
  const [weeklyMostListenedAlbums, setWeeklyMostListenedAlbums] = useState([]);
  const [popularReviews, setPopularReviews] = useState([]);
  const [newReleases, setNewReleases] = useState([]);
  const [recentAlbums, setRecentAlbums] = useState([]);
  const [topAlbums2025, setTopAlbums2025] = useState([]);
  const [trendingAlbums, setTrendingAlbums] = useState([]);
  const [trendingArtists, setTrendingArtists] = useState([]);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const experimentSeed = user?.id ?? user?.user_id ?? accessToken ?? "guest";
  const heroVariant = pickVariant(experimentSeed, "home-hero-cta");
  const feedVariant = pickVariant(experimentSeed, "home-feed-cta");
  const heroTitle =
    heroVariant === "B"
      ? "Găsește rapid albume și artiști noi."
      : "Explorează muzica românească într-un singur loc.";
  const heroDescription =
    heroVariant === "B"
      ? "Urmărești artiști, notezi albume și revii ușor la muzica pe care vrei să o asculți."
      : "Cauți artiști, notezi albume, citești păreri și îți organizezi descoperirile în liste.";
  const searchButtonLabel =
    heroVariant === "B" ? "Începe căutarea" : "Caută acum";
  const feedHeading =
    feedVariant === "B" ? "Ce merită văzut acum" : "Recomandate pentru tine";
  const recommendationsLabel =
    feedVariant === "B" ? "Vezi recomandări" : "Recomandări";
  const similarUsersLabel =
    feedVariant === "B" ? "Vezi utilizatori similari" : "Utilizatori similari";
  const statsLabel =
    feedVariant === "B" ? "Deschide statistici" : "Statistici muzicale";
  const feedButtons =
    feedVariant === "B"
      ? [
          {
            label: recommendationsLabel,
            to: "/recommendations",
            name: "recommendations",
          },
          { label: statsLabel, to: "/music-stats", name: "music_stats" },
          {
            label: similarUsersLabel,
            to: "/similar-users",
            name: "similar_users",
          },
        ]
      : [
          {
            label: recommendationsLabel,
            to: "/recommendations",
            name: "recommendations",
          },
          {
            label: similarUsersLabel,
            to: "/similar-users",
            name: "similar_users",
          },
          { label: statsLabel, to: "/music-stats", name: "music_stats" },
        ];

  useEffect(() => {
    let isCancelled = false;
    const safeAccessToken = isAuthVerified ? accessToken : null;

    async function load() {
      if (!isCancelled) {
        setIsLoading(true);
        setError(null);
      }

      try {
        const data = await getHome({
          accessToken: safeAccessToken,
          recLimit: 8,
          friendsRecLimit: 8,
          activityLimit: 5,
          popularLimit: 8,
          weeklyPopularLimit: 10,
          weeklyListensLimit: 8,
          popularReviewsLimit: 5,
          genresLimit: 12,
          bestLimit: 5,
          newLimit: 8,
          recentLimit: 8,
          top2025Limit: 8,
          trendingLimit: 8,
        });

        if (isCancelled) return;
        setRecommendations(
          Array.isArray(data?.recommendations) ? data.recommendations : [],
        );
        setFriendsRecommendations(
          Array.isArray(data?.friends_recommendations)
            ? data.friends_recommendations
            : [],
        );
        setFriendsActivity(
          Array.isArray(data?.friends_activity)
            ? data.friends_activity.slice(0, 5)
            : [],
        );
        setGenres(Array.isArray(data?.genres) ? data.genres : []);
        setBestAlbums(Array.isArray(data?.best_albums) ? data.best_albums : []);
        setPopularAlbums(
          Array.isArray(data?.popular_albums) ? data.popular_albums : [],
        );
        setWeeklyMostListenedAlbums(
          Array.isArray(data?.weekly_most_listened_albums)
            ? data.weekly_most_listened_albums
            : [],
        );
        setPopularReviews(
          Array.isArray(data?.popular_reviews) ? data.popular_reviews : [],
        );
        setNewReleases(
          Array.isArray(data?.new_releases) ? data.new_releases : [],
        );
        setRecentAlbums(
          Array.isArray(data?.recent_albums) ? data.recent_albums : [],
        );
        setTopAlbums2025(
          Array.isArray(data?.top_albums_2025) ? data.top_albums_2025 : [],
        );

        setTrendingAlbums(
          Array.isArray(data?.trending_albums) ? data.trending_albums : [],
        );
        setTrendingArtists(
          Array.isArray(data?.trending_artists) ? data.trending_artists : [],
        );
      } catch (err) {
        const status = err?.response?.status;
        if (!isCancelled) {
          if (status === 401 && !isAuthVerified) {
            setError(null);
          } else {
            setError("Nu am putut încărca homepage-ul.");
          }
        }
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    // Defer initial load to avoid synchronous setState calls inside the effect
    const t = setTimeout(() => {
      load();
    }, 0);

    return () => {
      isCancelled = true;
      clearTimeout(t);
    };
  }, [accessToken, isAuthVerified]);

  useEffect(() => {
    if (!isAuthVerified || !accessToken) return undefined;

    return subscribeLiveFeed({
      baseUrl: null,
      accessToken,
      kind: "activity",
      scope: "friends",
      limit: 5,
      interval: 5,
      onSnapshot: (payload) => {
        setFriendsActivity(Array.isArray(payload) ? payload.slice(0, 5) : []);
      },
    });
  }, [accessToken, isAuthVerified]);

  // Check if user needs onboarding
  useEffect(() => {
    async function checkOnboarding() {
      if (accessToken && isAuthVerified) {
        try {
          const status = await getOnboardingStatus();
          if (!status?.is_completed) {
            navigate("/onboarding");
          }
        } catch {
          // If there's an error checking status, don't force redirect
        }
      }
    }

    checkOnboarding();
  }, [accessToken, isAuthVerified, navigate]);

  useEffect(() => {
    if (!isAuthVerified || !accessToken || homeTrackedRef.current) return;
    homeTrackedRef.current = true;
    void trackAnalyticsEvent({
      baseUrl: null,
      accessToken,
      eventName: "home_view",
      targetType: "page",
      targetId: user?.id ?? user?.user_id ?? null,
      properties: {
        hero_variant: heroVariant,
        feed_variant: feedVariant,
      },
    }).catch(() => {});
  }, [
    accessToken,
    feedVariant,
    heroVariant,
    isAuthVerified,
    user?.id,
    user?.user_id,
  ]);

  function handleSearchSubmit(e) {
    e.preventDefault();
    const q = searchValue.trim();
    void trackAnalyticsEvent({
      baseUrl: null,
      accessToken,
      eventName: "home_cta_click",
      targetType: "cta",
      properties: {
        cta: "search_submit",
        hero_variant: heroVariant,
      },
    }).catch(() => {});
    navigate(`/search?q=${encodeURIComponent(q)}`);
  }

  const heroMetrics = [
    {
      label: "Recomandări",
      value: recommendations.length + friendsRecommendations.length,
    },
    {
      label: "Albume trending",
      value: trendingAlbums.length,
    },
    {
      label: "Genuri",
      value: genres.length,
    },
    {
      label: "Artiști în creștere",
      value: trendingArtists.length,
    },
  ];

  return (
    <div style={{ ...ui.container, paddingTop: 0 }}>
      <WeeklyChallengeRecapBanner />

      <section
        style={{
          ...ui.card,
          position: "relative",
          overflow: "hidden",
          padding: "28px",
          marginBottom: "22px",
          color: "#f8fafc",
          background:
            "linear-gradient(135deg, rgba(15, 23, 42, 0.96) 0%, rgba(30, 41, 59, 0.92) 52%, rgba(17, 24, 39, 0.98) 100%)",
          border: "1px solid rgba(148, 163, 184, 0.22)",
          boxShadow: "0 28px 70px rgba(15, 23, 42, 0.28)",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: "auto -40px -50px auto",
            width: "220px",
            height: "220px",
            borderRadius: "9999px",
            background: "rgba(59, 130, 246, 0.18)",
            filter: "blur(26px)",
          }}
        />
        <div
          style={{
            position: "absolute",
            inset: "-30px auto auto -60px",
            width: "180px",
            height: "180px",
            borderRadius: "9999px",
            background: "rgba(245, 158, 11, 0.22)",
            filter: "blur(24px)",
          }}
        />

        <div
          style={{
            position: "relative",
            display: "grid",
            gridTemplateColumns: "minmax(0, 1.4fr) minmax(260px, 0.9fr)",
            gap: "22px",
            alignItems: "center",
          }}
        >
          <div>
            <h1
              style={{
                margin: "14px 0 10px",
                maxWidth: "12ch",
                color: "#f8fafc",
                textShadow: "0 10px 30px rgba(15, 23, 42, 0.28)",
              }}
            >
              {heroTitle}
            </h1>
            <p
              style={{
                margin: 0,
                maxWidth: "58ch",
                fontSize: "1.02rem",
                color: "rgba(226, 232, 240, 0.92)",
              }}
            >
              {heroDescription}
            </p>

            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "10px",
                marginTop: "16px",
              }}
            >
              {heroMetrics.map((metric) => (
                <div
                  key={metric.label}
                  style={{
                    minWidth: "120px",
                    padding: "10px 14px",
                    borderRadius: "16px",
                    border: "1px solid rgba(255, 255, 255, 0.12)",
                    backgroundColor: "rgba(255,255,255,0.07)",
                    boxShadow: "0 10px 24px rgba(15, 23, 42, 0.18)",
                    backdropFilter: "blur(10px)",
                  }}
                >
                  <div
                    style={{
                      fontSize: "1.18rem",
                      fontWeight: 800,
                      color: "#f8fafc",
                    }}
                  >
                    {metric.value}
                  </div>
                  <div
                    style={{
                      fontSize: "0.85rem",
                      opacity: 0.82,
                      color: "rgba(226, 232, 240, 0.92)",
                    }}
                  >
                    {metric.label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gap: "12px",
              padding: "18px",
              borderRadius: "22px",
              backgroundColor: "rgba(15, 23, 42, 0.56)",
              border: "1px solid rgba(148, 163, 184, 0.18)",
              boxShadow: "0 22px 48px rgba(15, 23, 42, 0.28)",
              backdropFilter: "blur(18px)",
            }}
          >
            <div
              style={{ fontWeight: 800, fontSize: "1.05rem", color: "#f8fafc" }}
            >
              Caută rapid
            </div>
            <p style={{ margin: 0, color: "rgba(226, 232, 240, 0.88)" }}>
              Găsești albume, artiști, piese și utilizatori fără să pierzi
              contextul.
            </p>
            <form
              onSubmit={handleSearchSubmit}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "10px",
              }}
            >
              <input
                type="search"
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                placeholder="Caută un album, artist sau piesă"
                style={{
                  flex: 1,
                  ...ui.input,
                  backgroundColor: "rgba(15, 23, 42, 0.82)",
                  color: "#f8fafc",
                  border: "1px solid rgba(148, 163, 184, 0.22)",
                }}
              />
              <button type="submit" style={ui.button}>
                {searchButtonLabel}
              </button>
            </form>

          </div>
        </div>
      </section>

      {isLoading ? <p style={{ marginTop: "14px" }}>Se încarcă...</p> : null}
      {error ? (
        <p style={{ ...ui.errorText, marginTop: "14px" }} role="alert">
          {error}
        </p>
      ) : null}

      <div
        style={{
          display: "flex",
          gap: "18px",
          marginTop: "18px",
          alignItems: "flex-start",
        }}
      >
        <aside style={{ width: "260px", minWidth: "260px" }}>
          <div style={{ ...ui.card }}>
            <div style={{ fontWeight: 700, marginBottom: "10px" }}>Genuri</div>

            {!isLoading && !error && genres.length === 0 ? (
              <div style={{ opacity: 0.9 }}>Nu există genuri.</div>
            ) : null}

            {!isLoading && !error && genres.length > 0 ? (
              <div style={{ display: "grid", gap: "8px" }}>
                {genres.map((g) => (
                  <Link
                    key={g.slug}
                    to={`/albums?genre=${encodeURIComponent(g.slug)}`}
                    style={{ textDecoration: "none", color: "inherit" }}
                  >
                    <div
                      style={{
                        padding: "6px 8px",
                        border: `1px solid ${ui.colors.border}`,
                        borderRadius: "8px",
                      }}
                    >
                      {g.name}
                    </div>
                  </Link>
                ))}
              </div>
            ) : null}
          </div>

          <div style={{ ...ui.card, marginTop: "14px" }}>
            <div style={{ fontWeight: 700, marginBottom: "10px" }}>Liste</div>

            <div style={{ display: "grid", gap: "8px" }}>
              <Link
                to="/lists#public-lists"
                style={{
                  ...ui.button,
                  textDecoration: "none",
                  color: "inherit",
                }}
              >
                Toate listele
              </Link>
              {isAuthVerified ? (
                <Link
                  to="/my-lists"
                  style={{
                    ...ui.button,
                    textDecoration: "none",
                    color: "inherit",
                  }}
                >
                  Listele mele
                </Link>
              ) : null}
            </div>
          </div>

          <div style={{ ...ui.card, marginTop: "14px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "10px",
              }}
            >
              <div style={{ fontWeight: 700 }}>Best albums</div>
              <Link
                to="/top-albums"
                style={{
                  ...ui.button,
                  textDecoration: "none",
                  color: "inherit",
                  display: "inline-block",
                }}
              >
                Vezi toate
              </Link>
            </div>

            {!isLoading && !error && bestAlbums.length === 0 ? (
              <div style={{ marginTop: "10px", opacity: 0.9 }}>
                Nu am găsit albume.
              </div>
            ) : null}

            {!isLoading && !error && bestAlbums.length > 0 ? (
              <div style={{ marginTop: "10px", display: "grid", gap: "10px" }}>
                {bestAlbums.map((a) => {
                  const Row = (
                    <div
                      style={{
                        display: "flex",
                        gap: "10px",
                        alignItems: "center",
                      }}
                    >
                      {a.cover_url ? (
                        <img
                          src={a.cover_url}
                          alt={`Coperta albumului ${a.title}`}
                          style={{
                            width: "44px",
                            height: "44px",
                            borderRadius: "8px",
                            objectFit: "cover",
                            display: "block",
                          }}
                        />
                      ) : (
                        <div
                          style={{
                            width: "44px",
                            height: "44px",
                            borderRadius: "8px",
                            background: ui.colors.mutedBg,
                          }}
                        />
                      )}

                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontWeight: 700, lineHeight: 1.2 }}>
                          {a.title}
                        </div>
                        <div style={{ marginTop: "2px", opacity: 0.85 }}>
                          {a.artist_name}
                        </div>
                      </div>
                    </div>
                  );

                  return a.slug ? (
                    <Link
                      key={a.slug}
                      to={`/albums/${a.slug}`}
                      style={{ textDecoration: "none", color: "inherit" }}
                    >
                      {Row}
                    </Link>
                  ) : (
                    <div key={a.id || a.title}>{Row}</div>
                  );
                })}
              </div>
            ) : null}
          </div>
        </aside>

        <main style={{ flex: 1 }}>
          <section style={{ marginTop: "0px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "12px",
              }}
            >
              <h2 style={{ margin: 0 }}>{feedHeading}</h2>
              <div style={{ display: "flex", gap: "8px" }}>
                {feedButtons.map((button) => (
                  <Link
                    key={button.name}
                    to={button.to}
                    onClick={() =>
                      void trackAnalyticsEvent({
                        baseUrl: null,
                        accessToken,
                        eventName: "home_cta_click",
                        targetType: "cta",
                        properties: {
                          cta: button.name,
                          feed_variant: feedVariant,
                        },
                      }).catch(() => {})
                    }
                    style={{
                      ...ui.button,
                      textDecoration: "none",
                      color: "inherit",
                      display: "inline-block",
                    }}
                  >
                    {button.label}
                  </Link>
                ))}
              </div>
            </div>
            {!isLoading && !error && recommendations.length === 0 ? (
              <div style={{ marginTop: "10px" }}>
                <p style={{ margin: 0 }}>Încă nu ai recomandări.</p>
                <p style={{ marginTop: "8px", opacity: 0.9 }}>
                  Notează mai multe albume ca să primești recomandări.
                </p>
              </div>
            ) : null}

            {!isLoading && !error && recommendations.length > 0 ? (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                  gap: "16px",
                  marginTop: "12px",
                }}
              >
                {recommendations.map((rec) => {
                  const albumTitle = rec?.album || "Album";
                  const artistName = rec?.artist || "Artist";
                  const albumSlug = rec?.album_slug;
                  const coverUrl = rec?.cover_url;
                  const reason = String(rec?.reason || "").trim();
                  const matchPct = scoreToPercent(rec?.score);

                  const CardInner = (
                    <div style={ui.card}>
                      {coverUrl ? (
                        <img
                          src={coverUrl}
                          alt={`Coperta albumului ${albumTitle}`}
                          style={{
                            width: "100%",
                            aspectRatio: "1 / 1",
                            objectFit: "cover",
                            borderRadius: "8px",
                            display: "block",
                          }}
                        />
                      ) : (
                        <div
                          style={{
                            width: "100%",
                            aspectRatio: "1 / 1",
                            borderRadius: "8px",
                            background: ui.colors.mutedBg,
                          }}
                        />
                      )}

                      <div style={{ marginTop: "10px" }}>
                        <div style={{ fontWeight: 700 }}>{albumTitle}</div>
                        <div style={{ marginTop: "4px" }}>{artistName}</div>
                        {matchPct !== null ? (
                          <div style={{ marginTop: "6px", opacity: 0.9 }}>
                            Potrivire: {matchPct}%
                          </div>
                        ) : null}
                        {reason ? (
                          <div style={{ marginTop: "6px", opacity: 0.85 }}>
                            {reason}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  );

                  return albumSlug ? (
                    <Link
                      key={albumSlug}
                      to={`/albums/${albumSlug}`}
                      style={{ color: "inherit", textDecoration: "none" }}
                    >
                      {CardInner}
                    </Link>
                  ) : (
                    <div key={`${albumTitle}-${artistName}`}>{CardInner}</div>
                  );
                })}
              </div>
            ) : null}
          </section>

          <section style={{ marginTop: "26px" }}>
            <h2 style={{ margin: 0 }}>
              Pentru că prietenilor tăi le-au plăcut
            </h2>

            {!isLoading && !error && friendsRecommendations.length === 0 ? (
              <div style={{ marginTop: "10px" }}>
                <p style={{ margin: 0 }}>
                  Încă nu ai recomandări bazate pe prieteni.
                </p>
                <p style={{ marginTop: "8px", opacity: 0.9 }}>
                  E nevoie de mai multă activitate — adaugă prieteni și notează
                  mai multe albume.
                </p>
              </div>
            ) : null}

            {!isLoading && !error && friendsRecommendations.length > 0 ? (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                  gap: "16px",
                  marginTop: "12px",
                }}
              >
                {friendsRecommendations.map((rec) => {
                  const albumTitle = rec?.album || "Album";
                  const artistName = rec?.artist || "Artist";
                  const albumSlug = rec?.album_slug;
                  const coverUrl = rec?.cover_url;
                  const reason = String(rec?.reason || "").trim();
                  const matchPct = scoreToPercent(rec?.score);

                  const CardInner = (
                    <div style={ui.card}>
                      {coverUrl ? (
                        <img
                          src={coverUrl}
                          alt={`Coperta albumului ${albumTitle}`}
                          style={{
                            width: "100%",
                            aspectRatio: "1 / 1",
                            objectFit: "cover",
                            borderRadius: "8px",
                            display: "block",
                          }}
                        />
                      ) : (
                        <div
                          style={{
                            width: "100%",
                            aspectRatio: "1 / 1",
                            borderRadius: "8px",
                            background: ui.colors.mutedBg,
                          }}
                        />
                      )}

                      <div style={{ marginTop: "10px" }}>
                        <div style={{ fontWeight: 700 }}>{albumTitle}</div>
                        <div style={{ marginTop: "4px" }}>{artistName}</div>
                        {matchPct !== null ? (
                          <div style={{ marginTop: "6px", opacity: 0.9 }}>
                            Potrivire: {matchPct}%
                          </div>
                        ) : null}
                        {reason ? (
                          <div style={{ marginTop: "6px", opacity: 0.85 }}>
                            {reason}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  );

                  return albumSlug ? (
                    <Link
                      key={albumSlug}
                      to={`/albums/${albumSlug}`}
                      style={{ color: "inherit", textDecoration: "none" }}
                    >
                      {CardInner}
                    </Link>
                  ) : (
                    <div key={`${albumTitle}-${artistName}`}>{CardInner}</div>
                  );
                })}
              </div>
            ) : null}
          </section>

          <section style={{ marginTop: "26px" }}>
            <h2 style={{ margin: 0 }}>Trending (ultimele 7 zile)</h2>

            {!isLoading && !error && trendingAlbums.length === 0 ? (
              <div style={{ marginTop: "10px", opacity: 0.9 }}>
                Nu avem încă albume trending.
              </div>
            ) : null}

            {!isLoading && !error && trendingAlbums.length > 0 ? (
              <AlbumGrid albums={trendingAlbums} />
            ) : null}

            {!isLoading && !error ? (
              <div style={{ ...ui.card, marginTop: "14px" }}>
                <div style={{ fontWeight: 700, marginBottom: "10px" }}>
                  Artiști în creștere
                </div>

                {trendingArtists.length ? (
                  <div style={{ display: "grid", gap: "8px" }}>
                    {trendingArtists.map((a) => {
                      const slug = String(a?.slug || "").trim();
                      const name = String(a?.name || "Artist");
                      if (!slug) return null;

                      return (
                        <Link
                          key={slug}
                          to={`/artists/${encodeURIComponent(slug)}`}
                          style={{ textDecoration: "none", color: "inherit" }}
                        >
                          <div
                            style={{
                              display: "flex",
                              gap: "10px",
                              alignItems: "center",
                              padding: "8px",
                              border: `1px solid ${ui.colors.border}`,
                              borderRadius: "10px",
                            }}
                          >
                            {a?.image_url ? (
                              <img
                                src={a.image_url}
                                alt={`Imagine artist ${name}`}
                                style={{
                                  width: "44px",
                                  height: "44px",
                                  borderRadius: "10px",
                                  objectFit: "cover",
                                  display: "block",
                                }}
                              />
                            ) : (
                              <div
                                style={{
                                  width: "44px",
                                  height: "44px",
                                  borderRadius: "10px",
                                  background: ui.colors.mutedBg,
                                }}
                              />
                            )}
                            <div style={{ fontWeight: 700 }}>{name}</div>
                          </div>
                        </Link>
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ opacity: 0.9 }}>
                    Nu avem încă artiști trending.
                  </div>
                )}
              </div>
            ) : null}
          </section>

          <section style={{ marginTop: "26px" }}>
            <h2 style={{ margin: 0 }}>Activitatea prietenilor</h2>

            {!isLoading && !error && friendsActivity.length === 0 ? (
              <div style={{ marginTop: "10px" }}>
                <p style={{ margin: 0 }}>Încă nu există activitate.</p>
                <p style={{ marginTop: "8px", opacity: 0.9 }}>
                  Adaugă prieteni ca să vezi notele și review-urile lor recente.
                </p>
              </div>
            ) : null}

            {!isLoading && !error && friendsActivity.length > 0 ? (
              <div style={{ ...ui.card, marginTop: "12px" }}>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  {friendsActivity.map((it) => (
                    <div key={it.id} style={{ opacity: 0.95 }}>
                      {formatActivity(it)}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </section>

          <section style={{ marginTop: "26px" }}>
            <h2 style={{ margin: 0 }}>Albume populare</h2>

            {!isLoading && !error && popularAlbums.length === 0 ? (
              <p style={{ marginTop: "10px" }}>Nu am găsit albume.</p>
            ) : null}

            {!isLoading && !error && popularAlbums.length > 0 ? (
              <AlbumGrid albums={popularAlbums} />
            ) : null}
          </section>

          <section style={{ marginTop: "26px" }}>
            <h2 style={{ margin: 0 }}>
              Cele mai ascultate albume în ultima săptămână
            </h2>

            {!isLoading && !error && weeklyMostListenedAlbums.length === 0 ? (
              <p style={{ marginTop: "10px" }}>Nu am găsit albume.</p>
            ) : null}

            {!isLoading && !error && weeklyMostListenedAlbums.length > 0 ? (
              <AlbumGrid albums={weeklyMostListenedAlbums} />
            ) : null}
          </section>

          <section style={{ marginTop: "26px" }}>
            <h2 style={{ margin: 0 }}>
              Cele mai populare review-uri ale săptămânii
            </h2>

            {!isLoading && !error && popularReviews.length === 0 ? (
              <p style={{ marginTop: "10px" }}>Nu am găsit review-uri.</p>
            ) : null}

            {!isLoading && !error && popularReviews.length > 0 ? (
              <div style={{ marginTop: "12px", display: "grid", gap: "12px" }}>
                {popularReviews.map((r) => {
                  const title = String(r?.title || "").trim();
                  const content = String(r?.content || "").trim();
                  const username = r?.user_username || "user";
                  const likes = Number.isFinite(Number(r?.likes_count))
                    ? Number(r?.likes_count)
                    : 0;

                  const albumTitle = r?.album_title || "Album";
                  const albumSlug = r?.album_slug;
                  const artistName = r?.artist_name || "Artist";
                  const artistSlug = r?.artist_slug;

                  const snippet =
                    content.length > 260
                      ? `${content.slice(0, 260)}…`
                      : content;

                  return (
                    <div
                      key={r?.id || `${username}-${albumSlug || albumTitle}`}
                      style={ui.card}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: "12px",
                        }}
                      >
                        <div style={{ fontWeight: 700, opacity: 0.95 }}>
                          {username}
                          {albumSlug ? (
                            <>
                              {" "}
                              —{" "}
                              <Link
                                to={`/albums/${albumSlug}`}
                                style={{
                                  textDecoration: "none",
                                  color: "inherit",
                                }}
                              >
                                {albumTitle}
                              </Link>
                            </>
                          ) : (
                            <> — {albumTitle}</>
                          )}
                          {artistSlug ? (
                            <>
                              {" "}
                              ({" "}
                              <Link
                                to={`/artists/${artistSlug}`}
                                style={{
                                  textDecoration: "none",
                                  color: "inherit",
                                }}
                              >
                                {artistName}
                              </Link>{" "}
                              )
                            </>
                          ) : (
                            <> ({artistName})</>
                          )}
                        </div>
                        <div style={{ opacity: 0.9 }}>❤️ {likes}</div>
                      </div>

                      {title ? (
                        <div style={{ marginTop: "10px", fontWeight: 700 }}>
                          {title}
                        </div>
                      ) : null}

                      {snippet ? (
                        <div
                          style={{ marginTop: "8px", whiteSpace: "pre-wrap" }}
                        >
                          {snippet}
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            ) : null}
          </section>

          <section style={{ marginTop: "26px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "12px",
              }}
            >
              <h2 style={{ margin: 0 }}>Top albume 2025</h2>
              <Link
                to="/albums?year=2025&sort=ratings_count"
                style={{
                  ...ui.button,
                  textDecoration: "none",
                  color: "inherit",
                  display: "inline-block",
                }}
              >
                Vezi toate
              </Link>
            </div>

            {!isLoading && !error && topAlbums2025.length === 0 ? (
              <p style={{ marginTop: "10px" }}>Nu am găsit albume.</p>
            ) : null}

            {!isLoading && !error && topAlbums2025.length > 0 ? (
              <AlbumGrid albums={topAlbums2025} />
            ) : null}
          </section>

          <section style={{ marginTop: "26px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "12px",
              }}
            >
              <h2 style={{ margin: 0 }}>Lansări noi</h2>
              <Link
                to="/albums?sort=release_date"
                style={{
                  ...ui.button,
                  textDecoration: "none",
                  color: "inherit",
                  display: "inline-block",
                }}
              >
                Vezi toate
              </Link>
            </div>

            {!isLoading && !error && newReleases.length === 0 ? (
              <p style={{ marginTop: "10px" }}>Nu am găsit albume.</p>
            ) : null}

            {!isLoading && !error && newReleases.length > 0 ? (
              <AlbumGrid albums={newReleases} />
            ) : null}
          </section>

          <section style={{ marginTop: "26px" }}>
            <h2 style={{ margin: 0 }}>Lansări în ultima săptămână</h2>
            {!isLoading && !error && recentAlbums.length === 0 ? (
              <p style={{ marginTop: "10px" }}>Nu am găsit albume.</p>
            ) : null}

            {!isLoading && !error && recentAlbums.length > 0 ? (
              <AlbumGrid albums={recentAlbums} />
            ) : null}
          </section>
        </main>
      </div>

      <div style={{ marginTop: "18px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "12px",
          }}
        >
          <h2 style={{ margin: 0 }}>Oameni cu gusturi similare</h2>
          <Link to="/similar-users">Vezi toți →</Link>
        </div>
        <SimilarUsers limit={6} />
      </div>
    </div>
  );
}
