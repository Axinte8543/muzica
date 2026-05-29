import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import ProfileNav from "../components/ProfileNav.jsx";
import PaginationControls from "../components/PaginationControls.jsx";
import { useAuth } from "../context/useAuth.js";
import { getMyReviews } from "../api/reviews.js";
import { ui } from "../ui/ui.js";

function getErrorMessage(err, fallback) {
  const data = err?.response?.data;
  if (typeof data === "string" && data.trim()) return data;
  if (data && typeof data === "object") {
    const firstKey = Object.keys(data)[0];
    const val = data[firstKey];
    if (Array.isArray(val) && val[0]) return String(val[0]);
    if (typeof val === "string" && val.trim()) return val;
  }
  return fallback;
}

function formatDateOnly(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("ro-RO", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export default function ProfileReviewsPage() {
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken, logout } =
    useAuth();

  const [reviews, setReviews] = useState([]);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const itemsPerPage = 10;

  const totalPages = useMemo(() => {
    return Math.max(1, Math.ceil(reviews.length / itemsPerPage));
  }, [itemsPerPage, reviews.length]);

  const pageReviews = useMemo(() => {
    const start = (page - 1) * itemsPerPage;
    return reviews.slice(start, start + itemsPerPage);
  }, [itemsPerPage, page, reviews]);

  useEffect(() => {
    let isCancelled = false;

    async function load() {
      if (!isAuthVerified || !accessToken) {
        setReviews([]);
        setIsLoading(false);
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const data = await getMyReviews({ baseUrl, accessToken });
        if (isCancelled) return;
        setReviews(Array.isArray(data) ? data : []);
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled) {
          setReviews([]);
          setError(getErrorMessage(err, "Nu am putut încărca review-urile."));
        }
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    load();

    return () => {
      isCancelled = true;
    };
  }, [accessToken, baseUrl, isAuthVerified, logout]);

  useEffect(() => {
    setPage((prev) => Math.min(prev, totalPages));
  }, [totalPages]);

  if (!isAuthenticated) {
    return (
      <div>
        <ProfileNav />
        <div style={{ padding: "24px" }}>
          <h1 style={{ marginTop: 0 }}>Review-urile mele</h1>
          <p>Trebuie să fii logat ca să vezi review-urile tale.</p>
          <p>
            <Link to="/login">Mergi la Login</Link>
          </p>
        </div>
      </div>
    );
  }

  if (isAuthenticated && !isAuthVerified) {
    return (
      <div>
        <ProfileNav />
        <div style={{ padding: "24px" }}>
          <h1 style={{ marginTop: 0 }}>Review-urile mele</h1>
          <p style={{ marginTop: "14px" }}>Se încarcă...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <ProfileNav />
      <div style={{ padding: "24px" }}>
        <h1 style={{ marginTop: 0 }}>Review-urile mele</h1>

        {isLoading ? <p>Loading reviews...</p> : null}
        {error ? <p style={ui.errorText}>{error}</p> : null}

        {!isLoading && !error ? (
          reviews.length ? (
            <ul style={{ paddingLeft: "18px" }}>
              {pageReviews.map((r) => (
                <li key={r.id} style={{ marginBottom: "14px" }}>
                  <div>
                    <strong>
                      <Link to={`/albums/${r.album_slug}`}>
                        {r.album_title}
                      </Link>
                    </strong>
                    <span style={{ opacity: 0.9 }}>
                      {" "}
                      —{" "}
                      <Link to={`/artists/${r.artist_slug}`}>
                        {r.artist_name}
                      </Link>
                    </span>
                  </div>

                  <div
                    style={{
                      marginTop: "8px",
                      padding: "10px 12px",
                      border: `1px solid ${ui.colors.border}`,
                      borderRadius: 12,
                      background: "rgba(255, 255, 255, 0.02)",
                    }}
                  >
                    {r.title ? (
                      <div style={{ fontWeight: 700, marginBottom: 4 }}>
                        {r.title}
                      </div>
                    ) : null}
                    {r.content ? (
                      <div style={{ whiteSpace: "pre-wrap" }}>{r.content}</div>
                    ) : null}
                  </div>

                  <div
                    style={{
                      marginTop: "6px",
                      opacity: 0.85,
                      fontSize: "0.9em",
                    }}
                  >
                    Likes: {r.likes_count ?? 0} • Postat la:{" "}
                    {formatDateOnly(r.created_at)}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p>No reviews yet</p>
          )
        ) : null}

        <PaginationControls
          page={page}
          totalPages={totalPages}
          totalCount={reviews.length}
          onPrev={() => setPage((prev) => Math.max(1, prev - 1))}
          onNext={() => setPage((prev) => Math.min(totalPages, prev + 1))}
        />
      </div>
    </div>
  );
}
