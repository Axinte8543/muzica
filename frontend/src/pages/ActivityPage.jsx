import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  getActivity,
  getFriendsActivity,
  getFollowingActivity,
} from "../api/activity.js";
import { buildLiveFeedUrl } from "../api/live.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

function formatItem(item) {
  const actor = item?.actor_username || "Utilizator";
  const name = item?.target_name || "";

  switch (item?.activity_type) {
    case "listen_album":
      return `${actor} a ascultat ${name}`.trim();
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
    case "list_add_album":
      return `${actor} a adăugat ${name}`.trim();
    default:
      return `${actor} a făcut o acțiune`.trim();
  }
}

export default function ActivityPage() {
  const { baseUrl, accessToken, isAuthenticated, isAuthVerified, logout } =
    useAuth();

  const [filter, setFilter] = useState("friends");

  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const applyActivityPayload = useCallback((data) => {
    setItems(Array.isArray(data) ? data : []);
  }, []);

  const canLoad = useMemo(() => {
    return Boolean(isAuthVerified && accessToken);
  }, [isAuthVerified, accessToken]);

  useEffect(() => {
    let isCancelled = false;

    async function load() {
      if (!canLoad) {
        if (!isCancelled) {
          setItems([]);
          setIsLoading(false);
          setError(null);
        }
        return;
      }

      if (!isCancelled) {
        setIsLoading(true);
        setError(null);
      }

      try {
        const loader =
          filter === "friends"
            ? getFriendsActivity
            : filter === "following"
              ? getFollowingActivity
              : getActivity;
        const limit = filter === "friends" ? 10 : 50;

        const data = await loader({ baseUrl, accessToken, limit });
        if (!isCancelled) applyActivityPayload(data);
      } catch (err) {
        const status = err?.response?.status;
        if (status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled) setError("Nu am putut încărca activitatea.");
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      isCancelled = true;
    };
  }, [canLoad, baseUrl, accessToken, filter, logout, applyActivityPayload]);

  useEffect(() => {
    if (!canLoad) return undefined;

    const streamUrl = buildLiveFeedUrl({
      baseUrl,
      accessToken,
      kind: "activity",
      scope: filter,
      limit: filter === "friends" ? 10 : 50,
      interval: 5,
    });

    const source = new EventSource(streamUrl);
    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data || "{}");
        if (data?.kind !== "activity") return;
        applyActivityPayload(data?.payload || []);
      } catch (err) {
        console.error(err);
      }
    };

    source.onerror = (err) => {
      void err;
    };

    return () => source.close();
  }, [canLoad, baseUrl, accessToken, filter, applyActivityPayload]);

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Activitate</h1>

      {isAuthenticated && !isAuthVerified && (
        <p style={{ marginTop: "14px" }}>Se încarcă...</p>
      )}

      {!isAuthenticated && (
        <div style={{ marginTop: "14px" }}>
          <p>Trebuie să fii logat ca să vezi activitatea.</p>
          <p>
            <Link to="/login">Mergi la Login</Link>
          </p>
        </div>
      )}

      {isAuthVerified && isLoading && (
        <p style={{ marginTop: "14px" }}>Se încarcă...</p>
      )}

      {isAuthVerified && error && (
        <p style={{ ...ui.errorText, marginTop: "14px" }} role="alert">
          {error}
        </p>
      )}

      {isAuthVerified && !isLoading && !error && (
        <div style={{ ...ui.card, marginTop: "14px" }}>
          <div style={{ marginBottom: "10px", opacity: 0.85 }}>
            {filter === "following"
              ? "Activități recente ale artiștilor urmăriți"
              : "Activitate recentă"}
          </div>

          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={() => setFilter("all")}
              disabled={filter === "all"}
              style={ui.buttonSmall}
            >
              Toate
            </button>
            <button
              type="button"
              onClick={() => setFilter("friends")}
              disabled={filter === "friends"}
              style={ui.buttonSmall}
            >
              Doar prieteni
            </button>
            <button
              type="button"
              onClick={() => setFilter("following")}
              disabled={filter === "following"}
              style={ui.buttonSmall}
            >
              Doar follow
            </button>
          </div>

          {items.length ? (
            <div
              style={{ display: "flex", flexDirection: "column", gap: "8px" }}
              aria-live="polite"
            >
              {items.map((it) => (
                <div key={it.id} style={{ opacity: 0.95 }}>
                  {formatItem(it)}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ opacity: 0.9 }}>
              Încă nu există activitate. Urmărește artiști, notează albume și
              adaugă prieteni.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
