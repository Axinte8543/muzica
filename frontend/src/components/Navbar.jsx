import { useEffect, useMemo, useState } from "react";
import {
  Link,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "../context/useAuth.js";
import { apiClient } from "../api/apiClient.js";
import { ui } from "../ui/ui.js";

const RECENT_SEARCHES_KEY = "recentSearches.v1";
const RECENT_SEARCHES_LIMIT = 8;
const THEME_STORAGE_KEY = "theme.v1";

function getInitialTheme() {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    if (saved === "dark" || saved === "light") return saved;
  } catch {
    // ignore
  }

  if (typeof window !== "undefined") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  return "light";
}

function applyTheme(theme) {
  if (typeof document === "undefined") return;
  document.documentElement.dataset.theme = theme === "dark" ? "dark" : "light";
}

function saveRecentSearches(items) {
  try {
    localStorage.setItem(
      RECENT_SEARCHES_KEY,
      JSON.stringify(items.slice(0, RECENT_SEARCHES_LIMIT)),
    );
  } catch {
    // ignore
  }
}

function loadRecentSearches() {
  try {
    const raw = localStorage.getItem(RECENT_SEARCHES_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed)
      ? parsed.map((item) => String(item || "").trim()).filter(Boolean)
      : [];
  } catch {
    return [];
  }
}

function pushRecentSearch(items, q) {
  const trimmed = String(q || "").trim();
  if (!trimmed) return items;
  const next = [trimmed, ...items.filter((v) => v !== trimmed)].slice(
    0,
    RECENT_SEARCHES_LIMIT,
  );
  saveRecentSearches(next);
  return next;
}

function releaseTypeLabel(item) {
  const type = String(item?.release_type || item?.album_release_type || "").toLowerCase();
  if (type === "single") return "Single";
  if (type === "ep") return "EP";
  if (type === "compilation") return "Compilație";
  return "Album";
}

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { accessToken, isAuthenticated, isAuthVerified, user, logout } =
    useAuth();

  const currentQ = useMemo(() => {
    return (searchParams.get("q") || "").trim();
  }, [searchParams]);

  const [searchValue, setSearchValue] = useState(() => currentQ);
  const [recentSearches, setRecentSearches] = useState(() =>
    loadRecentSearches(),
  );
  const [isSearchFocused, setIsSearchFocused] = useState(false);
  const [theme, setTheme] = useState(() => getInitialTheme());
  const [debouncedSearch, setDebouncedSearch] = useState(() =>
    String(currentQ || "").trim(),
  );
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    applyTheme(theme);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // ignore
    }
  }, [theme]);

  useEffect(() => {
    const next = String(searchValue || "").trim();
    const handle = setTimeout(() => setDebouncedSearch(next), next ? 200 : 0);
    return () => clearTimeout(handle);
  }, [searchValue]);

  const suggestionsQuery = useQuery({
    queryKey: [
      "searchSuggestions",
      debouncedSearch,
      isAuthVerified ? "auth" : "anon",
      accessToken || "",
    ],
    enabled: Boolean(debouncedSearch),
    staleTime: 1000 * 30,
    placeholderData: (prev) => prev,
    queryFn: async () => {
      const musicReq = apiClient.get(`/api/search/`, {
        params: { q: debouncedSearch, limit: 5 },
      });

      const usersReq =
        isAuthVerified && accessToken
          ? apiClient.get(`/api/users/search`, {
              params: { q: debouncedSearch, limit: 5 },
            })
          : Promise.resolve({ data: [] });

      const [musicRes, usersRes] = await Promise.all([musicReq, usersReq]);

      return {
        artists: musicRes.data?.artists || [],
        albums: musicRes.data?.albums || [],
        songs: musicRes.data?.songs || [],
        users: Array.isArray(usersRes.data) ? usersRes.data : [],
      };
    },
  });

  const suggestions = useMemo(() => {
    const data = suggestionsQuery.data;
    return {
      users: Array.isArray(data?.users) ? data.users : [],
      artists: Array.isArray(data?.artists) ? data.artists : [],
      albums: Array.isArray(data?.albums) ? data.albums : [],
      songs: Array.isArray(data?.songs) ? data.songs : [],
    };
  }, [suggestionsQuery.data]);

  const hasAnySuggestions =
    suggestions.users.length ||
    suggestions.artists.length ||
    suggestions.albums.length ||
    suggestions.songs.length;

  const showDropdown =
    isSearchFocused &&
    (debouncedSearch ? hasAnySuggestions : recentSearches.length);

  function rememberSearch(q) {
    setRecentSearches((prev) => pushRecentSearch(prev, q));
  }

  function goToSearch(q, options) {
    const nextQ = String(q || "").trim();
    setSearchValue(nextQ);
    if (nextQ) rememberSearch(nextQ);
    navigate(`/search?q=${encodeURIComponent(nextQ)}`, options);
  }

  function goTo(path) {
    setIsSearchFocused(false);
    navigate(path);
  }

  useEffect(() => {
    if (location.pathname !== "/search") return;

    const nextQ = searchValue.trim();
    if (nextQ === currentQ) return;

    const handle = setTimeout(() => {
      navigate(`/search?q=${encodeURIComponent(nextQ)}`, { replace: true });
    }, 300);

    return () => clearTimeout(handle);
  }, [currentQ, location.pathname, navigate, searchValue]);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  function handleSubmit(e) {
    e.preventDefault();
    const nextQ = searchValue.trim();
    if (nextQ) rememberSearch(nextQ);
    navigate(`/search?q=${encodeURIComponent(nextQ)}`);
  }

  function toggleTheme() {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }

  const brandLinkStyle = {
    display: "inline-flex",
    alignItems: "center",
    gap: "10px",
    minWidth: 0,
    textDecoration: "none",
    color: "inherit",
  };

  const brandMarkStyle = {
    width: "36px",
    height: "36px",
    borderRadius: "12px",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    background:
      "linear-gradient(135deg, rgba(245, 158, 11, 0.98), rgba(251, 191, 36, 0.82))",
    color: "#0f172a",
    fontWeight: 900,
    letterSpacing: "-0.04em",
    boxShadow: "0 10px 24px rgba(245, 158, 11, 0.22)",
    flexShrink: 0,
  };

  const brandTextStyle = {
    display: "flex",
    flexDirection: "column",
    lineHeight: 1,
    minWidth: 0,
  };

  const brandNameStyle = {
    fontSize: "1.05rem",
    fontWeight: 900,
    letterSpacing: "-0.03em",
  };

  return (
    <div
      style={{
        width: "min(100%, 1440px)",
        margin: "12px auto 0",
        padding: "12px 14px",
      }}
    >
      <div
        style={{
          position: "sticky",
          top: 12,
          zIndex: 1000,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "16px",
          padding: "14px 18px",
          border: `1px solid ${ui.colors.border}`,
          borderRadius: "24px",
          backgroundColor: "var(--surface-color)",
          boxShadow: "var(--shadow-card)",
          backdropFilter: "blur(18px)",
        }}
      >
        <div
          className="navbar-left"
          style={{ display: "flex", alignItems: "center", gap: "12px" }}
        >
          <Link
            to="/"
            title="roMusic - prima pagină"
            style={brandLinkStyle}
          >
            <span aria-hidden="true" style={brandMarkStyle}>rM</span>
            <span style={brandTextStyle}>
              <span style={brandNameStyle}>roMusic</span>
            </span>
          </Link>
          <div className="navbar-links">
            <Link to="/albums">Albume</Link>
            {isAuthenticated ? <Link to="/dashboard">Dashboard</Link> : null}
            {isAuthenticated ? (
              <Link to="/recommendations">Recomandări</Link>
            ) : null}
            {isAuthenticated ? (
              <Link to="/notifications">Notificări</Link>
            ) : null}
            {isAuthenticated ? <Link to="/messages">Mesaje</Link> : null}
            <Link to="/lists">Liste</Link>
            <Link to="/following">Urmăriți</Link>
            {isAuthenticated ? <Link to="/activity">Activitate</Link> : null}
            {isAuthenticated ? <Link to="/suggest">Propune</Link> : null}
          </div>
          <button
            className="navbar-mobile-button"
            aria-label="Meniu"
            aria-expanded={mobileOpen}
            aria-controls="mobile-navigation"
            onClick={() => setMobileOpen((v) => !v)}
            type="button"
          >
            ☰
          </button>
        </div>

        <form
          onSubmit={handleSubmit}
          style={{
            flex: 1,
            display: "flex",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              position: "relative",
              width: "100%",
              maxWidth: "520px",
            }}
          >
            <div style={{ display: "flex", gap: "8px", width: "100%" }}>
              <input
                type="search"
                aria-label="Caută muzică"
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                onFocus={() => setIsSearchFocused(true)}
                onBlur={() => {
                  window.setTimeout(() => setIsSearchFocused(false), 120);
                }}
                placeholder="Caută..."
                style={{
                  width: "100%",
                  ...ui.input,
                }}
              />
              <button type="submit" style={ui.button}>
                Caută
              </button>
            </div>

            {showDropdown ? (
              <div
                onMouseDown={(e) => e.preventDefault()}
                style={{
                  position: "absolute",
                  top: "100%",
                  left: 0,
                  right: 0,
                  marginTop: "8px",
                  border: `1px solid ${ui.colors.border}`,
                  borderRadius: "16px",
                  backgroundColor: "var(--surface-strong)",
                  color: "var(--text-color)",
                  padding: "12px",
                  boxShadow: "var(--shadow-card)",
                  backdropFilter: "blur(18px)",
                  zIndex: 2000,
                }}
              >
                {!debouncedSearch ? (
                  <div style={{ display: "grid", gap: 8 }}>
                    <div
                      style={{
                        fontSize: "0.85em",
                        opacity: 0.75,
                        fontWeight: 700,
                      }}
                    >
                      Recent searches
                    </div>

                    {recentSearches.map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => goToSearch(item)}
                        style={{
                          ...ui.buttonSmall,
                          textAlign: "left",
                          width: "100%",
                        }}
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div style={{ display: "grid", gap: 12 }}>
                    {suggestions.users.length ? (
                      <div style={{ display: "grid", gap: 6 }}>
                        <div style={{ fontSize: "0.85em", opacity: 0.75, fontWeight: 700 }}>
                          Users
                        </div>
                        {suggestions.users.slice(0, 4).map((u) => {
                          const username = String(u?.username || "").trim();
                          const id = u?.id;
                          if (!username) return null;
                          const path = id
                            ? `/users/${encodeURIComponent(username)}?id=${encodeURIComponent(String(id))}`
                            : `/users/${encodeURIComponent(username)}`;
                          return (
                            <button
                              key={`user-${String(id ?? username)}`}
                              type="button"
                              onClick={() => goTo(path)}
                              style={{ ...ui.buttonSmall, textAlign: "left", width: "100%" }}
                            >
                              {username}
                            </button>
                          );
                        })}
                      </div>
                    ) : null}

                    {suggestions.artists.length ? (
                      <div style={{ display: "grid", gap: 6 }}>
                        <div style={{ fontSize: "0.85em", opacity: 0.75, fontWeight: 700 }}>
                          Artists
                        </div>
                        {suggestions.artists.slice(0, 5).map((a) => (
                          <button
                            key={`artist-${a.id}`}
                            type="button"
                            onClick={() => goTo(`/artists/${encodeURIComponent(String(a.slug))}`)}
                            style={{ ...ui.buttonSmall, textAlign: "left", width: "100%" }}
                          >
                            {a.name}
                          </button>
                        ))}
                      </div>
                    ) : null}

                    {suggestions.albums.length ? (
                      <div style={{ display: "grid", gap: 6 }}>
                        <div style={{ fontSize: "0.85em", opacity: 0.75, fontWeight: 700 }}>
                          Albume / Singles
                        </div>
                        {suggestions.albums.slice(0, 5).map((a) => (
                          <button
                            key={`album-${a.id}`}
                            type="button"
                            onClick={() => goTo(`/albums/${encodeURIComponent(String(a.slug))}`)}
                            style={{ ...ui.buttonSmall, textAlign: "left", width: "100%" }}
                          >
                            [{releaseTypeLabel(a)}]{" "}
                            {a.title}
                            {a.artist_name ? ` - ${a.artist_name}` : ""}
                          </button>
                        ))}
                      </div>
                    ) : null}

                    {suggestions.songs.length ? (
                      <div style={{ display: "grid", gap: 6 }}>
                        <div style={{ fontSize: "0.85em", opacity: 0.75, fontWeight: 700 }}>
                          Piese
                        </div>
                        {suggestions.songs.slice(0, 5).map((s) => (
                          <button
                            key={`song-${s.id}`}
                            type="button"
                            onClick={() => goTo(`/songs/${encodeURIComponent(String(s.slug))}`)}
                            style={{ ...ui.buttonSmall, textAlign: "left", width: "100%" }}
                          >
                            [Piesă]{" "}
                            {s.title}
                            {s.artist_name ? ` - ${s.artist_name}` : ""}
                            {s.album_title
                              ? ` · ${releaseTypeLabel(s)}: ${s.album_title}`
                              : ""}
                          </button>
                        ))}
                      </div>
                    ) : null}

                    <button
                      type="button"
                      onClick={() => goToSearch(debouncedSearch)}
                      style={{ ...ui.buttonSmall, textAlign: "left", width: "100%" }}
                    >
                      Vezi toate rezultatele pentru "{debouncedSearch}"
                    </button>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </form>

        {mobileOpen ? (
          <nav id="mobile-navigation" className="navbar-mobile-menu open" aria-label="Meniu mobil">
            <div>
              <Link to="/albums" onClick={() => setMobileOpen(false)}>
                Albume
              </Link>
            </div>

            {isAuthenticated ? (
              <>
                <div>
                  <Link to="/dashboard" onClick={() => setMobileOpen(false)}>
                    Dashboard
                  </Link>
                </div>
                <div>
                  <Link
                    to="/recommendations"
                    onClick={() => setMobileOpen(false)}
                  >
                    Recomandări
                  </Link>
                </div>
                <div>
                  <Link
                    to="/notifications"
                    onClick={() => setMobileOpen(false)}
                  >
                    Notificări
                  </Link>
                </div>
                <div>
                  <Link to="/messages" onClick={() => setMobileOpen(false)}>
                    Mesaje
                  </Link>
                </div>
                <div>
                  <Link to="/activity" onClick={() => setMobileOpen(false)}>
                    Activitate
                  </Link>
                </div>
                <div>
                  <Link to="/suggest" onClick={() => setMobileOpen(false)}>
                    Propune
                  </Link>
                </div>
              </>
            ) : null}

            <div>
              <Link to="/lists" onClick={() => setMobileOpen(false)}>
                Liste
              </Link>
            </div>
            <div>
              <Link to="/following" onClick={() => setMobileOpen(false)}>
                Urmăriți
              </Link>
            </div>
          </nav>
        ) : null}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            marginLeft: "auto",
          }}
        >
          {isAuthenticated ? (
            <>
              <div
                style={{ display: "flex", flexDirection: "column", gap: "2px" }}
              >
                <div style={{ opacity: 0.9 }}>
                  Salut, {user?.username || "user"}
                </div>
                <div style={{ fontSize: "0.9em" }}>
                  <Link to="/profile">Profil</Link>
                </div>
              </div>
              <button onClick={handleLogout} style={ui.button}>
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login">Login</Link>
              <Link to="/register">Register</Link>
            </>
          )}
          <button
            type="button"
            onClick={toggleTheme}
            style={{
              ...ui.buttonSmall,
              padding: "4px 8px",
              fontSize: "0.8rem",
              lineHeight: 1.1,
            }}
          >
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </div>
    </div>
  );
}
