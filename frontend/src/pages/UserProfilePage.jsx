import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { getCompatibility } from "../api/compatibility.js";
import { getPublicUserProfile } from "../api/publicProfile.js";
import {
  acceptFriendRequest,
  getFriendsList,
  rejectFriendRequest,
  sendFriendRequest,
} from "../api/friends.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

function formatDateTime(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString();
}

function formatActivity(item) {
  const actor = item?.actor_username || "User";
  const name = item?.target_name || "";

  switch (item?.activity_type) {
    case "rate_album": {
      const rating = Number(item?.rating);
      const stars = Number.isFinite(rating) ? ` ⭐${rating}` : "";
      return `${actor} rated ${name}${stars}`.trim();
    }
    case "review_album":
      return `${actor} a scris un review la ${name}`.trim();
    case "follow_artist":
      return `${actor} followed ${name}`.trim();
    case "create_list":
      return `${actor} created a list ${name}`.trim();
    default:
      return `${actor} did something`.trim();
  }
}

function similarityToPercent(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return null;
  const pct = num <= 1 ? num * 100 : num;
  return Math.max(0, Math.min(100, Math.round(pct)));
}

export default function UserProfilePage() {
  const { username } = useParams();

  const {
    baseUrl,
    isAuthenticated,
    isAuthVerified,
    accessToken,
    logout,
    user,
    isLoadingUser,
  } = useAuth();
  const [searchParams] = useSearchParams();
  const userId = searchParams.get("id");

  const [compat, setCompat] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const [publicProfile, setPublicProfile] = useState(null);
  const [isLoadingPublic, setIsLoadingPublic] = useState(false);
  const [publicError, setPublicError] = useState(null);

  const [friendsData, setFriendsData] = useState(null);
  const [isLoadingFriends, setIsLoadingFriends] = useState(false);
  const [friendsError, setFriendsError] = useState(null);
  const [isSubmittingFriendAction, setIsSubmittingFriendAction] =
    useState(false);

  const canLoad = useMemo(() => {
    return Boolean(isAuthVerified && accessToken && userId);
  }, [isAuthVerified, accessToken, userId]);

  useEffect(() => {
    let isCancelled = false;

    async function load() {
      if (!canLoad) {
        setCompat(null);
        setIsLoading(false);
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const data = await getCompatibility({
          baseUrl,
          accessToken,
          userId,
        });
        if (!isCancelled) setCompat(data);
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled) setError("Nu am putut încărca compatibilitatea.");
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      isCancelled = true;
    };
  }, [canLoad, baseUrl, accessToken, userId, logout]);

  useEffect(() => {
    let isCancelled = false;

    async function loadPublic() {
      const u = String(username || "").trim();
      if (!u) {
        if (!isCancelled) {
          setPublicProfile(null);
          setIsLoadingPublic(false);
          setPublicError(null);
        }
        return;
      }

      if (!isCancelled) {
        setIsLoadingPublic(true);
        setPublicError(null);
      }

      try {
        const data = await getPublicUserProfile({
          baseUrl,
          username: u,
          reviewsLimit: 5,
          ratingsLimit: 5,
          activityLimit: 5,
        });
        if (!isCancelled) setPublicProfile(data);
      } catch (err) {
        console.error(err);
        if (!isCancelled)
          setPublicError("Nu am putut încărca profilul public.");
      } finally {
        if (!isCancelled) setIsLoadingPublic(false);
      }
    }

    loadPublic();
    return () => {
      isCancelled = true;
    };
  }, [baseUrl, username]);

  useEffect(() => {
    let isCancelled = false;

    async function loadFriends() {
      if (!isAuthVerified || !accessToken) {
        if (!isCancelled) {
          setFriendsData(null);
          setIsLoadingFriends(false);
          setFriendsError(null);
        }
        return;
      }

      if (!isCancelled) {
        setIsLoadingFriends(true);
        setFriendsError(null);
      }

      try {
        const data = await getFriendsList({ baseUrl, accessToken });
        if (!isCancelled) setFriendsData(data);
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled)
          setFriendsError("Nu am putut încărca statusul de prietenie.");
      } finally {
        if (!isCancelled) setIsLoadingFriends(false);
      }
    }

    loadFriends();
    return () => {
      isCancelled = true;
    };
  }, [baseUrl, isAuthVerified, accessToken, logout, username]);

  const pct = similarityToPercent(compat?.similarity);
  const pctLabel = pct === null ? "—" : `Similaritate: ${pct}%`;

  const commonGenres = Array.isArray(compat?.common_genres)
    ? compat.common_genres
    : [];
  const commonArtists = Array.isArray(compat?.common_artists)
    ? compat.common_artists
    : [];
  const commonAlbums = Array.isArray(compat?.common_albums)
    ? compat.common_albums
    : [];

  const stats = publicProfile?.stats;
  const recentReviews = Array.isArray(publicProfile?.recent_reviews)
    ? publicProfile.recent_reviews
    : [];
  const recentRatings = Array.isArray(publicProfile?.recent_album_ratings)
    ? publicProfile.recent_album_ratings
    : [];
  const recentActivity = Array.isArray(publicProfile?.recent_activity)
    ? publicProfile.recent_activity.slice(0, 5)
    : [];

  const normalizedUsername = String(username || "")
    .trim()
    .toLowerCase();
  const normalizedMe = String(user?.username || "")
    .trim()
    .toLowerCase();
  const isOwnProfile = Boolean(
    normalizedUsername && normalizedUsername === normalizedMe,
  );

  const friendsList = Array.isArray(friendsData?.friends?.results)
    ? friendsData.friends.results
    : [];
  const incoming = Array.isArray(friendsData?.incoming)
    ? friendsData.incoming
    : [];
  const outgoing = Array.isArray(friendsData?.outgoing)
    ? friendsData.outgoing
    : [];

  const isFriends = friendsList.some(
    (u) =>
      String(u?.username || "")
        .trim()
        .toLowerCase() === normalizedUsername,
  );
  const incomingFromThisUser = incoming.find(
    (fr) =>
      String(fr?.sender_username || "")
        .trim()
        .toLowerCase() === normalizedUsername,
  );
  const outgoingToThisUser = outgoing.find(
    (fr) =>
      String(fr?.receiver_username || "")
        .trim()
        .toLowerCase() === normalizedUsername,
  );

  const averageRatingValue = Number(stats?.average_rating_given);
  const averageRatingLabel = Number.isFinite(averageRatingValue)
    ? averageRatingValue.toFixed(1)
    : "—";

  const heroMetrics = [
    { label: "Ratinguri", value: stats?.activity?.albums_rated ?? 0 },
    { label: "Review-uri", value: stats?.activity?.reviews_written ?? 0 },
    {
      label: "Artiști urmăriți",
      value: stats?.activity?.artists_followed ?? 0,
    },
    { label: "Liste", value: stats?.activity?.lists_created ?? 0 },
  ];

  const profileHighlights = [
    { label: "Artist preferat", value: stats?.favorite_artist || "—" },
    { label: "Rating mediu", value: averageRatingLabel },
  ];

  const relationshipBadge = isFriends
    ? "Prieteni"
    : incomingFromThisUser
      ? "Cerere primită"
      : outgoingToThisUser
        ? "Cerere trimisă"
        : "Poți conecta";

  const relationshipDescription = isFriends
    ? "Sunteți conectați deja."
    : incomingFromThisUser
      ? "Acest utilizator ți-a trimis o cerere de prietenie."
      : outgoingToThisUser
        ? "Cererea ta este încă în așteptare."
        : "Trimite o cerere dacă vrei să urmărești mai ușor activitatea lui.";

  const showCompatPanel = Boolean(isAuthenticated && userId && !isOwnProfile);
  const showFriendPanel = Boolean(
    isAuthenticated && !isLoadingUser && user && !isOwnProfile,
  );

  const pageStyle = {
    padding: "24px",
    maxWidth: "1280px",
    margin: "0 auto",
  };

  const heroCardStyle = {
    ...ui.card,
    padding: "24px",
    display: "grid",
    gap: "18px",
    alignItems: "start",
  };

  const contentGridStyle = {
    display: "grid",
    gap: "14px",
    marginTop: "14px",
  };

  const summaryGridStyle = {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
    gap: "12px",
    marginTop: "16px",
  };

  const summaryTileStyle = {
    padding: "14px 16px",
    borderRadius: "16px",
    border: `1px solid ${ui.colors.border}`,
    background: "rgba(255, 255, 255, 0.03)",
  };

  const badgeStyle = {
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    padding: "6px 12px",
    borderRadius: "999px",
    border: `1px solid ${ui.colors.border}`,
    background: "rgba(255, 255, 255, 0.04)",
    fontSize: "0.8rem",
    fontWeight: 700,
    letterSpacing: "0.02em",
    textTransform: "uppercase",
  };

  const highlightRowStyle = {
    display: "flex",
    flexWrap: "wrap",
    gap: "10px",
    marginTop: "16px",
  };

  const highlightPillStyle = {
    display: "inline-flex",
    alignItems: "center",
    gap: "8px",
    padding: "10px 12px",
    borderRadius: "999px",
    border: `1px solid ${ui.colors.border}`,
    background: "rgba(255, 255, 255, 0.03)",
  };

  const panelCardStyle = {
    padding: "18px",
    borderRadius: "18px",
    border: `1px solid ${ui.colors.border}`,
    background: "rgba(255, 255, 255, 0.02)",
  };

  const sectionTitleStyle = {
    fontWeight: 800,
    fontSize: "1rem",
    marginBottom: "10px",
  };

  const subtleTextStyle = {
    opacity: 0.88,
    lineHeight: 1.55,
  };

  const progressTrackStyle = {
    height: "10px",
    borderRadius: "999px",
    background: "rgba(148, 163, 184, 0.14)",
    overflow: "hidden",
    marginTop: "10px",
  };

  const progressBarStyle = {
    height: "100%",
    borderRadius: "999px",
    background:
      "linear-gradient(90deg, rgba(245, 158, 11, 0.9), rgba(251, 191, 36, 0.95))",
  };

  const actionRowStyle = {
    display: "flex",
    flexWrap: "wrap",
    gap: "10px",
    marginTop: "12px",
  };

  const primaryActionButtonStyle = {
    ...ui.button,
    background:
      "linear-gradient(180deg, rgba(245, 158, 11, 0.2), rgba(245, 158, 11, 0.12))",
    borderColor: "rgba(245, 158, 11, 0.35)",
    fontWeight: 700,
  };

  const secondaryActionButtonStyle = {
    ...ui.buttonSmall,
    backgroundColor: "transparent",
    fontWeight: 700,
  };

  async function refreshFriends() {
    try {
      const data = await getFriendsList({ baseUrl, accessToken });
      setFriendsData(data);
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      throw err;
    }
  }

  async function handleAddFriend() {
    if (!isAuthVerified || !accessToken || !username) return;
    setIsSubmittingFriendAction(true);
    setFriendsError(null);
    try {
      await sendFriendRequest({
        baseUrl,
        accessToken,
        receiverUsername: username,
      });
      await refreshFriends();
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setFriendsError("Nu am putut trimite cererea de prietenie.");
    } finally {
      setIsSubmittingFriendAction(false);
    }
  }

  async function handleAccept(requestId) {
    if (!isAuthVerified || !accessToken || !requestId) return;
    setIsSubmittingFriendAction(true);
    setFriendsError(null);
    try {
      await acceptFriendRequest({ baseUrl, accessToken, requestId });
      await refreshFriends();
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setFriendsError("Nu am putut accepta cererea.");
    } finally {
      setIsSubmittingFriendAction(false);
    }
  }

  async function handleReject(requestId) {
    if (!isAuthVerified || !accessToken || !requestId) return;
    setIsSubmittingFriendAction(true);
    setFriendsError(null);
    try {
      await rejectFriendRequest({ baseUrl, accessToken, requestId });
      await refreshFriends();
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setFriendsError("Nu am putut respinge cererea.");
    } finally {
      setIsSubmittingFriendAction(false);
    }
  }

  return (
    <div style={pageStyle}>
      {isAuthenticated && !isAuthVerified ? (
        <p style={{ marginTop: 0 }}>Se încarcă...</p>
      ) : null}

      <p style={{ marginTop: 0 }}>
        <Link to="/similar-users">← Înapoi la utilizatori similari</Link>
      </p>

      <div className="profile-hero" style={heroCardStyle}>
        <div>
          <div style={badgeStyle}>Profil public</div>
          <h1
            style={{
              margin: "12px 0 8px",
              fontSize: "clamp(2.4rem, 4vw, 3.6rem)",
              lineHeight: 1.02,
            }}
          >
            {username || "user"}
          </h1>
          <p style={{ ...subtleTextStyle, maxWidth: "60ch" }}>
            Un rezumat rapid al gusturilor, activității și compatibilității.
          </p>

          <div style={summaryGridStyle}>
            {heroMetrics.map((metric) => (
              <div key={metric.label} style={summaryTileStyle}>
                <div style={{ opacity: 0.78, fontSize: "0.85rem" }}>
                  {metric.label}
                </div>
                <div
                  style={{
                    marginTop: "6px",
                    fontSize: "1.7rem",
                    fontWeight: 800,
                  }}
                >
                  {metric.value}
                </div>
              </div>
            ))}
          </div>

          <div style={highlightRowStyle}>
            {profileHighlights.map((item) => (
              <div key={item.label} style={highlightPillStyle}>
                <span style={{ opacity: 0.72 }}>{item.label}</span>
                <span style={{ fontWeight: 800 }}>{item.value}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={panelCardStyle}>
          <div style={sectionTitleStyle}>Relație</div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 10,
            }}
          >
            <div style={{ fontWeight: 800 }}>{relationshipBadge}</div>
            <div style={{ ...badgeStyle, textTransform: "none" }}>
              {isOwnProfile ? "Este profilul tău" : "Profil public"}
            </div>
          </div>
          <p style={{ ...subtleTextStyle, marginTop: 10, marginBottom: 0 }}>
            {relationshipDescription}
          </p>

          {showFriendPanel ? (
            <div style={{ marginTop: 14 }}>
              {isLoadingFriends ? (
                <p style={{ margin: 0 }}>Se încarcă...</p>
              ) : null}

              {!isLoadingFriends && friendsError ? (
                <p style={{ ...ui.errorText, margin: 0 }} role="alert">
                  {friendsError}
                </p>
              ) : null}

              {!isLoadingFriends && !friendsError && isFriends ? (
                <p style={{ margin: 0, opacity: 0.9 }}>
                  Sunteți deja conectați.
                </p>
              ) : null}

              {!isLoadingFriends &&
              !friendsError &&
              !isFriends &&
              outgoingToThisUser ? (
                <p style={{ margin: 0, opacity: 0.9 }}>
                  Cererea ta a fost trimisă.
                </p>
              ) : null}

              {!isLoadingFriends &&
              !friendsError &&
              !isFriends &&
              incomingFromThisUser ? (
                <div>
                  <p style={{ margin: 0, opacity: 0.9 }}>
                    Ai primit o cerere de prietenie.
                  </p>
                  <div style={actionRowStyle}>
                    <button
                      type="button"
                      onClick={() => handleAccept(incomingFromThisUser.id)}
                      disabled={isSubmittingFriendAction}
                      style={primaryActionButtonStyle}
                    >
                      Acceptă
                    </button>
                    <button
                      type="button"
                      onClick={() => handleReject(incomingFromThisUser.id)}
                      disabled={isSubmittingFriendAction}
                      style={secondaryActionButtonStyle}
                    >
                      Respinge
                    </button>
                  </div>
                </div>
              ) : null}

              {!isLoadingFriends &&
              !friendsError &&
              !isFriends &&
              !outgoingToThisUser &&
              !incomingFromThisUser ? (
                <button
                  type="button"
                  onClick={handleAddFriend}
                  disabled={isSubmittingFriendAction}
                  style={{ ...primaryActionButtonStyle, marginTop: 12 }}
                >
                  Adaugă prieten
                </button>
              ) : null}
            </div>
          ) : (
            <p style={{ ...subtleTextStyle, marginTop: 12, marginBottom: 0 }}>
              {isOwnProfile
                ? "Acesta este profilul tău public."
                : "Autentifică-te pentru acțiuni de prietenie."}
            </p>
          )}
        </div>
      </div>

      <div className="profile-content-grid" style={contentGridStyle}>
        <div style={{ ...ui.card, padding: "20px" }}>
          <div style={sectionTitleStyle}>Activitate recentă</div>

          {isLoadingPublic ? (
            <p style={{ marginTop: 12 }}>Se încarcă...</p>
          ) : null}

          {!isLoadingPublic && publicError ? (
            <p style={{ ...ui.errorText, marginTop: 12 }} role="alert">
              {publicError}
            </p>
          ) : null}

          {!isLoadingPublic && !publicError && publicProfile ? (
            <>
              {recentRatings.length > 0 ? (
                <div style={{ marginTop: 14 }}>
                  <div style={{ fontWeight: 700 }}>Ratinguri recente</div>
                  <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
                    {recentRatings.map((r) => (
                      <div key={r.id} style={{ opacity: 0.96 }}>
                        <Link
                          to={`/albums/${r.album_slug}`}
                          style={{ color: "inherit" }}
                        >
                          {r.album_title}
                        </Link>{" "}
                        — {r.artist_name} — ⭐{r.rating}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {recentReviews.length > 0 ? (
                <div style={{ marginTop: 14 }}>
                  <div style={{ fontWeight: 700 }}>Review-uri recente</div>
                  <div style={{ marginTop: 10, display: "grid", gap: 12 }}>
                    {recentReviews.map((rv) => (
                      <div key={rv.id} style={{ opacity: 0.96 }}>
                        <div style={{ fontWeight: 700 }}>
                          <Link
                            to={`/albums/${rv.album_slug}`}
                            style={{ color: "inherit" }}
                          >
                            {rv.album_title}
                          </Link>{" "}
                          — {rv.artist_name}
                        </div>
                        {rv.title ? (
                          <div style={{ marginTop: 4 }}>{rv.title}</div>
                        ) : null}
                        <div style={{ marginTop: 4, opacity: 0.82 }}>
                          {formatDateTime(rv.created_at)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {recentActivity.length > 0 ? (
                <div style={{ marginTop: 14 }}>
                  <div style={{ fontWeight: 700 }}>Recent activity</div>
                  <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
                    {recentActivity.map((it) => (
                      <div key={it.id} style={{ opacity: 0.96 }}>
                        {formatActivity(it)}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </>
          ) : null}
        </div>

        <div style={{ display: "grid", gap: 14 }}>
          {showCompatPanel ? (
            <div style={{ ...ui.card, padding: "20px" }}>
              <div style={sectionTitleStyle}>Compatibilitate</div>
              <div style={{ marginTop: 6, opacity: 0.95 }}>{pctLabel}</div>

              <div style={{ marginTop: 12 }}>
                <div style={{ opacity: 0.75 }}>Scor de potrivire</div>
                <div style={progressTrackStyle}>
                  <div style={{ ...progressBarStyle, width: `${pct ?? 0}%` }} />
                </div>
              </div>

              {commonGenres.length ? (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontWeight: 700 }}>Genuri comune</div>
                  <div style={{ opacity: 0.9 }}>{commonGenres.join(", ")}</div>
                </div>
              ) : null}

              {commonArtists.length ? (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontWeight: 700 }}>Artiști comuni</div>
                  <div style={{ opacity: 0.9 }}>{commonArtists.join(", ")}</div>
                </div>
              ) : null}

              {commonAlbums.length ? (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontWeight: 700 }}>Albume comune</div>
                  <div style={{ opacity: 0.9 }}>{commonAlbums.join(", ")}</div>
                </div>
              ) : null}
            </div>
          ) : null}

          {isAuthenticated && !isLoadingUser && user && !isOwnProfile ? (
            <div style={{ ...ui.card, padding: "20px" }}>
              <div style={sectionTitleStyle}>Prieteni</div>
              <p style={{ marginTop: 0, opacity: 0.88 }}>
                {isFriends
                  ? "Sunteți conectați deja."
                  : outgoingToThisUser
                    ? "Cererea ta de prietenie este în așteptare."
                    : incomingFromThisUser
                      ? "Poți răspunde cererii primite aici."
                      : "Trimite o cerere de prietenie pentru a urmări mai ușor activitatea."}
              </p>
              {!isFriends && !outgoingToThisUser && !incomingFromThisUser ? (
                <button
                  type="button"
                  onClick={handleAddFriend}
                  disabled={isSubmittingFriendAction}
                  style={primaryActionButtonStyle}
                >
                  Adaugă prieten
                </button>
              ) : null}
            </div>
          ) : null}

          {!isAuthenticated ? (
            <div style={{ ...ui.card, padding: "20px" }}>
              <div style={sectionTitleStyle}>Conectează-te</div>
              <p style={{ marginTop: 0, opacity: 0.9 }}>
                Trebuie să fii logat ca să vezi compatibilitatea.
              </p>
              <p style={{ marginBottom: 0 }}>
                <Link to="/login">Mergi la Login</Link>
              </p>
            </div>
          ) : null}

          {isAuthenticated && !userId ? (
            <div style={{ ...ui.card, padding: "20px" }}>
              Compatibilitatea nu este disponibilă (lipsește id-ul
              utilizatorului).
            </div>
          ) : null}

          {isAuthenticated && userId && isLoading ? (
            <div style={{ ...ui.card, padding: "20px" }}>Se încarcă...</div>
          ) : null}

          {isAuthenticated && userId && error ? (
            <div style={{ ...ui.card, padding: "20px" }} role="alert">
              <p style={{ ...ui.errorText, margin: 0 }}>{error}</p>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
