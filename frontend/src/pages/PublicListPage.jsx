import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  getPublicListDetail,
  likePublicList,
  unlikePublicList,
} from "../api/lists.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

export default function PublicListPage() {
  const { listId } = useParams();
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken, logout } =
    useAuth();

  const [listData, setListData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isTogglingLike, setIsTogglingLike] = useState(false);

  useEffect(() => {
    let isCancelled = false;

    async function load() {
      if (!listId) return;

      setIsLoading(true);
      setError(null);

      try {
        const data = await getPublicListDetail({
          baseUrl,
          listId,
          accessToken,
        });
        if (!isCancelled) setListData(data);
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled) setError("Nu am putut încărca lista.");
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    load();

    return () => {
      isCancelled = true;
    };
  }, [accessToken, baseUrl, listId, logout]);

  async function handleToggleLike() {
    if (!isAuthenticated || !isAuthVerified || !accessToken || !listData?.id)
      return;

    setIsTogglingLike(true);
    setError(null);

    const wasLiked = Boolean(listData.is_liked);
    setListData((prev) =>
      prev
        ? {
            ...prev,
            is_liked: !wasLiked,
            likes_count: Math.max(
              0,
              Number(prev.likes_count || 0) + (wasLiked ? -1 : 1),
            ),
          }
        : prev,
    );

    try {
      if (wasLiked) {
        await unlikePublicList({ baseUrl, listId: listData.id, accessToken });
      } else {
        await likePublicList({ baseUrl, listId: listData.id, accessToken });
      }
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setListData((prev) =>
        prev
          ? {
              ...prev,
              is_liked: wasLiked,
              likes_count: Math.max(
                0,
                Number(prev.likes_count || 0) + (wasLiked ? 1 : -1),
              ),
            }
          : prev,
      );
      setError("Nu am putut actualiza like-ul.");
    } finally {
      setIsTogglingLike(false);
    }
  }

  const albums = Array.isArray(listData?.albums) ? listData.albums : [];

  return (
    <div style={{ ...ui.container, maxWidth: "1200px", margin: "0 auto" }}>
      <p style={{ marginTop: 0, display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Link to="/lists">← Înapoi la liste</Link>
      </p>

      {isLoading ? <p>Se încarcă...</p> : null}
      {error ? <p style={ui.errorText}>{error}</p> : null}

      {!isLoading && !error && listData ? (
        <>
          <section style={{ ...ui.card, marginBottom: "14px" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 12,
                flexWrap: "wrap",
              }}
            >
              <div>
                <h1 style={{ margin: "0 0 8px" }}>{listData.name}</h1>
                <div style={{ opacity: 0.85 }}>
                  de{" "}
                  <Link to={`/users/${listData.user_username}`}>
                    @{listData.user_username}
                  </Link>{" "}
                  · {listData.albums_count || 0} albume · ❤️{" "}
                  {listData.likes_count || 0}
                </div>
                {listData.description ? (
                  <p
                    style={{
                      marginTop: "10px",
                      whiteSpace: "pre-wrap",
                      opacity: 0.92,
                    }}
                  >
                    {listData.description}
                  </p>
                ) : null}
                {Array.isArray(listData.tags) && listData.tags.length ? (
                  <div style={{ marginTop: "10px", opacity: 0.82 }}>
                    Taguri: {listData.tags.join(", ")}
                  </div>
                ) : null}
              </div>

              {isAuthenticated ? (
                <button
                  type="button"
                  style={ui.button}
                  disabled={isTogglingLike}
                  onClick={handleToggleLike}
                >
                  {isTogglingLike
                    ? "Se actualizează..."
                    : listData.is_liked
                      ? "Unlike"
                      : "Like"}
                </button>
              ) : null}
            </div>
          </section>

          <section style={ui.card}>
            <h3 style={{ marginTop: 0 }}>Albume din listă</h3>
            {albums.length ? (
              <div
                style={{
                  display: "grid",
                  gap: "10px",
                  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                }}
              >
                {albums.map((item) => (
                  <article
                    key={item.id}
                    style={{ ...ui.card, padding: "12px" }}
                  >
                    <div
                      style={{
                        display: "flex",
                        gap: "10px",
                        alignItems: "center",
                      }}
                    >
                      {item.cover_url ? (
                        <img
                          src={item.cover_url}
                          alt={item.album_title}
                          style={{
                            width: "56px",
                            height: "56px",
                            borderRadius: "10px",
                            objectFit: "cover",
                            border: "1px solid var(--border-color)",
                          }}
                        />
                      ) : null}
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ fontWeight: 700 }}>
                          <Link to={`/albums/${item.album_slug}`}>
                            {item.album_title}
                          </Link>
                        </div>
                        <div style={{ opacity: 0.82 }}>
                          <Link to={`/artists/${item.artist_slug}`}>
                            {item.artist_name}
                          </Link>
                        </div>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <p style={{ marginBottom: 0, opacity: 0.85 }}>
                Lista este goală.
              </p>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
