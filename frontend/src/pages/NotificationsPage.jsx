import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  acceptFriendRequest,
  getFriendsList,
  rejectFriendRequest,
} from "../api/friends.js";
import { buildLiveFeedUrl } from "../api/live.js";
import {
  getNotificationPreferences,
  getNotifications,
  updateNotificationPreferences,
} from "../api/notifications.js";
import { useAuth } from "../context/useAuth.js";
import { useNotice } from "../context/useNotice.js";
import { ui } from "../ui/ui.js";

function relativeTime(value) {
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

function notificationMeta(type) {
  switch (type) {
    case "friend":
      return { label: "Prietenie", icon: "+", color: "rgba(34, 197, 94, 0.18)" };
    case "like":
      return { label: "Like review", icon: "♥", color: "rgba(236, 72, 153, 0.16)" };
    case "reply":
      return { label: "Răspuns review", icon: "R", color: "rgba(59, 130, 246, 0.16)" };
    default:
      return { label: "Notificare", icon: "•", color: "rgba(148, 163, 184, 0.14)" };
  }
}

export default function NotificationsPage() {
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken } = useAuth();
  const { notify } = useNotice();

  const [incoming, setIncoming] = useState([]);
  const [reviewLikes, setReviewLikes] = useState([]);
  const [reviewReplies, setReviewReplies] = useState([]);
  const [prefs, setPrefs] = useState(null);
  const [isSavingPrefs, setIsSavingPrefs] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);

  const canLoad = useMemo(() => {
    return Boolean(isAuthVerified && accessToken);
  }, [isAuthVerified, accessToken]);

  const notificationItems = useMemo(() => {
    const friendItems = incoming
      .map((fr) => {
        const sender = String(fr?.sender_username || "").trim();
        if (!fr?.id || !sender) return null;
        return {
          id: `friend-${fr.id}`,
          type: "friend",
          createdAt: fr.created_at,
          user: sender,
          text: "vrea să fie prieten cu tine",
          requestId: fr.id,
        };
      })
      .filter(Boolean);

    const likeItems = reviewLikes
      .map((lk) => {
        const liker = String(lk?.liker_username || "").trim();
        if (!lk?.id || !liker) return null;
        return {
          id: `like-${lk.id}`,
          type: "like",
          createdAt: lk.created_at,
          user: liker,
          text: "a apreciat review-ul tău la",
          albumSlug: String(lk?.album_slug || "").trim(),
          albumTitle: String(lk?.album_title || "Album"),
        };
      })
      .filter(Boolean);

    const replyItems = reviewReplies
      .map((rp) => {
        const replier = String(rp?.replier_username || "").trim();
        if (!rp?.id || !replier) return null;
        return {
          id: `reply-${rp.id}`,
          type: "reply",
          createdAt: rp.created_at,
          user: replier,
          text: "a răspuns la review-ul tău la",
          albumSlug: String(rp?.album_slug || "").trim(),
          albumTitle: String(rp?.album_title || "Album"),
        };
      })
      .filter(Boolean);

    return [...friendItems, ...likeItems, ...replyItems].sort((a, b) => {
      const aTime = new Date(a.createdAt || 0).getTime() || 0;
      const bTime = new Date(b.createdAt || 0).getTime() || 0;
      return bTime - aTime;
    });
  }, [incoming, reviewLikes, reviewReplies]);

  const applyNotificationsPayload = useCallback((data) => {
    setIncoming(
      Array.isArray(data?.incoming_friend_requests)
        ? data.incoming_friend_requests
        : [],
    );
    setReviewLikes(Array.isArray(data?.review_likes) ? data.review_likes : []);
    setReviewReplies(
      Array.isArray(data?.review_replies) ? data.review_replies : [],
    );
  }, []);

  const load = useCallback(async () => {
    if (!canLoad) {
      setIncoming([]);
      setReviewLikes([]);
      setReviewReplies([]);
      setPrefs(null);
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const nextPrefs = await getNotificationPreferences({
        baseUrl,
        accessToken,
      });
      setPrefs(nextPrefs || null);

      const data = await getNotifications({ baseUrl, accessToken, limit: 10 });
      applyNotificationsPayload(data);
    } catch (err) {
      console.error(err);
      setError("Nu am putut încărca notificările.");
      setIncoming([]);
      setReviewLikes([]);
      setReviewReplies([]);
    } finally {
      setIsLoading(false);
    }
  }, [baseUrl, accessToken, canLoad, applyNotificationsPayload]);

  useEffect(() => {
    if (!canLoad) return undefined;

    const t = setTimeout(() => {
      void load();
    }, 0);

    return () => clearTimeout(t);
  }, [canLoad, load]);

  useEffect(() => {
    if (!canLoad) return undefined;

    const streamUrl = buildLiveFeedUrl({
      baseUrl,
      accessToken,
      kind: "notifications",
      limit: 10,
      interval: 5,
    });

    const source = new EventSource(streamUrl);
    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data || "{}");
        if (data?.kind !== "notifications") return;
        applyNotificationsPayload(data?.payload || {});
      } catch (err) {
        console.error(err);
      }
    };

    source.onerror = (err) => {
      void err;
    };

    return () => source.close();
  }, [canLoad, baseUrl, accessToken, applyNotificationsPayload]);

  async function refreshIncomingFromFriendsList() {
    const data = await getFriendsList({ baseUrl, accessToken });
    setIncoming(Array.isArray(data?.incoming) ? data.incoming : []);
  }

  async function handleAccept(requestId) {
    if (!requestId) return;
    setActionError(null);

    try {
      await acceptFriendRequest({ baseUrl, accessToken, requestId });
      await refreshIncomingFromFriendsList();
    } catch (err) {
      console.error(err);
      setActionError("Nu am putut accepta cererea.");
    }
  }

  async function handleReject(requestId) {
    if (!requestId) return;
    setActionError(null);

    try {
      await rejectFriendRequest({ baseUrl, accessToken, requestId });
      await refreshIncomingFromFriendsList();
    } catch (err) {
      console.error(err);
      setActionError("Nu am putut respinge cererea.");
    }
  }

  async function updatePrefs(patch) {
    if (!canLoad) return;
    setActionError(null);
    setIsSavingPrefs(true);

    try {
      const next = await updateNotificationPreferences({
        baseUrl,
        accessToken,
        preferences: patch,
      });
      setPrefs(next || null);
      notify({ type: "success", message: "Preferințele au fost salvate." });
    } catch (err) {
      console.error(err);
      notify({ type: "error", message: "Nu am putut salva preferințele." });
      setActionError("Nu am putut salva preferințele.");
    } finally {
      setIsSavingPrefs(false);
    }
  }

  if (!isAuthenticated) {
    return (
      <div style={ui.container}>
        <h1 style={{ marginTop: 0 }}>Notificări</h1>
        <p>Trebuie să fii logat ca să vezi notificările.</p>
        <p>
          <Link to="/login">Mergi la Login</Link>
        </p>
      </div>
    );
  }

  if (isAuthenticated && !isAuthVerified) {
    return (
      <div style={ui.container}>
        <h1 style={{ marginTop: 0 }}>Notificări</h1>
        <p style={{ marginTop: "14px" }}>Se încarcă...</p>
      </div>
    );
  }

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Notificări</h1>

      <section style={{ marginTop: "14px" }}>
        <h2 style={{ margin: 0 }}>Preferințe</h2>

        <div style={{ ...ui.card, marginTop: "12px" }}>
          {prefs ? (
            <div style={{ display: "grid", gap: 10 }}>
              <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={Boolean(prefs.notify_friend_requests)}
                  disabled={isSavingPrefs}
                  onChange={(e) =>
                    updatePrefs({ notify_friend_requests: e.target.checked })
                  }
                />
                Cereri de prietenie
              </label>

              <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={Boolean(prefs.notify_review_likes)}
                  disabled={isSavingPrefs}
                  onChange={(e) =>
                    updatePrefs({ notify_review_likes: e.target.checked })
                  }
                />
                Aprecieri la review-uri
              </label>

              <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={Boolean(prefs.notify_review_replies)}
                  disabled={isSavingPrefs}
                  onChange={(e) =>
                    updatePrefs({ notify_review_replies: e.target.checked })
                  }
                />
                Răspunsuri la review-uri
              </label>

              {isSavingPrefs ? (
                <div style={{ opacity: 0.85 }}>Se salvează…</div>
              ) : null}
            </div>
          ) : (
            <div style={{ opacity: 0.85 }}>Se încarcă preferințele…</div>
          )}
        </div>
      </section>

      <section style={{ marginTop: "26px" }}>
        <h2 style={{ margin: 0 }}>Feed notificări</h2>

        {!isLoading && !error ? (
          <div
            style={{
              display: "grid",
              gap: "8px",
              marginTop: "12px",
            }}
          >
            {notificationItems.length ? (
              notificationItems.map((item) => {
                const meta = notificationMeta(item.type);
                return (
                  <article
                    key={item.id}
                    style={{
                      ...ui.card,
                      padding: "12px",
                      display: "grid",
                      gridTemplateColumns: "minmax(0, 1fr) auto",
                      gap: "12px",
                      alignItems: "center",
                    }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          flexWrap: "wrap",
                          marginBottom: "6px",
                        }}
                      >
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                            border: "1px solid var(--border-color)",
                            borderRadius: "999px",
                            padding: "2px 9px",
                            background: meta.color,
                            fontSize: "0.88em",
                            fontWeight: 700,
                          }}
                        >
                          <span>{meta.icon}</span>
                          {meta.label}
                        </span>
                        {item.createdAt ? (
                          <time
                            dateTime={item.createdAt}
                            style={{ opacity: 0.72, fontSize: "0.9em" }}
                          >
                            {relativeTime(item.createdAt)}
                          </time>
                        ) : null}
                      </div>

                      <div style={{ lineHeight: 1.45 }}>
                        <Link to={`/users/${encodeURIComponent(item.user)}`}>
                          {item.user}
                        </Link>{" "}
                        <span style={{ opacity: 0.9 }}>{item.text}</span>
                        {item.albumTitle ? (
                          <>
                            {" "}
                            {item.albumSlug ? (
                              <Link
                                to={`/albums/${encodeURIComponent(
                                  item.albumSlug,
                                )}?tab=reviews`}
                              >
                                {item.albumTitle}
                              </Link>
                            ) : (
                              <strong>{item.albumTitle}</strong>
                            )}
                          </>
                        ) : null}
                      </div>
                    </div>

                    {item.type === "friend" ? (
                      <div
                        style={{
                          display: "flex",
                          gap: "8px",
                          flexWrap: "wrap",
                          justifyContent: "flex-end",
                        }}
                      >
                        <button
                          type="button"
                          style={ui.buttonSmall}
                          onClick={() => handleAccept(item.requestId)}
                        >
                          Acceptă
                        </button>
                        <button
                          type="button"
                          style={ui.buttonSmall}
                          onClick={() => handleReject(item.requestId)}
                        >
                          Respinge
                        </button>
                      </div>
                    ) : null}
                  </article>
                );
              })
            ) : (
              <div style={{ ...ui.card, opacity: 0.9 }}>
                Nu ai notificări noi.
              </div>
            )}
          </div>
        ) : null}
      </section>

      {!isLoading && !error ? (
        <div style={{ marginTop: "16px" }}>
          <button type="button" style={ui.button} onClick={load}>
            Reîncarcă
          </button>
        </div>
      ) : null}

      {isLoading ? <p style={{ marginTop: "14px" }}>Se încarcă...</p> : null}
      {error ? (
        <p style={{ ...ui.errorText, marginTop: "14px" }} role="alert">
          {error}
        </p>
      ) : null}

      {actionError ? (
        <p style={{ ...ui.errorText, marginTop: "10px" }} role="alert">
          {actionError}
        </p>
      ) : null}
    </div>
  );
}
