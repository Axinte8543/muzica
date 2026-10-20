import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import ProfileNav from "../components/ProfileNav.jsx";
import { useAuth } from "../context/useAuth.js";
import { getMyProfileStats } from "../api/profileStats.js";
import { getMyReviews } from "../api/reviews.js";
import { getMyRatings } from "../api/ratings.js";
import { getMyXP } from "../api/gamification.js";
import { ui } from "../ui/ui.js";

function Avatar({ username, size = 92 }) {
  const initial = String(username || "?")
    .trim()
    .charAt(0)
    .toUpperCase();
  const style = {
    width: size,
    height: size,
    borderRadius: "50%",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: Math.round(size * 0.42),
    fontWeight: 800,
    color: "white",
    background: "linear-gradient(135deg,#111827,#1f2937)",
    border: `2px solid ${ui.colors.border}`,
  };
  return <div style={style}>{initial}</div>;
}

function formatRelativeDate(value) {
  if (!value) return "";
  const date = new Date(value);
  const time = date.getTime();
  if (!Number.isFinite(time)) return "";

  const diffSeconds = Math.max(0, Math.floor((Date.now() - time) / 1000));
  if (diffSeconds < 60) return "acum";
  const minutes = Math.floor(diffSeconds / 60);
  if (minutes < 60) return `acum ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `acum ${hours} h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `acum ${days} zile`;

  return date.toLocaleDateString("ro-RO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function albumCoverFrom(item) {
  return (
    item?.album_cover_url ||
    item?.cover_url ||
    item?.album?.cover_url ||
    item?.cover ||
    ""
  );
}

function AlbumMiniCard({ item, type }) {
  const title = item?.album_title || item?.title || "Album";
  const slug = item?.album_slug || item?.slug || "";
  const artist = item?.artist_name || item?.album_artist || item?.artist || "";
  const coverUrl = albumCoverFrom(item);
  const createdAt = item?.created_at || item?.updated_at || item?.rated_at;
  const rating = Number(item?.rating);
  const target = slug
    ? `/albums/${encodeURIComponent(slug)}${type === "review" ? "?tab=reviews" : ""}`
    : "";

  return (
    <div
      style={{
        border: `1px solid ${ui.colors.border}`,
        borderRadius: "8px",
        padding: "10px",
        display: "grid",
        gridTemplateColumns: "54px minmax(0, 1fr)",
        gap: "10px",
        alignItems: "center",
        background: "rgba(15, 23, 42, 0.28)",
      }}
    >
      <div
        style={{
          width: "54px",
          height: "54px",
          borderRadius: "6px",
          overflow: "hidden",
          border: `1px solid ${ui.colors.border}`,
          background: ui.colors.mutedBg,
        }}
      >
        {coverUrl ? (
          <img
            src={coverUrl}
            alt={`Coperta albumului ${title}`}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : null}
      </div>

      <div style={{ minWidth: 0 }}>
        <div style={{ fontWeight: 800, overflowWrap: "anywhere" }}>
          {target ? <Link to={target}>{title}</Link> : title}
        </div>
        {artist ? (
          <div style={{ opacity: 0.82, marginTop: "2px" }}>{artist}</div>
        ) : null}
        <div
          style={{
            display: "flex",
            gap: "8px",
            alignItems: "center",
            flexWrap: "wrap",
            marginTop: "6px",
            fontSize: "0.92em",
          }}
        >
          <span
            style={{
              border: `1px solid ${ui.colors.border}`,
              borderRadius: "999px",
              padding: "1px 8px",
              color: "var(--link-color)",
              fontWeight: 700,
            }}
          >
            {type === "review"
              ? "Review"
              : Number.isFinite(rating)
                ? `${rating}/5`
                : "Rating"}
          </span>
          {createdAt ? (
            <time dateTime={createdAt} style={{ opacity: 0.75 }}>
              {formatRelativeDate(createdAt)}
            </time>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default function MyProfilePage() {
  const {
    user,
    isAuthenticated,
    isAuthVerified,
    baseUrl,
    accessToken,
    logout,
  } = useAuth();

  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [recentReviews, setRecentReviews] = useState([]);
  const [recentRatings, setRecentRatings] = useState([]);
  const [userXP, setUserXP] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!isAuthenticated || !isAuthVerified) return;
      setIsLoading(true);
      setError(null);
      try {
        const [data, reviewsRes, ratingsRes, xpRes] = await Promise.all([
          getMyProfileStats({ baseUrl, accessToken }),
          getMyReviews({ baseUrl, accessToken }),
          getMyRatings({ baseUrl, accessToken, albumPage: 1, songPage: 1 }),
          getMyXP(),
        ]);

        if (!cancelled) {
          setStats(data);
          setUserXP(xpRes);

          // Normalize recent reviews (expect array)
          try {
            const revs = Array.isArray(reviewsRes)
              ? reviewsRes
              : (reviewsRes?.results ?? []);
            setRecentReviews(revs.slice(0, 5));
          } catch {
            setRecentReviews([]);
          }

          // Normalize recent ratings (backend may return {albums: {results: []}, songs: {results: []}} or a flat array)
          try {
            let albumsList = [];
            if (Array.isArray(ratingsRes)) {
              albumsList = ratingsRes;
            } else if (ratingsRes && Array.isArray(ratingsRes.albums)) {
              albumsList = ratingsRes.albums;
            } else if (
              ratingsRes &&
              ratingsRes.albums &&
              Array.isArray(ratingsRes.albums.results)
            ) {
              albumsList = ratingsRes.albums.results;
            }
            setRecentRatings((albumsList || []).slice(0, 5));
          } catch {
            setRecentRatings([]);
          }
        }
      } catch (err) {
        console.error(err);
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        if (!cancelled) setError("Nu am putut încărca statisticile.");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, isAuthVerified, baseUrl, accessToken, logout]);

  const username = user?.username || "user";

  const heroMetrics = useMemo(() => {
    const s = stats?.activity || {};
    return [
      { label: "Ratings", value: s.albums_rated ?? 0, to: "/profile/ratings" },
      {
        label: "Reviews",
        value: s.reviews_written ?? 0,
        to: "/profile/reviews",
      },
    ];
  }, [stats]);

  if (!isAuthenticated) {
    return (
      <div>
        <ProfileNav />
        <div style={{ padding: "24px" }}>
          <h1 style={{ marginTop: 0 }}>Profilul meu</h1>
          <p>Trebuie să fii logat ca să vezi pagina ta de profil.</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <ProfileNav />

      <div style={{ padding: "24px", maxWidth: 1200, margin: "0 auto" }}>
        <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
          <Avatar username={username} size={110} />
          <div>
            <h1 style={{ margin: 0, fontSize: "2.2rem" }}>{username}</h1>
            <div style={{ marginTop: 8, opacity: 0.85 }}>
              <Link to="/profile/stats">Vezi statistici</Link>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 20, display: "grid", gap: 14 }}>
          <div style={{ ...ui.card, padding: 20 }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: 12,
              }}
            >
              {heroMetrics.map((m) => (
                <Link
                  key={m.label}
                  to={m.to}
                  style={{ textDecoration: "none", color: "inherit" }}
                >
                  <div style={{ textAlign: "center", cursor: "pointer" }}>
                    <div style={{ opacity: 0.8 }}>{m.label}</div>
                    <div
                      style={{
                        fontWeight: 800,
                        fontSize: "1.6rem",
                        marginTop: 6,
                      }}
                    >
                      {m.value}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: 14,
            }}
          >
            <div style={{ ...ui.card, padding: 20 }}>
              <h2 style={{ marginTop: 0 }}>Activitate recentă</h2>
              {isLoading ? <p>Se încarcă...</p> : null}
              {error ? <p style={ui.errorText}>{error}</p> : null}
              {!isLoading && !error && stats ? (
                <div style={{ display: "grid", gap: "16px" }}>
                  <section>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "10px",
                        marginBottom: "10px",
                      }}
                    >
                      <strong>Albume evaluate</strong>
                      <Link to="/profile/ratings">
                        {stats.activity?.albums_rated ?? 0} total
                      </Link>
                    </div>
                    {recentRatings && recentRatings.length > 0 ? (
                      <div style={{ display: "grid", gap: "8px" }}>
                        {recentRatings.map((r, idx) => (
                          <AlbumMiniCard
                            key={r.id || idx}
                            item={r}
                            type="rating"
                          />
                        ))}
                      </div>
                    ) : (
                      <div style={{ opacity: 0.82 }}>
                        Încă nu ai ratinguri recente.
                      </div>
                    )}
                  </section>

                  <section>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "10px",
                        marginBottom: "10px",
                      }}
                    >
                      <strong>Recenzii scrise</strong>
                      <Link to="/profile/reviews">
                        {stats.activity?.reviews_written ?? 0} total
                      </Link>
                    </div>
                    {recentReviews && recentReviews.length > 0 ? (
                      <div style={{ display: "grid", gap: "8px" }}>
                        {recentReviews.map((rev, idx) => (
                          <AlbumMiniCard
                            key={rev.id || idx}
                            item={rev}
                            type="review"
                          />
                        ))}
                      </div>
                    ) : (
                      <div style={{ opacity: 0.82 }}>
                        Încă nu ai review-uri recente.
                      </div>
                    )}
                  </section>
                </div>
              ) : null}
            </div>

            <div style={{ display: "grid", gap: 12 }}>
              <div style={{ ...ui.card, padding: 16 }}>
                <div style={{ fontWeight: 700 }}>Quick Links</div>
                <ul style={{ marginTop: 8 }}>
                  <li>
                    <Link to="/profile/listens">Listens</Link>
                  </li>
                  <li>
                    <Link to="/profile/ratings">Ratings</Link>
                  </li>
                  <li>
                    <Link to="/profile/want-to-listen">Want to listen</Link>
                  </li>
                </ul>
              </div>

              <div style={{ ...ui.card, padding: 16 }}>
                <div style={{ fontWeight: 700 }}>Setări</div>
                <div style={{ marginTop: 8 }}>
                  <Link to="/profile/privacy">Confidențialitate</Link>
                </div>
              </div>
            </div>
          </div>

          <div
            style={{
              ...ui.card,
              padding: "18px 20px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "16px",
              flexWrap: "wrap",
            }}
          >
            <div>
              <div style={{ fontWeight: 800 }}>Experiență acumulată</div>
              <div style={{ marginTop: "4px", opacity: 0.75 }}>
                XP obținut din realizări și provocări
              </div>
            </div>
            <div
              aria-label={`${userXP?.total_xp ?? 0} puncte de experiență`}
              style={{
                fontSize: "1.6rem",
                fontWeight: 900,
                color: "#f59e0b",
                whiteSpace: "nowrap",
              }}
            >
              {isLoading ? "…" : `${userXP?.total_xp ?? 0} XP`}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
