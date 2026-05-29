import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";
import {
  getMyAlbumRating,
  getMySongRating,
  rateAlbum,
  rateSong,
} from "../api/ratings.js";

function Star({ filled, disabled }) {
  return (
    <span
      aria-hidden="true"
      style={{
        fontSize: "22px",
        lineHeight: 1,
        opacity: disabled ? 0.5 : 1,
        color: "#111827",
      }}
    >
      {filled ? "★" : "☆"}
    </span>
  );
}

export default function RatingWidget({ kind, itemId }) {
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken, logout } =
    useAuth();

  const [myRating, setMyRating] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const canLoad = Boolean(isAuthVerified && accessToken && itemId);

  const title = useMemo(() => {
    if (kind === "album") return "Rating album";
    if (kind === "song") return "Rating melodie";
    return "Rating";
  }, [kind]);

  useEffect(() => {
    let isCancelled = false;

    async function loadMyRating() {
      if (!canLoad) {
        setMyRating(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const rating =
          kind === "album"
            ? await getMyAlbumRating({
                baseUrl,
                albumId: itemId,
                accessToken,
              })
            : await getMySongRating({
                baseUrl,
                songId: itemId,
                accessToken,
              });

        if (!isCancelled) setMyRating(rating);
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled) setError("Nu am putut încărca ratingul tău.");
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    loadMyRating();

    return () => {
      isCancelled = true;
    };
  }, [canLoad, kind, itemId, baseUrl, accessToken, logout]);

  async function handleRate(nextRating) {
    if (!isAuthVerified || !accessToken) return;
    if (!itemId) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const responseData =
        kind === "album"
          ? await rateAlbum({
              baseUrl,
              albumId: itemId,
              rating: nextRating,
              accessToken,
            })
          : await rateSong({
              baseUrl,
              songId: itemId,
              rating: nextRating,
              accessToken,
            });

      setMyRating(responseData?.rating ?? nextRating);
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut salva ratingul.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div
      style={{
        marginTop: "14px",
        ...ui.card,
        maxWidth: "420px",
      }}
    >
      <div style={{ fontWeight: 700 }}>{title}</div>

      {!isAuthenticated ? (
        <p style={{ margin: "8px 0 0", opacity: 0.9 }}>Please log in to rate</p>
      ) : null}

      {isAuthenticated && !isAuthVerified ? (
        <p style={{ margin: "8px 0 0", opacity: 0.9 }}>Se încarcă...</p>
      ) : null}

      <div style={{ marginTop: "8px", display: "flex", gap: "6px" }}>
        {Array.from({ length: 5 }).map((_, idx) => {
          const value = idx + 1;
          const filled = myRating ? value <= myRating : false;
          const disabled =
            !isAuthenticated ||
            !isAuthVerified ||
            isLoading ||
            isSubmitting ||
            !itemId;

          return (
            <button
              key={value}
              type="button"
              onClick={() => handleRate(value)}
              disabled={disabled}
              aria-label={`Dă rating ${value}`}
              style={{
                background: "transparent",
                border: "none",
                cursor: disabled ? "not-allowed" : "pointer",
                padding: 0,
              }}
            >
              <Star filled={filled} disabled={disabled} />
            </button>
          );
        })}
      </div>

      <div style={{ marginTop: "8px", fontSize: "0.95em", opacity: 0.9 }}>
        {isAuthenticated ? (
          isLoading ? (
            <span>Se încarcă ratingul tău...</span>
          ) : myRating ? (
            <span>Ratingul tău: {myRating}/5</span>
          ) : (
            <span>Nu ai votat încă.</span>
          )
        ) : null}
        {isSubmitting ? <span> Se salvează...</span> : null}
      </div>

      {error ? (
        <p style={{ ...ui.errorText, margin: "8px 0 0" }}>{error}</p>
      ) : null}
    </div>
  );
}
