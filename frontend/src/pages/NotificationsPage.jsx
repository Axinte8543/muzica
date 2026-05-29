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

      const data = await getNotifications({ baseUrl, accessToken, limit: 20 });
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
    if (!canLoad) return;
    void load();
  }, [canLoad, load]);

  useEffect(() => {
    if (!canLoad) return undefined;

    const streamUrl = buildLiveFeedUrl({
      baseUrl,
      accessToken,
      kind: "notifications",
      limit: 20,
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
  }, [canLoad, baseUrl, accessToken]);

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
        <h2 style={{ margin: 0 }}>Cereri de prietenie</h2>

        {!isLoading && !error ? (
          <div style={{ ...ui.card, marginTop: "12px" }}>
            {incoming.length ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                }}
              >
                {incoming.map((fr) => {
                  const sender = String(fr?.sender_username || "").trim();
                  const requestId = fr?.id;
                  if (!sender || !requestId) return null;

                  return (
                    <div
                      key={requestId}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "12px",
                      }}
                    >
                      <div style={{ opacity: 0.95 }}>
                        <Link to={`/users/${encodeURIComponent(sender)}`}>
                          {sender}
                        </Link>{" "}
                        vrea să fie prieten cu tine.
                      </div>

                      <div style={{ display: "flex", gap: "8px" }}>
                        <button
                          type="button"
                          style={ui.button}
                          onClick={() => handleAccept(requestId)}
                        >
                          Acceptă
                        </button>
                        <button
                          type="button"
                          style={ui.button}
                          onClick={() => handleReject(requestId)}
                        >
                          Respinge
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ opacity: 0.9 }}>Nu ai cereri de prietenie noi.</div>
            )}
          </div>
        ) : null}
      </section>

      <section style={{ marginTop: "26px" }}>
        <h2 style={{ margin: 0 }}>Aprecieri la review-uri</h2>

        {!isLoading && !error ? (
          <div style={{ ...ui.card, marginTop: "12px" }}>
            {reviewLikes.length ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                }}
              >
                {reviewLikes.map((lk) => {
                  const liker = String(lk?.liker_username || "").trim();
                  const albumSlug = String(lk?.album_slug || "").trim();
                  const albumTitle = String(lk?.album_title || "Album");
                  const id = lk?.id;
                  if (!id || !liker) return null;

                  return (
                    <div key={id} style={{ opacity: 0.95 }}>
                      <Link to={`/users/${encodeURIComponent(liker)}`}>
                        {liker}
                      </Link>{" "}
                      a apreciat review-ul tău la{" "}
                      {albumSlug ? (
                        <Link to={`/albums/${encodeURIComponent(albumSlug)}`}>
                          {albumTitle}
                        </Link>
                      ) : (
                        <span style={{ fontWeight: 700 }}>{albumTitle}</span>
                      )}
                      .
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ opacity: 0.9 }}>
                Încă nu ai aprecieri la review-uri.
              </div>
            )}
          </div>
        ) : null}
      </section>

      <section style={{ marginTop: "26px" }}>
        <h2 style={{ margin: 0 }}>Răspunsuri la review-uri</h2>

        {!isLoading && !error ? (
          <div style={{ ...ui.card, marginTop: "12px" }}>
            {reviewReplies.length ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                }}
              >
                {reviewReplies.map((rp) => {
                  const replier = String(rp?.replier_username || "").trim();
                  const albumSlug = String(rp?.album_slug || "").trim();
                  const albumTitle = String(rp?.album_title || "Album");
                  const id = rp?.id;
                  if (!id || !replier) return null;

                  return (
                    <div key={id} style={{ opacity: 0.95 }}>
                      <Link to={`/users/${encodeURIComponent(replier)}`}>
                        {replier}
                      </Link>{" "}
                      a răspuns la review-ul tău la{" "}
                      {albumSlug ? (
                        <Link to={`/albums/${encodeURIComponent(albumSlug)}`}>
                          {albumTitle}
                        </Link>
                      ) : (
                        <span style={{ fontWeight: 700 }}>{albumTitle}</span>
                      )}
                      .
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ opacity: 0.9 }}>
                Încă nu ai răspunsuri la review-uri.
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
