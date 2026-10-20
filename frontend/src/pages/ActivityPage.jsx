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

function activityMeta(type) {
  switch (type) {
    case "listen_album":
      return { icon: "♪", label: "Ascultare", verb: "a ascultat" };
    case "rate_album":
      return { icon: "★", label: "Rating", verb: "a notat" };
    case "review_album":
      return { icon: "R", label: "Review", verb: "a scris un review la" };
    case "follow_artist":
      return { icon: "+", label: "Follow", verb: "a urmărit" };
    case "create_list":
      return { icon: "#", label: "Listă", verb: "a creat lista" };
    case "list_add_album":
      return { icon: "+", label: "Listă", verb: "a adăugat" };
    default:
      return { icon: "•", label: "Acțiune", verb: "a făcut o acțiune" };
  }
}

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

function ActivityCard({ item }) {
  const actor = item?.actor_username || "Utilizator";
  const name = item?.target_name || "";
  const meta = activityMeta(item?.activity_type);
  const when = relativeTime(item?.created_at);
  const rating = Number(item?.rating);
  const targetUrl = item?.target_url || "";
  const targetKind = item?.target_kind || "target";

  return (
    <article
      style={{
        ...ui.card,
        padding: "12px",
        display: "grid",
        gridTemplateColumns: "40px minmax(0, 1fr)",
        gap: "12px",
        alignItems: "start",
      }}
    >
      <div
        title={meta.label}
        aria-label={meta.label}
        style={{
          width: "40px",
          height: "40px",
          borderRadius: "8px",
          display: "grid",
          placeItems: "center",
          border: "1px solid var(--border-color)",
          background: "rgba(245, 158, 11, 0.13)",
          color: "var(--link-color)",
          fontWeight: 800,
        }}
      >
        {meta.icon}
      </div>

      <div style={{ minWidth: 0 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "10px",
            flexWrap: "wrap",
            marginBottom: "4px",
          }}
        >
          <span style={{ opacity: 0.78, fontSize: "0.9em" }}>
            {meta.label}
          </span>
          {when ? (
            <time
              dateTime={item?.created_at}
              style={{ opacity: 0.72, fontSize: "0.9em" }}
            >
              {when}
            </time>
          ) : null}
        </div>

        <div style={{ lineHeight: 1.45 }}>
          <Link to={`/users/${encodeURIComponent(actor)}`}>{actor}</Link>{" "}
          <span style={{ opacity: 0.9 }}>{meta.verb}</span>{" "}
          {targetUrl ? (
            <Link to={targetUrl} title={targetKind}>
              {name || "conținut"}
            </Link>
          ) : (
            <strong>{name || "conținut"}</strong>
          )}
          {Number.isFinite(rating) ? (
            <span
              style={{
                marginLeft: "8px",
                display: "inline-flex",
                alignItems: "center",
                border: "1px solid var(--border-color)",
                borderRadius: "999px",
                padding: "1px 8px",
                fontSize: "0.9em",
                color: "var(--link-color)",
              }}
            >
              {rating}/5
            </span>
          ) : null}
        </div>
      </div>
    </article>
  );
}

export default function ActivityPage() {
  const { baseUrl, accessToken, isAuthenticated, isAuthVerified, logout } =
    useAuth();

  const [filter, setFilter] = useState("friends");
  const [page, setPage] = useState(1);

  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const applyActivityPayload = useCallback((data) => {
    setItems(Array.isArray(data) ? data : []);
  }, []);

  const canLoad = useMemo(() => {
    return Boolean(isAuthVerified && accessToken);
  }, [isAuthVerified, accessToken]);

  const pageSize = 15;
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const pageItems = useMemo(() => {
    const start = (safePage - 1) * pageSize;
    return items.slice(start, start + pageSize);
  }, [items, safePage]);

  useEffect(() => {
    setPage(1);
  }, [filter]);

  useEffect(() => {
    if (page <= totalPages) return;
    setPage(totalPages);
  }, [page, totalPages]);

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
        const limit = 100;

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
      limit: 100,
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
            <>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                  marginTop: "12px",
                }}
                aria-live="polite"
              >
                {pageItems.map((it) => (
                  <ActivityCard key={it.id} item={it} />
                ))}
              </div>
              {items.length > pageSize ? (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "10px",
                    marginTop: "14px",
                  }}
                >
                  <button
                    type="button"
                    style={ui.buttonSmall}
                    disabled={safePage <= 1}
                    onClick={() => setPage((value) => Math.max(1, value - 1))}
                  >
                    Prev
                  </button>
                  <span style={{ opacity: 0.85 }}>
                    Pagina {safePage} / {totalPages} · {items.length} acțiuni
                  </span>
                  <button
                    type="button"
                    style={ui.buttonSmall}
                    disabled={safePage >= totalPages}
                    onClick={() =>
                      setPage((value) => Math.min(totalPages, value + 1))
                    }
                  >
                    Next
                  </button>
                </div>
              ) : null}
            </>
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
