import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

import ProfileNav from "../components/ProfileNav.jsx";
import PaginationControls from "../components/PaginationControls.jsx";
import { getMyWantToListen } from "../api/watchlist.js";
import { markAlbumListened } from "../api/listens.js";
import { useAuth } from "../context/useAuth.js";
import { useNotice } from "../context/useNotice.js";
import { ui } from "../ui/ui.js";
import { prefetchAlbum } from "../query/prefetchAlbum.js";

export default function ProfileWantToListenPage() {
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken, logout } =
    useAuth();
  const { notify } = useNotice();
  const queryClient = useQueryClient();

  const [items, setItems] = useState([]);
  const [selectedAlbumIds, setSelectedAlbumIds] = useState(() => new Set());
  const [isBulkWorking, setIsBulkWorking] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const itemsPerPage = 10;
  const [pageInfo, setPageInfo] = useState({
    count: 0,
    next: null,
    previous: null,
  });

  const canLoad = useMemo(() => {
    return Boolean(isAuthVerified && accessToken);
  }, [isAuthVerified, accessToken]);

  const totalPages = useMemo(() => {
    return Math.max(1, Math.ceil((Number(pageInfo.count) || 0) / itemsPerPage));
  }, [itemsPerPage, pageInfo.count]);

  const load = useCallback(async () => {
    if (!canLoad) {
      setItems([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await getMyWantToListen({
        baseUrl,
        accessToken,
        page,
      });
      const nextItems = Array.isArray(data?.results)
        ? data.results
        : Array.isArray(data)
          ? data
          : [];
      setItems(nextItems);
      setPageInfo({
        count: Number(data?.count) || nextItems.length,
        next: data?.next || null,
        previous: data?.previous || null,
      });
      setSelectedAlbumIds(new Set());
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut încărca lista Want To Listen.");
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, baseUrl, canLoad, logout, page]);

  const selectedCount = selectedAlbumIds.size;

  async function bulkMarkListened() {
    if (!canLoad) return;
    if (!selectedAlbumIds.size) return;

    setIsBulkWorking(true);

    let ok = 0;
    let fail = 0;
    for (const albumId of selectedAlbumIds) {
      try {
        await markAlbumListened({ baseUrl, accessToken, albumId });
        ok += 1;
      } catch (err) {
        console.error(err);
        fail += 1;
      }
    }

    if (ok) {
      notify({
        type: "success",
        message: `Marcat ca ascultate: ${ok}${fail ? ` (eșuate: ${fail})` : ""}.`,
      });
    } else {
      notify({ type: "error", message: "Nu am putut marca albumele." });
    }

    setIsBulkWorking(false);
    await load();
  }

  useEffect(() => {
    if (!canLoad) return;
    void load();
  }, [canLoad, load]);

  useEffect(() => {
    setPage((prev) => Math.min(prev, totalPages));
  }, [totalPages]);

  if (!isAuthenticated) {
    return (
      <div>
        <ProfileNav />
        <div style={ui.container}>
          <h1 style={{ marginTop: 0 }}>Want To Listen</h1>
          <p>Trebuie să fii logat ca să vezi watchlist-ul.</p>
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
          <h1 style={{ marginTop: 0 }}>Want To Listen</h1>
          <p style={{ marginTop: "14px" }}>Se încarcă...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <ProfileNav />
      <div style={ui.container}>
        <h1 style={{ marginTop: 0 }}>Want To Listen</h1>

        {!error ? (
          <p style={{ marginTop: "10px", opacity: 0.9 }}>
            Albume în listă:{" "}
            <strong>{Array.isArray(items) ? items.length : 0}</strong>
          </p>
        ) : null}

        {isLoading ? <p style={{ marginTop: "14px" }}>Se încarcă...</p> : null}
        {error ? (
          <p style={{ ...ui.errorText, marginTop: "14px" }} role="alert">
            {error}
          </p>
        ) : null}

        {!isLoading && !error ? (
          items.length ? (
            <div style={{ ...ui.card, marginTop: "12px" }}>
              {selectedCount ? (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 12,
                    paddingBottom: 10,
                    marginBottom: 10,
                    borderBottom: `1px solid ${ui.colors.border}`,
                  }}
                >
                  <div style={{ opacity: 0.9 }}>
                    Selectate: <strong>{selectedCount}</strong>
                  </div>
                  <button
                    type="button"
                    style={ui.button}
                    onClick={bulkMarkListened}
                    disabled={isBulkWorking}
                  >
                    Marchează ca ascultate
                  </button>
                </div>
              ) : null}

              <ul style={{ paddingLeft: "18px", margin: 0 }}>
                {items.map((it) => {
                  const id = it?.id;
                  const albumId = it?.album_id;
                  const albumSlug = String(it?.album_slug || "").trim();
                  const albumTitle = String(it?.album_title || "Album");
                  const artistSlug = String(it?.artist_slug || "").trim();
                  const artistName = String(it?.artist_name || "Artist");

                  if (!id || !albumId) return null;

                  const checked = selectedAlbumIds.has(albumId);

                  return (
                    <li key={id} style={{ margin: "10px 0" }}>
                      <div
                        style={{
                          display: "flex",
                          gap: 10,
                          alignItems: "flex-start",
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          disabled={isBulkWorking}
                          onChange={(e) => {
                            const nextChecked = e.target.checked;
                            setSelectedAlbumIds((prev) => {
                              const next = new Set(prev);
                              if (nextChecked) next.add(albumId);
                              else next.delete(albumId);
                              return next;
                            });
                          }}
                          style={{ marginTop: 3 }}
                        />

                        <div>
                          <strong>
                            {albumSlug ? (
                              <Link
                                to={`/albums/${encodeURIComponent(albumSlug)}`}
                                onMouseEnter={() =>
                                  prefetchAlbum({
                                    queryClient,
                                    baseUrl,
                                    slug: albumSlug,
                                    accessToken,
                                    isAuthVerified,
                                  })
                                }
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
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : (
            <p style={{ marginTop: "12px" }}>Nu ai adăugat nimic încă.</p>
          )
        ) : null}

        <PaginationControls
          page={page}
          totalPages={totalPages}
          totalCount={pageInfo.count}
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
