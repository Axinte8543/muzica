import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import ProfileNav from "../components/ProfileNav.jsx";
import PaginationControls from "../components/PaginationControls.jsx";
import { useAuth } from "../context/useAuth.js";
import { getMyListens, getMyListensStats } from "../api/listens.js";
import { ui } from "../ui/ui.js";

export default function ProfileListensPage() {
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken, logout } =
    useAuth();

  const [listens, setListens] = useState([]);
  const [stats, setStats] = useState(null);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const itemsPerPage = 10;

  const canLoad = useMemo(() => {
    return Boolean(isAuthVerified && accessToken);
  }, [isAuthVerified, accessToken]);

  const totalPages = useMemo(() => {
    return Math.max(1, Math.ceil(listens.length / itemsPerPage));
  }, [itemsPerPage, listens.length]);

  const pageItems = useMemo(() => {
    const start = (page - 1) * itemsPerPage;
    return listens.slice(start, start + itemsPerPage);
  }, [itemsPerPage, listens, page]);

  const load = useCallback(async () => {
    if (!canLoad) {
      setListens([]);
      setStats(null);
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const [listensData, statsData] = await Promise.all([
        getMyListens({ baseUrl, accessToken, limit: 100 }),
        getMyListensStats({ baseUrl, accessToken }),
      ]);
      setListens(Array.isArray(listensData) ? listensData : []);
      setStats(statsData && typeof statsData === "object" ? statsData : null);
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut încărca albumele ascultate.");
      setListens([]);
      setStats(null);
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, baseUrl, canLoad, logout]);

  useEffect(() => {
    if (!canLoad) return;
    const t = setTimeout(() => {
      void load();
    }, 0);
    return () => clearTimeout(t);
  }, [canLoad, load]);

  useEffect(() => {
    const t = setTimeout(() => {
      setPage((prev) => Math.min(prev, totalPages));
    }, 0);
    return () => clearTimeout(t);
  }, [totalPages]);

  if (!isAuthenticated) {
    return (
      <div>
        <ProfileNav />
        <div style={ui.container}>
          <h1 style={{ marginTop: 0 }}>Albume ascultate</h1>
          <p>Trebuie să fii logat ca să vezi albumele ascultate.</p>
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
        <div style={ui.container}>
          <h1 style={{ marginTop: 0 }}>Albume ascultate</h1>
          <p style={{ marginTop: "14px" }}>Se încarcă...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <ProfileNav />
      <div style={ui.container}>
        <h1 style={{ marginTop: 0 }}>Albume ascultate</h1>

        {!error ? (
          <p style={{ marginTop: "10px", opacity: 0.9 }}>
            Total albume ascultate:{" "}
            <strong>{stats?.total_albums ?? "—"}</strong> • Anul acesta:{" "}
            <strong>{stats?.year_albums ?? "—"}</strong>
          </p>
        ) : null}

        {isLoading ? <p style={{ marginTop: "14px" }}>Se încarcă...</p> : null}
        {error ? (
          <p style={{ ...ui.errorText, marginTop: "14px" }} role="alert">
            {error}
          </p>
        ) : null}

        {!isLoading && !error ? (
          listens.length ? (
            <div style={{ ...ui.card, marginTop: "12px" }}>
              <ul style={{ paddingLeft: "18px", margin: 0 }}>
                {pageItems.map((l) => {
                  const id = l?.id;
                  const albumSlug = String(l?.album_slug || "").trim();
                  const albumTitle = String(l?.album_title || "Album");
                  const artistSlug = String(l?.artist_slug || "").trim();
                  const artistName = String(l?.artist_name || "Artist");
                  const listenedAt = l?.listened_at;
                  const listenedDate = l?.listened_date;

                  if (!id) return null;

                  return (
                    <li key={id} style={{ margin: "10px 0" }}>
                      <div>
                        <strong>
                          {albumSlug ? (
                            <Link
                              to={`/albums/${encodeURIComponent(albumSlug)}`}
                            >
                              {albumTitle}
                            </Link>
                          ) : (
                            <span>{albumTitle}</span>
                          )}
                        </strong>
                        <span style={{ opacity: 0.9 }}>
                          {" "}
                          —{" "}
                          {artistSlug ? (
                            <Link
                              to={`/artists/${encodeURIComponent(artistSlug)}`}
                            >
                              {artistName}
                            </Link>
                          ) : (
                            <span>{artistName}</span>
                          )}
                        </span>
                      </div>
                      <div style={{ marginTop: "4px", opacity: 0.85 }}>
                        Ascultat: {listenedDate || listenedAt || ""}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : (
            <p style={{ marginTop: "12px" }}>Nu ai albume ascultate încă.</p>
          )
        ) : null}

        <PaginationControls
          page={page}
          totalPages={totalPages}
          totalCount={listens.length}
          onPrev={() => setPage((prev) => Math.max(1, prev - 1))}
          onNext={() => setPage((prev) => Math.min(totalPages, prev + 1))}
        />

        {!isLoading && !error ? (
          <div style={{ marginTop: "16px" }}>
            <button type="button" style={ui.button} onClick={load}>
              Reîncarcă
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
