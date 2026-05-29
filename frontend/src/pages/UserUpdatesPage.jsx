import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getActivity } from "../api/activity.js";
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
    default:
      return `${actor} a făcut o acțiune`.trim();
  }
}

export default function UserUpdatesPage() {
  const { baseUrl, accessToken, isAuthenticated, isAuthVerified, logout } =
    useAuth();

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
        const data = await getActivity({ baseUrl, accessToken, limit: 50 });
        if (!isCancelled) applyActivityPayload(data);
      } catch (err) {
        const status = err?.response?.status;
        if (status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled) setError("Nu am putut încărca update-urile.");
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      isCancelled = true;
    };
  }, [canLoad, baseUrl, accessToken, logout, applyActivityPayload]);

  useEffect(() => {
    if (!canLoad) return undefined;

    const streamUrl = buildLiveFeedUrl({
      baseUrl,
      accessToken,
      kind: "activity",
      scope: "all",
      limit: 50,
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
  }, [canLoad, baseUrl, accessToken, applyActivityPayload]);

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>User Updates</h1>

      {isAuthenticated && !isAuthVerified && (
        <p style={{ marginTop: "14px" }}>Se încarcă...</p>
      )}

      {!isAuthenticated && (
        <div style={{ marginTop: "14px" }}>
          <p>Trebuie să fii logat ca să vezi update-urile.</p>
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
              Încă nu există update-uri. Notează albume, ascultă muzică și
              urmărește artiști.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
