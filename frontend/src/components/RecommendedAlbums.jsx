import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/useAuth.js";
import { getRecommendations } from "../api/recommendations.js";
import { ui } from "../ui/ui.js";

function formatScore(value) {
  if (value === null || value === undefined) return "—";
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  return num.toFixed(2);
}

function isDemoRecommendation(rec) {
  const text = [
    rec?.album,
    rec?.album_slug,
    rec?.reason,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  return /\bdemo fresh\b/.test(text);
}

/**
 * Map recommendation reasons to icons and colors
 */
function getRecommendationIcon(reason) {
  if (!reason) return "💡";
  const lowerReason = String(reason).toLowerCase();

  if (lowerReason.includes("urmărești")) return "⭐"; // Following artist
  if (lowerReason.includes("interacționat des")) return "🎵"; // Frequent interaction
  if (lowerReason.includes("activitate frecventă")) return "🎸"; // Genre activity
  if (lowerReason.includes("prietenii")) return "👥"; // Friends
  if (lowerReason.includes("utilizatori cu gusturi similare")) return "🎯"; // Similar users
  if (lowerReason.includes("popular printre")) return "📈"; // Popular
  return "💡"; // Default
}

/**
 * Determine color scheme based on reason
 */
function getReasonStyles(reason) {
  if (!reason) {
    return {
      bg: "rgba(59, 130, 246, 0.1)",
      border: "rgba(59, 130, 246, 0.3)",
      text: "inherit",
    };
  }

  const lowerReason = String(reason).toLowerCase();

  if (lowerReason.includes("urmărești")) {
    return {
      bg: "rgba(234, 179, 8, 0.12)",
      border: "rgba(234, 179, 8, 0.4)",
      text: "inherit",
    };
  }
  if (lowerReason.includes("interacționat des")) {
    return {
      bg: "rgba(34, 197, 94, 0.12)",
      border: "rgba(34, 197, 94, 0.4)",
      text: "inherit",
    };
  }
  if (lowerReason.includes("activitate frecventă")) {
    return {
      bg: "rgba(168, 85, 247, 0.12)",
      border: "rgba(168, 85, 247, 0.4)",
      text: "inherit",
    };
  }
  if (lowerReason.includes("prietenii")) {
    return {
      bg: "rgba(236, 72, 153, 0.12)",
      border: "rgba(236, 72, 153, 0.4)",
      text: "inherit",
    };
  }
  if (lowerReason.includes("similar")) {
    return {
      bg: "rgba(59, 130, 246, 0.12)",
      border: "rgba(59, 130, 246, 0.4)",
      text: "inherit",
    };
  }

  return {
    bg: "rgba(75, 85, 99, 0.1)",
    border: "rgba(75, 85, 99, 0.3)",
    text: "inherit",
  };
}

export default function RecommendedAlbums({ limit = 8, pageSize = null }) {
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken, logout } =
    useAuth();

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const canLoad = useMemo(() => {
    return Boolean(isAuthVerified && accessToken);
  }, [isAuthVerified, accessToken]);

  useEffect(() => {
    let isCancelled = false;

    async function load() {
      if (!canLoad) {
        setItems([]);
        setIsLoading(false);
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const data = await getRecommendations({
          baseUrl,
          accessToken,
          limit,
        });

        if (!isCancelled) {
          const cleanItems = Array.isArray(data)
            ? data.filter((rec) => !isDemoRecommendation(rec))
            : [];
          setItems(cleanItems);
        }
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled) setError("Nu am putut încărca recomandările.");
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    load();

    return () => {
      isCancelled = true;
    };
  }, [canLoad, baseUrl, accessToken, limit, logout]);

  useEffect(() => {
    setPage(1);
  }, [items.length, pageSize]);

  if (!isAuthenticated) {
    return (
      <p style={{ marginTop: "10px" }}>Please log in to see recommendations</p>
    );
  }

  if (!isAuthVerified) {
    return <p style={{ marginTop: "10px" }}>Se încarcă...</p>;
  }

  if (isLoading) {
    return <p style={{ marginTop: "10px" }}>Se încarcă...</p>;
  }

  if (error) {
    return (
      <p style={{ ...ui.errorText, marginTop: "10px" }} role="alert">
        {error}
      </p>
    );
  }

  if (!items.length) {
    return <p style={{ marginTop: "10px" }}>No recommendations yet</p>;
  }

  const normalizedPageSize =
    Number.isFinite(Number(pageSize)) && Number(pageSize) > 0
      ? Math.max(1, Number(pageSize))
      : null;
  const totalPages = normalizedPageSize
    ? Math.max(1, Math.ceil(items.length / normalizedPageSize))
    : 1;
  const safePage = Math.min(page, totalPages);
  const visibleItems = normalizedPageSize
    ? items.slice(
        (safePage - 1) * normalizedPageSize,
        safePage * normalizedPageSize,
      )
    : items;

  return (
    <>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
          gap: "16px",
          marginTop: "12px",
        }}
      >
        {visibleItems.map((rec) => {
        const albumTitle = rec?.album || "Album";
        const artistName = rec?.artist || "Artist";
        const albumSlug = rec?.album_slug;
        const coverUrl = rec?.cover_url;
        const reason = String(rec?.reason || "").trim();
        const score = formatScore(rec?.score);
        const icon = getRecommendationIcon(reason);
        const reasonStyles = getReasonStyles(reason);

        const CardInner = (
          <div
            style={{
              ...ui.card,
              display: "flex",
              flexDirection: "column",
              height: "100%",
            }}
          >
            {/* Album Cover */}
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
                  marginBottom: "12px",
                }}
              />
            ) : (
              <div
                style={{
                  width: "100%",
                  aspectRatio: "1 / 1",
                  borderRadius: "8px",
                  background: ui.colors.mutedBg,
                  marginBottom: "12px",
                }}
              />
            )}

            {/* Album Info */}
            <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
              <div
                style={{ fontWeight: 700, fontSize: "15px", lineHeight: 1.3 }}
              >
                {albumTitle}
              </div>
              <div
                style={{
                  marginTop: "4px",
                  opacity: 0.8,
                  fontSize: "14px",
                  lineHeight: 1.2,
                }}
              >
                {artistName}
              </div>

              {/* Recommendation Reason - Highlighted */}
              {reason ? (
                <div
                  style={{
                    marginTop: "10px",
                    paddingTop: "10px",
                    borderTop: `1px solid ${reasonStyles.border}`,
                    flex: 1,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      gap: "6px",
                      alignItems: "flex-start",
                      padding: "8px 10px",
                      borderRadius: "6px",
                      backgroundColor: reasonStyles.bg,
                      border: `1px solid ${reasonStyles.border}`,
                      fontSize: "13px",
                      lineHeight: 1.4,
                    }}
                  >
                    <span style={{ flexShrink: 0, fontSize: "16px" }}>
                      {icon}
                    </span>
                    <span style={{ flex: 1, color: reasonStyles.text }}>
                      {reason}
                    </span>
                  </div>
                </div>
              ) : null}

              {/* Score Display */}
              <div
                style={{
                  marginTop: "10px",
                  paddingTop: "10px",
                  borderTop: `1px solid ${ui.colors.border}`,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  fontSize: "12px",
                  opacity: 0.75,
                }}
              >
                <span>Scor recomandare</span>
                <strong style={{ fontSize: "14px" }}>
                  {score}
                  /1.00
                </strong>
              </div>
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

      {normalizedPageSize && totalPages > 1 ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "12px",
            marginTop: "18px",
          }}
        >
          <button
            type="button"
            style={ui.button}
            onClick={() => setPage((value) => Math.max(1, value - 1))}
            disabled={safePage <= 1}
          >
            Prev
          </button>
          <span style={{ opacity: 0.85 }}>
            Page {safePage} / {totalPages} — {items.length} recomandări
          </span>
          <button
            type="button"
            style={ui.button}
            onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
            disabled={safePage >= totalPages}
          >
            Next
          </button>
        </div>
      ) : null}
    </>
  );
}
