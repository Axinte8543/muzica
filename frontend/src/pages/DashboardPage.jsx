import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getFriendsActivity } from "../api/activity.js";
import { getMyLists } from "../api/lists.js";
import { getFollowedArtists } from "../api/follows.js";
import { getRecommendations } from "../api/recommendations.js";
import { subscribeLiveFeed } from "../api/live.js";
import ProfileStats from "../components/ProfileStats.jsx";
import SimilarUsers from "../components/SimilarUsers.jsx";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

function formatFriendActivity(item) {
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

function SectionHeader({ title, actionTo, actionLabel }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "12px",
      }}
    >
      <h2 style={{ margin: 0 }}>{title}</h2>
      {actionTo && actionLabel ? (
        <Link
          to={actionTo}
          style={{
            ...ui.button,
            textDecoration: "none",
            color: "inherit",
            display: "inline-block",
          }}
        >
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}

export default function DashboardPage() {
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken } = useAuth();

  const [recommendations, setRecommendations] = useState([]);
  const [friendsActivity, setFriendsActivity] = useState([]);
  const [recentLists, setRecentLists] = useState([]);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const canLoad = useMemo(() => {
    return Boolean(isAuthVerified && accessToken);
  }, [isAuthVerified, accessToken]);

  const followedArtistsQuery = useQuery({
    queryKey: ["followedArtists", baseUrl || "", accessToken || ""],
    enabled: canLoad,
    staleTime: 1000 * 30, // 30s
    placeholderData: (prev) => prev,
    queryFn: async () => {
      const data = await getFollowedArtists({ baseUrl, accessToken });
      const artists = Array.isArray(data) ? data : [];
      return artists.slice(0, 8);
    },
  });

  const followedArtists = Array.isArray(followedArtistsQuery.data)
    ? followedArtistsQuery.data
    : [];

  useEffect(() => {
    let isCancelled = false;

    async function load() {
      if (!canLoad) {
        setRecommendations([]);
        setFriendsActivity([]);
        setRecentLists([]);
        setIsLoading(false);
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      const [recsRes, activityRes, listsRes] = await Promise.allSettled([
        getRecommendations({ baseUrl, accessToken, limit: 8 }),
        getFriendsActivity({ baseUrl, accessToken, limit: 10 }),
        getMyLists({ baseUrl, accessToken }),
      ]);

      if (isCancelled) return;

      if (recsRes.status === "fulfilled") {
        setRecommendations(Array.isArray(recsRes.value) ? recsRes.value : []);
      } else {
        setRecommendations([]);
        setError("Nu am putut încărca recomandările.");
      }

      if (activityRes.status === "fulfilled") {
        setFriendsActivity(
          Array.isArray(activityRes.value) ? activityRes.value : [],
        );
      } else {
        setFriendsActivity([]);
        setError((prev) => prev || "Nu am putut încărca activitatea.");
      }

      if (listsRes.status === "fulfilled") {
        const data = listsRes.value;
        const lists = Array.isArray(data) ? data : [];
        setRecentLists(lists.slice(0, 3));
      } else {
        setRecentLists([]);
        setError((prev) => prev || "Nu am putut încărca listele.");
      }

      if (!isCancelled) setIsLoading(false);
    }

    load();

    return () => {
      isCancelled = true;
    };
  }, [accessToken, baseUrl, canLoad]);

  useEffect(() => {
    if (!canLoad) return undefined;

    return subscribeLiveFeed({
      baseUrl,
      accessToken,
      kind: "activity",
      scope: "friends",
      limit: 10,
      interval: 5,
      onSnapshot: (payload) => {
        setFriendsActivity(Array.isArray(payload) ? payload : []);
      },
    });
  }, [accessToken, baseUrl, canLoad]);

  if (!isAuthenticated) {
    return (
      <div style={ui.container}>
        <h1 style={{ marginTop: 0 }}>Dashboard</h1>
        <p>Trebuie să fii logat ca să îți vezi dashboard-ul.</p>
        <p>
          <Link to="/login">Mergi la Login</Link>
        </p>
      </div>
    );
  }

  if (isAuthenticated && !isAuthVerified) {
    return (
      <div style={ui.container}>
        <h1 style={{ marginTop: 0 }}>Dashboard</h1>
        <p style={{ marginTop: "14px" }}>Se încarcă...</p>
      </div>
    );
  }

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Dashboard</h1>

      {isLoading ? <p style={{ marginTop: "14px" }}>Se încarcă...</p> : null}
      {error ? (
        <p style={{ ...ui.errorText, marginTop: "14px" }} role="alert">
          {error}
        </p>
      ) : null}

      <section style={{ marginTop: "22px" }}>
        <SectionHeader
          title="Recomandările tale"
          actionTo="/recommendations"
          actionLabel="Vezi toate"
        />

        {!isLoading && recommendations.length === 0 ? (
          <div style={{ marginTop: "10px" }}>
            <p style={{ margin: 0 }}>Încă nu ai recomandări.</p>
            <p style={{ marginTop: "8px", opacity: 0.9 }}>
              Notează mai multe albume ca să primești recomandări.
            </p>
          </div>
        ) : null}

        {recommendations.length > 0 ? (
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
        <SectionHeader title="Activitatea prietenilor" />

        <div style={{ ...ui.card, marginTop: "12px" }}>
          {friendsActivity.length ? (
            <div
              style={{ display: "flex", flexDirection: "column", gap: "8px" }}
            >
              {friendsActivity.map((it) => (
                <div key={it.id} style={{ opacity: 0.95 }}>
                  {formatFriendActivity(it)}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ opacity: 0.9 }}>
              Încă nu există activitate. Adaugă prieteni și notează mai multe
              albume.
            </div>
          )}
        </div>
      </section>

      <section style={{ marginTop: "26px" }}>
        <SectionHeader
          title="Utilizatori similari"
          actionTo="/similar-users"
          actionLabel="Vezi tot"
        />
        <SimilarUsers limit={6} />
      </section>

      <section style={{ marginTop: "26px" }}>
        <SectionHeader
          title="Statistici personale"
          actionTo="/profile/stats"
          actionLabel="Detalii"
        />
        <ProfileStats />
      </section>

      <section style={{ marginTop: "26px" }}>
        <SectionHeader
          title="Liste recente"
          actionTo="/lists"
          actionLabel="Vezi toate"
        />

        <div style={{ ...ui.card, marginTop: "12px" }}>
          {recentLists.length ? (
            <ul style={{ margin: 0, paddingLeft: "18px" }}>
              {recentLists.map((l) => (
                <li key={l.id} style={{ marginBottom: "8px" }}>
                  <span style={{ fontWeight: 700 }}>{l.name}</span>
                  <span style={{ opacity: 0.9 }}> ({l.albums_count ?? 0})</span>
                </li>
              ))}
            </ul>
          ) : (
            <div style={{ opacity: 0.9 }}>
              Nu ai încă nicio listă. Creează una în pagina de Liste.
            </div>
          )}
        </div>
      </section>

      <section style={{ marginTop: "26px" }}>
        <SectionHeader
          title="Artiști urmăriți"
          actionTo="/following"
          actionLabel="Vezi toți"
        />

        <div style={{ ...ui.card, marginTop: "12px" }}>
          {followedArtists.length ? (
            <ul style={{ margin: 0, paddingLeft: "18px" }}>
              {followedArtists.map((a) => (
                <li key={a.id} style={{ marginBottom: "8px" }}>
                  <Link to={`/artists/${a.artist_slug}`}>{a.artist_name}</Link>
                </li>
              ))}
            </ul>
          ) : (
            <div style={{ opacity: 0.9 }}>Nu urmărești încă niciun artist.</div>
          )}
        </div>
      </section>
    </div>
  );
}
