import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getSimilarUsers } from "../api/similarUsers.js";
import { sendFriendRequest } from "../api/friends.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

function similarityToPercent(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return null;
  const pct = num <= 1 ? num * 100 : num;
  return Math.max(0, Math.min(100, Math.round(pct)));
}

export default function SimilarUsers({ limit = 10 }) {
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken } = useAuth();

  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const [sentTo, setSentTo] = useState(() => new Set());
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canLoad = useMemo(() => {
    return Boolean(isAuthVerified && accessToken);
  }, [isAuthVerified, accessToken]);

  useEffect(() => {
    let isCancelled = false;

    async function load() {
      if (!canLoad) {
        setUsers([]);
        setIsLoading(false);
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const data = await getSimilarUsers({
          baseUrl,
          accessToken,
          limit,
        });

        if (!isCancelled) setUsers(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error(err);
        if (!isCancelled)
          setError("Nu am putut încărca utilizatorii similari.");
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    load();

    return () => {
      isCancelled = true;
    };
  }, [canLoad, baseUrl, accessToken, limit]);

  if (isAuthenticated && !isAuthVerified) {
    return <p style={{ marginTop: "10px" }}>Se încarcă...</p>;
  }

  if (!isAuthenticated) {
    return (
      <div style={{ marginTop: "10px" }}>
        <p>Trebuie să fii logat ca să vezi utilizatori similari.</p>
        <p>
          <Link to="/login">Mergi la Login</Link>
        </p>
      </div>
    );
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

  if (!users.length) {
    return (
      <div style={{ marginTop: "10px" }}>
        <p style={{ margin: 0 }}>Încă nu există utilizatori similari.</p>
        <p style={{ marginTop: "8px", opacity: 0.9 }}>
          E nevoie de mai multă activitate — notează mai multe albume ca să
          primești potriviri.
        </p>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
        gap: "16px",
        marginTop: "12px",
      }}
    >
      {users.map((u) => {
        const username = String(u?.username || "").trim();
        const userId = u?.user_id;
        const pct = similarityToPercent(u?.similarity);
        const pctLabel = pct === null ? "—" : `Similaritate: ${pct}%`;

        const commonGenres = Array.isArray(u?.common_genres)
          ? u.common_genres
          : [];
        const commonArtists = Array.isArray(u?.common_artists)
          ? u.common_artists
          : [];
        const commonAlbums = Array.isArray(u?.common_albums)
          ? u.common_albums
          : [];

        if (!username) return null;

        const to = userId
          ? `/users/${encodeURIComponent(username)}?id=${encodeURIComponent(
              String(userId),
            )}`
          : `/users/${encodeURIComponent(username)}`;

        return (
          <Link
            key={`${username}-${String(userId ?? "")}`}
            to={to}
            style={{ color: "inherit", textDecoration: "none" }}
          >
            <div style={ui.card}>
              <div
                style={{
                  display: "flex",
                  gap: "10px",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <div style={{ fontWeight: 700 }}>{username}</div>
                <button
                  type="button"
                  style={ui.button}
                  disabled={isSubmitting || sentTo.has(username)}
                  onClick={async (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (!accessToken) return;
                    setIsSubmitting(true);
                    try {
                      await sendFriendRequest({
                        baseUrl,
                        accessToken,
                        receiverUsername: username,
                      });
                      setSentTo((prev) => {
                        const next = new Set(prev);
                        next.add(username);
                        return next;
                      });
                    } catch (err) {
                      console.error(err);
                    } finally {
                      setIsSubmitting(false);
                    }
                  }}
                >
                  {sentTo.has(username) ? "Cerere trimisă" : "Adaugă prieten"}
                </button>
              </div>
              <div style={{ marginTop: "6px", opacity: 0.9 }}>{pctLabel}</div>

              {!!commonGenres.length && (
                <div style={{ marginTop: "8px" }}>
                  <div style={{ fontWeight: 700 }}>Genuri comune</div>
                  <div style={{ opacity: 0.9 }}>{commonGenres.join(", ")}</div>
                </div>
              )}

              {!!commonArtists.length && (
                <div style={{ marginTop: "8px" }}>
                  <div style={{ fontWeight: 700 }}>Artiști comuni</div>
                  <div style={{ opacity: 0.9 }}>{commonArtists.join(", ")}</div>
                </div>
              )}

              {!!commonAlbums.length && (
                <div style={{ marginTop: "8px" }}>
                  <div style={{ fontWeight: 700 }}>Albume comune</div>
                  <div style={{ opacity: 0.9 }}>{commonAlbums.join(", ")}</div>
                </div>
              )}
            </div>
          </Link>
        );
      })}
    </div>
  );
}
