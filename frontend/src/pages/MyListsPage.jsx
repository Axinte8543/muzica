import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getMyLists } from "../api/lists.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("ro-RO", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

function coverPreview(albums) {
  const items = Array.isArray(albums) ? albums.slice(0, 4) : [];
  if (!items.length) {
    return (
      <div
        style={{
          aspectRatio: "1 / 1",
          borderRadius: 8,
          background: ui.colors.mutedBg,
          display: "grid",
          placeItems: "center",
          opacity: 0.82,
        }}
      >
        Listă goală
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(2, 1fr)",
        gap: 6,
      }}
    >
      {items.map((album, index) => (
        <div
          key={album?.id || album?.album_id || index}
          style={{
            aspectRatio: "1 / 1",
            borderRadius: 8,
            overflow: "hidden",
            background: ui.colors.mutedBg,
          }}
        >
          {album?.cover_url ? (
            <img
              src={album.cover_url}
              alt={`Coperta albumului ${album?.album_title || "Album"}`}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                display: "block",
              }}
            />
          ) : null}
        </div>
      ))}
    </div>
  );
}

export default function MyListsPage() {
  const {
    user,
    baseUrl,
    isAuthenticated,
    isAuthVerified,
    accessToken,
    logout,
  } = useAuth();

  const [lists, setLists] = useState([]);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!isAuthVerified || !accessToken) {
        setLists([]);
        setIsLoading(false);
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const data = await getMyLists({ baseUrl, accessToken });
        if (cancelled) return;
        const username = String(user?.username || "").toLowerCase();
        const ownedLists = (Array.isArray(data) ? data : []).filter((item) => {
          const owner = String(item?.user_username || "").toLowerCase();
          return item?.my_role === "owner" || (username && owner === username);
        });
        setLists(ownedLists);
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!cancelled) {
          setLists([]);
          setError("Nu am putut încărca listele tale.");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [accessToken, baseUrl, isAuthVerified, logout, user?.username]);

  const visibleLists = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return lists;
    return lists.filter((item) => {
      return (
        String(item?.name || "").toLowerCase().includes(needle) ||
        String(item?.description || "").toLowerCase().includes(needle)
      );
    });
  }, [lists, query]);

  if (!isAuthenticated) {
    return (
      <div style={ui.container}>
        <h1 style={{ marginTop: 0 }}>Listele mele</h1>
        <p>Trebuie să fii logat ca să vezi listele tale.</p>
        <Link to="/login" style={ui.button}>
          Mergi la Login
        </Link>
      </div>
    );
  }

  return (
    <div style={ui.container}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1 style={{ marginTop: 0, marginBottom: 8 }}>Listele mele</h1>
          <p style={{ margin: 0, opacity: 0.86 }}>
            Liste create de {user?.username || "utilizatorul curent"}.
          </p>
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Link to="/lists" style={{ ...ui.button, textDecoration: "none" }}>
            Toate listele
          </Link>
          <Link
            to="/lists#my-lists"
            style={{ ...ui.button, textDecoration: "none" }}
          >
            Gestionează liste
          </Link>
        </div>
      </div>

      <div style={{ ...ui.card, marginTop: 18 }}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Caută în listele tale..."
          style={{ ...ui.input, width: "100%", boxSizing: "border-box" }}
        />
      </div>

      {isAuthVerified && isLoading ? <p>Se încarcă...</p> : null}
      {error ? (
        <p style={{ ...ui.errorText, marginTop: 14 }} role="alert">
          {error}
        </p>
      ) : null}

      {!isLoading && !error && lists.length === 0 ? (
        <div style={{ ...ui.card, marginTop: 18 }}>
          Nu ai creat încă nicio listă.
        </div>
      ) : null}

      {!isLoading && !error && lists.length > 0 ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: 16,
            marginTop: 18,
          }}
        >
          {visibleLists.map((list) => {
            const albumsCount = Number(list?.albums_count || 0);
            const albums = Array.isArray(list?.albums) ? list.albums : [];
            const isPublic = Boolean(list?.is_public);

            return (
              <article
                key={list.id}
                style={{
                  ...ui.card,
                  display: "grid",
                  gap: 12,
                  alignContent: "start",
                }}
              >
                {coverPreview(albums)}

                <div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 10,
                      alignItems: "center",
                    }}
                  >
                    <h2 style={{ margin: 0, fontSize: "1.15rem" }}>
                      {list.name}
                    </h2>
                    <span
                      style={{
                        border: `1px solid ${ui.colors.border}`,
                        borderRadius: 999,
                        padding: "3px 8px",
                        fontSize: "0.82rem",
                        opacity: 0.86,
                      }}
                    >
                      {isPublic ? "Publică" : "Privată"}
                    </span>
                  </div>

                  {list.description ? (
                    <p style={{ marginBottom: 0, opacity: 0.86 }}>
                      {list.description}
                    </p>
                  ) : null}
                </div>

                <div style={{ display: "grid", gap: 6, opacity: 0.82 }}>
                  <span>{albumsCount} albume</span>
                  {list.created_at ? (
                    <span>Creată pe {formatDate(list.created_at)}</span>
                  ) : null}
                </div>

                {albums.length ? (
                  <ul style={{ margin: 0, paddingLeft: 18 }}>
                    {albums.slice(0, 3).map((album) => (
                      <li key={album.id || album.album_id}>
                        {album.album_slug ? (
                          <Link to={`/albums/${album.album_slug}`}>
                            {album.album_title}
                          </Link>
                        ) : (
                          album.album_title || "Album"
                        )}
                      </li>
                    ))}
                  </ul>
                ) : null}

                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  {isPublic ? (
                    <Link
                      to={`/lists/public/${list.id}`}
                      style={{ ...ui.buttonSmall, textDecoration: "none" }}
                    >
                      Vezi public
                    </Link>
                  ) : null}
                  <Link
                    to="/lists#my-lists"
                    style={{ ...ui.buttonSmall, textDecoration: "none" }}
                  >
                    Editează
                  </Link>
                </div>
              </article>
            );
          })}
        </div>
      ) : null}

      {!isLoading && !error && lists.length > 0 && visibleLists.length === 0 ? (
        <div style={{ ...ui.card, marginTop: 18 }}>
          Nicio listă nu corespunde căutării.
        </div>
      ) : null}
    </div>
  );
}
