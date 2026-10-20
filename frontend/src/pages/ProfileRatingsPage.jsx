import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import ProfileNav from "../components/ProfileNav.jsx";
import PaginationControls from "../components/PaginationControls.jsx";
import { useAuth } from "../context/useAuth.js";
import { getMyRatings } from "../api/ratings.js";
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

function renderRatingStars(value) {
  const rating = Math.max(0, Math.min(5, Math.round(Number(value) || 0)));
  const emptyStars = 5 - rating;

  return (
    <span aria-label={`${rating} din 5 stele`} title={`${rating} din 5 stele`}>
      <span style={{ color: "#f59e0b", letterSpacing: "1px" }}>
        {"★".repeat(rating)}
        {"☆".repeat(emptyStars)}
      </span>
    </span>
  );
}

export default function ProfileRatingsPage() {
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken, logout } =
    useAuth();

  const [albums, setAlbums] = useState([]);
  const [songs, setSongs] = useState([]);
  const [albumPageInfo, setAlbumPageInfo] = useState({
    count: 0,
    next: null,
    previous: null,
  });
  const [songPageInfo, setSongPageInfo] = useState({
    count: 0,
    next: null,
    previous: null,
  });
  const [albumPage, setAlbumPage] = useState(1);
  const [songPage, setSongPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const itemsPerPage = 10;

  const albumTotalPages = useMemo(() => {
    return Math.max(
      1,
      Math.ceil((Number(albumPageInfo.count) || 0) / itemsPerPage),
    );
  }, [albumPageInfo.count, itemsPerPage]);

  const songTotalPages = useMemo(() => {
    return Math.max(
      1,
      Math.ceil((Number(songPageInfo.count) || 0) / itemsPerPage),
    );
  }, [itemsPerPage, songPageInfo.count]);

  useEffect(() => {
    let isCancelled = false;

    async function load() {
      if (!isAuthVerified || !accessToken) {
        setAlbums([]);
        setSongs([]);
        setIsLoading(false);
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const data = await getMyRatings({
          baseUrl,
          accessToken,
          albumPage,
          songPage,
        });
        if (isCancelled) return;
        const nextAlbums = Array.isArray(data?.albums?.results)
          ? data.albums.results
          : [];
        const nextSongs = Array.isArray(data?.songs?.results)
          ? data.songs.results
          : [];
        setAlbums(nextAlbums);
        setSongs(nextSongs);
        setAlbumPageInfo({
          count: Number(data?.albums?.count) || nextAlbums.length,
          next: data?.albums?.next || null,
          previous: data?.albums?.previous || null,
        });
        setSongPageInfo({
          count: Number(data?.songs?.count) || nextSongs.length,
          next: data?.songs?.next || null,
          previous: data?.songs?.previous || null,
        });
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled) {
          setAlbums([]);
          setSongs([]);
          setError(getErrorMessage(err, "Nu am putut încărca ratingurile."));
        }
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    load();

    return () => {
      isCancelled = true;
    };
  }, [accessToken, baseUrl, albumPage, isAuthVerified, logout, songPage]);

  useEffect(() => {
    const t = setTimeout(() => {
      setAlbumPage((prev) => Math.min(prev, albumTotalPages));
    }, 0);
    return () => clearTimeout(t);
  }, [albumTotalPages]);

  useEffect(() => {
    const t = setTimeout(() => {
      setSongPage((prev) => Math.min(prev, songTotalPages));
    }, 0);
    return () => clearTimeout(t);
  }, [songTotalPages]);

  if (!isAuthenticated) {
    return (
      <div>
        <ProfileNav />
        <div style={{ padding: "24px" }}>
          <h1 style={{ marginTop: 0 }}>Ratingurile mele</h1>
          <p>Trebuie să fii logat ca să vezi ratingurile tale.</p>
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
          <h1 style={{ marginTop: 0 }}>Ratingurile mele</h1>
          <p style={{ marginTop: "14px" }}>Se încarcă...</p>
        </div>
      </div>
    );
  }

  const hasAny =
    Number(albumPageInfo.count) > 0 || Number(songPageInfo.count) > 0;

  return (
    <div>
      <ProfileNav />
      <div style={{ padding: "24px" }}>
        <h1 style={{ marginTop: 0 }}>Ratingurile mele</h1>

        {isLoading ? <p>Se încarcă ratingurile...</p> : null}
        {error ? <p style={ui.errorText}>{error}</p> : null}

        {!isLoading && !error ? (
          hasAny ? (
            <div style={{ display: "grid", gap: "18px" }}>
              <section>
                <h3 style={{ marginTop: 0 }}>Albume</h3>
                {albums.length ? (
                  <ul style={{ paddingLeft: "18px" }}>
                    {albums.map((r) => (
                      <li key={r.id} style={{ marginBottom: "10px" }}>
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
                        <div style={{ opacity: 0.85, fontSize: "0.9em" }}>
                          {renderRatingStars(r.rating)} • Postat la:{" "}
                          {formatDateOnly(r.created_at)}
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>No album ratings yet</p>
                )}
                <PaginationControls
                  page={albumPage}
                  totalPages={albumTotalPages}
                  totalCount={albumPageInfo.count}
                  onPrev={() => setAlbumPage((prev) => Math.max(1, prev - 1))}
                  onNext={() =>
                    setAlbumPage((prev) => Math.min(albumTotalPages, prev + 1))
                  }
                />
              </section>

              <section>
                <h3 style={{ marginTop: 0 }}>Melodii</h3>
                {songs.length ? (
                  <ul style={{ paddingLeft: "18px" }}>
                    {songs.map((r) => (
                      <li key={r.id} style={{ marginBottom: "10px" }}>
                        <div>
                          <strong>
                            <Link to={`/songs/${r.song_slug}`}>
                              {r.song_title}
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
                        <div style={{ opacity: 0.85, fontSize: "0.9em" }}>
                          {renderRatingStars(r.rating)} • Postat la:{" "}
                          {formatDateOnly(r.created_at)}
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>No song ratings yet</p>
                )}
                <PaginationControls
                  page={songPage}
                  totalPages={songTotalPages}
                  totalCount={songPageInfo.count}
                  onPrev={() => setSongPage((prev) => Math.max(1, prev - 1))}
                  onNext={() =>
                    setSongPage((prev) => Math.min(songTotalPages, prev + 1))
                  }
                />
              </section>
            </div>
          ) : (
            <p>No ratings yet</p>
          )
        ) : null}
      </div>
    </div>
  );
}
