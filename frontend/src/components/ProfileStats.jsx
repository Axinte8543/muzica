import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getMyProfileStats } from "../api/profileStats.js";
import {
  getMyPrivacySettings,
  updateMyPrivacySettings,
} from "../api/privacy.js";
import { setMyFavoriteAlbums } from "../api/favoriteAlbums.js";
import { setMyFavoriteSongs } from "../api/favoriteSongs.js";
import { exportMyDataBlob } from "../api/exportData.js";
import { importMyDataCsv } from "../api/importData.js";
import { getMyStreak, getWeeklyChallenges } from "../api/gamification.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

function formatAverage(value) {
  if (value === null || value === undefined) return "—";
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  return num.toFixed(1);
}

function favoriteSlotsFromStats(stats) {
  const slots = [null, null, null, null];
  const fav = Array.isArray(stats?.favorite_albums)
    ? stats.favorite_albums
    : [];
  fav.forEach((item) => {
    const pos = Number(item?.position);
    if (!Number.isFinite(pos) || pos < 1 || pos > 4) return;
    const albumId =
      item?.album_id === null || item?.album_id === undefined
        ? null
        : Number(item.album_id);
    slots[pos - 1] = Number.isFinite(albumId) ? albumId : null;
  });
  return slots;
}

function favoriteSongSlotsFromStats(stats) {
  const slots = [null, null, null, null];
  const fav = Array.isArray(stats?.favorite_songs) ? stats.favorite_songs : [];
  fav.forEach((item) => {
    const pos = Number(item?.position);
    if (!Number.isFinite(pos) || pos < 1 || pos > 4) return;
    const songId =
      item?.song_id === null || item?.song_id === undefined
        ? null
        : Number(item.song_id);
    slots[pos - 1] = Number.isFinite(songId) ? songId : null;
  });
  return slots;
}

export default function ProfileStats() {
  const { baseUrl, isAuthVerified, accessToken, logout } = useAuth();

  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const [isSavingFavorites, setIsSavingFavorites] = useState(false);
  const [favoritesError, setFavoritesError] = useState(null);

  const [privacyPublicLists, setPrivacyPublicLists] = useState(true);
  const [privacyPublicActivity, setPrivacyPublicActivity] = useState(true);
  const [privacyPublicCompatibility, setPrivacyPublicCompatibility] =
    useState(true);
  const [isLoadingPrivacy, setIsLoadingPrivacy] = useState(false);
  const [isSavingPrivacy, setIsSavingPrivacy] = useState(false);
  const [privacyError, setPrivacyError] = useState(null);
  const [privacySavedAt, setPrivacySavedAt] = useState(null);

  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState(null);
  const [exportSavedAt, setExportSavedAt] = useState(null);

  const [importResource, setImportResource] = useState("ratings");
  const [importFile, setImportFile] = useState(null);
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState(null);
  const [importResult, setImportResult] = useState(null);

  const [streak, setStreak] = useState(null);
  const [weeklyChallenges, setWeeklyChallenges] = useState(null);
  const [isLoadingGami, setIsLoadingGami] = useState(false);
  const [gamiError, setGamiError] = useState(null);

  const canLoad = useMemo(() => {
    return Boolean(isAuthVerified && accessToken);
  }, [isAuthVerified, accessToken]);

  useEffect(() => {
    let isCancelled = false;

    async function load() {
      if (!canLoad) {
        setStats(null);
        setIsLoading(false);
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const data = await getMyProfileStats({ baseUrl, accessToken });
        if (!isCancelled)
          setStats(data && typeof data === "object" ? data : null);
      } catch (err) {
        const status = err?.response?.status;
        if (status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled) setError("Nu am putut încărca statisticile.");
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    load();

    return () => {
      isCancelled = true;
    };
  }, [canLoad, baseUrl, accessToken, logout]);

  useEffect(() => {
    let isCancelled = false;

    async function loadGamification() {
      if (!canLoad) {
        if (!isCancelled) {
          setStreak(null);
          setWeeklyChallenges(null);
          setIsLoadingGami(false);
          setGamiError(null);
        }
        return;
      }

      if (!isCancelled) {
        setIsLoadingGami(true);
        setGamiError(null);
      }

      try {
        const [streakData, weeklyData] = await Promise.all([
          getMyStreak(),
          getWeeklyChallenges(),
        ]);

        if (!isCancelled) {
          setStreak(
            streakData && typeof streakData === "object" ? streakData : null,
          );
          setWeeklyChallenges(
            weeklyData && typeof weeklyData === "object" ? weeklyData : null,
          );
        }
      } catch (err) {
        const status = err?.response?.status;
        if (status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled) setGamiError("Nu am putut încărca provocările.");
      } finally {
        if (!isCancelled) setIsLoadingGami(false);
      }
    }

    loadGamification();

    return () => {
      isCancelled = true;
    };
  }, [canLoad, logout]);

  useEffect(() => {
    let isCancelled = false;

    async function loadPrivacy() {
      if (!canLoad) {
        if (!isCancelled) {
          setIsLoadingPrivacy(false);
          setPrivacyError(null);
          setPrivacyPublicLists(true);
          setPrivacyPublicActivity(true);
          setPrivacyPublicCompatibility(true);
          setPrivacySavedAt(null);
        }
        return;
      }

      if (!isCancelled) {
        setIsLoadingPrivacy(true);
        setPrivacyError(null);
      }

      try {
        const data = await getMyPrivacySettings({ baseUrl, accessToken });
        const nextPublicLists = Boolean(data?.public_lists ?? true);
        const nextPublicActivity = Boolean(data?.public_activity ?? true);
        const nextPublicCompatibility = Boolean(
          data?.public_compatibility ?? true,
        );
        if (!isCancelled) {
          setPrivacyPublicLists(nextPublicLists);
          setPrivacyPublicActivity(nextPublicActivity);
          setPrivacyPublicCompatibility(nextPublicCompatibility);
          setPrivacySavedAt(data?.updated_at || null);
        }
      } catch (err) {
        const status = err?.response?.status;
        if (status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled)
          setPrivacyError("Nu am putut încărca setările de confidențialitate.");
      } finally {
        if (!isCancelled) setIsLoadingPrivacy(false);
      }
    }

    void loadPrivacy();

    return () => {
      isCancelled = true;
    };
  }, [canLoad, baseUrl, accessToken, logout]);

  async function savePrivacy() {
    if (!canLoad || isSavingPrivacy) return;

    setIsSavingPrivacy(true);
    setPrivacyError(null);
    try {
      const data = await updateMyPrivacySettings({
        baseUrl,
        accessToken,
        publicLists: privacyPublicLists,
        publicActivity: privacyPublicActivity,
        publicCompatibility: privacyPublicCompatibility,
      });
      setPrivacySavedAt(data?.updated_at || null);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        logout();
        return;
      }
      console.error(err);
      setPrivacyError("Nu am putut salva setările.");
    } finally {
      setIsSavingPrivacy(false);
    }
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  async function exportJson() {
    if (!canLoad || isExporting) return;
    setIsExporting(true);
    setExportError(null);
    try {
      const blob = await exportMyDataBlob({
        baseUrl,
        accessToken,
        format: "json",
      });
      const filename = `export_${new Date().toISOString().slice(0, 10)}.json`;
      downloadBlob(blob, filename);
      setExportSavedAt(new Date().toISOString());
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        logout();
        return;
      }
      console.error(err);
      setExportError("Nu am putut exporta datele.");
    } finally {
      setIsExporting(false);
    }
  }

  async function exportCsv(resource) {
    if (!canLoad || isExporting) return;
    const res = String(resource || "").trim();
    if (!res) return;

    setIsExporting(true);
    setExportError(null);
    try {
      const blob = await exportMyDataBlob({
        baseUrl,
        accessToken,
        format: "csv",
        resource: res,
      });
      const filename = `export_${res}_${new Date().toISOString().slice(0, 10)}.csv`;
      downloadBlob(blob, filename);
      setExportSavedAt(new Date().toISOString());
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        logout();
        return;
      }
      console.error(err);
      setExportError("Nu am putut exporta CSV.");
    } finally {
      setIsExporting(false);
    }
  }

  async function importCsv() {
    if (!canLoad || isImporting) return;
    if (!importFile) {
      setImportError("Alege un fișier CSV.");
      return;
    }

    setIsImporting(true);
    setImportError(null);
    setImportResult(null);
    try {
      const data = await importMyDataCsv({
        resource: importResource,
        file: importFile,
      });
      setImportResult(data && typeof data === "object" ? data : null);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        logout();
        return;
      }
      console.error(err);
      const detail = err?.response?.data?.detail;
      setImportError(detail ? String(detail) : "Nu am putut importa CSV.");
    } finally {
      setIsImporting(false);
    }
  }

  if (isLoading) {
    return <p>Se încarcă...</p>;
  }

  if (error) {
    return (
      <p style={ui.errorText} role="alert">
        {error}
      </p>
    );
  }

  const favoriteArtist = stats?.favorite_artist || "—";
  const totalRatings = Number.isFinite(Number(stats?.total_ratings))
    ? Number(stats.total_ratings)
    : 0;
  const avgGiven = formatAverage(stats?.average_rating_given);

  const ratingDistribution = Array.isArray(stats?.ratings_distribution)
    ? stats.ratings_distribution
    : [];
  const activity =
    stats?.activity && typeof stats.activity === "object"
      ? stats.activity
      : null;

  const favoriteAlbums = Array.isArray(stats?.favorite_albums)
    ? stats.favorite_albums
    : [];
  const favoriteSongs = Array.isArray(stats?.favorite_songs)
    ? stats.favorite_songs
    : [];

  const badges = Array.isArray(stats?.badges) ? stats.badges : [];

  const listenStreak = Number.isFinite(Number(streak?.listen_streak_days))
    ? Number(streak.listen_streak_days)
    : 0;
  const ratingStreak = Number.isFinite(Number(streak?.rating_streak_days))
    ? Number(streak.rating_streak_days)
    : 0;
  const activityStreak = Number.isFinite(Number(streak?.activity_streak_days))
    ? Number(streak.activity_streak_days)
    : 0;
  const challenges = Array.isArray(weeklyChallenges?.challenges)
    ? weeklyChallenges.challenges
    : [];

  async function clearFavoriteSlot(position) {
    if (!canLoad || isSavingFavorites) return;
    const currentSlots = favoriteSlotsFromStats(stats);
    const idx = Number(position) - 1;
    if (!Number.isFinite(idx) || idx < 0 || idx > 3) return;
    currentSlots[idx] = null;

    setIsSavingFavorites(true);
    setFavoritesError(null);
    try {
      const data = await setMyFavoriteAlbums({
        baseUrl,
        accessToken,
        slots: currentSlots,
      });
      const nextFav =
        data && typeof data === "object" && Array.isArray(data.favorite_albums)
          ? data.favorite_albums
          : [];
      setStats((prev) => (prev ? { ...prev, favorite_albums: nextFav } : prev));
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        logout();
        return;
      }
      console.error(err);
      setFavoritesError("Nu am putut salva albumele favorite.");
    } finally {
      setIsSavingFavorites(false);
    }
  }

  async function clearFavoriteSongSlot(position) {
    if (!canLoad || isSavingFavorites) return;
    const currentSlots = favoriteSongSlotsFromStats(stats);
    const idx = Number(position) - 1;
    if (!Number.isFinite(idx) || idx < 0 || idx > 3) return;
    currentSlots[idx] = null;

    setIsSavingFavorites(true);
    setFavoritesError(null);
    try {
      const data = await setMyFavoriteSongs({
        baseUrl,
        accessToken,
        slots: currentSlots,
      });
      const nextFav =
        data && typeof data === "object" && Array.isArray(data.favorite_songs)
          ? data.favorite_songs
          : [];
      setStats((prev) => (prev ? { ...prev, favorite_songs: nextFav } : prev));
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        logout();
        return;
      }
      console.error(err);
      setFavoritesError("Nu am putut salva melodiile favorite.");
    } finally {
      setIsSavingFavorites(false);
    }
  }

  const reviewsWritten = Number.isFinite(Number(activity?.reviews_written))
    ? Number(activity.reviews_written)
    : 0;
  const albumsRated = Number.isFinite(Number(activity?.albums_rated))
    ? Number(activity.albums_rated)
    : totalRatings;
  const artistsFollowed = Number.isFinite(Number(activity?.artists_followed))
    ? Number(activity.artists_followed)
    : 0;
  const listsCreated = Number.isFinite(Number(activity?.lists_created))
    ? Number(activity.lists_created)
    : 0;

  return (
    <div style={{ display: "grid", gap: "16px", marginTop: "12px" }}>
      <div style={{ ...ui.card, maxWidth: "720px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: "12px",
            alignItems: "baseline",
          }}
        >
          <div style={{ fontWeight: 700 }}>Albumele mele favorite (Top 4)</div>
          <Link to="/albums" style={{ fontSize: "14px" }}>
            Vezi albume
          </Link>
        </div>

        <p style={{ marginTop: "8px", opacity: 0.85 }}>
          Apasă pe „Alege” ca să selectezi un album pentru slot.
        </p>

        {favoritesError ? (
          <p style={{ ...ui.errorText, marginTop: "8px" }} role="alert">
            {favoritesError}
          </p>
        ) : null}

        <div style={{ display: "grid", gap: "10px", marginTop: "10px" }}>
          {[1, 2, 3, 4].map((pos) => {
            const item = favoriteAlbums.find(
              (x) => Number(x?.position) === pos,
            );
            const hasAlbum = Boolean(item?.album_slug && item?.album_title);

            return (
              <div
                key={pos}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "12px",
                  padding: "8px 10px",
                  border: `1px solid ${ui.colors.border}`,
                  borderRadius: "8px",
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 700 }}>#{pos}</div>
                  <div style={{ marginTop: "2px" }}>
                    {hasAlbum ? (
                      <Link to={`/albums/${item.album_slug}`}>
                        {item.album_title}
                      </Link>
                    ) : (
                      <span style={{ opacity: 0.7 }}>Neales</span>
                    )}
                    {hasAlbum && item?.artist_slug ? (
                      <span style={{ opacity: 0.85 }}>
                        {" "}
                        —{" "}
                        <Link to={`/artists/${item.artist_slug}`}>
                          {item.artist_name}
                        </Link>
                      </span>
                    ) : null}
                  </div>
                </div>

                <div style={{ display: "flex", gap: "8px", flexShrink: 0 }}>
                  <Link
                    to={`/albums?pickFavoriteSlot=${pos}`}
                    style={{
                      ...ui.buttonSmall,
                      display: "inline-block",
                      textDecoration: "none",
                      color: "inherit",
                    }}
                  >
                    Alege
                  </Link>
                  <button
                    type="button"
                    onClick={() => clearFavoriteSlot(pos)}
                    disabled={isSavingFavorites}
                    style={ui.buttonSmall}
                  >
                    Șterge
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ ...ui.card, maxWidth: "720px" }}>
        <div style={{ fontWeight: 700 }}>Melodiile mele favorite (Top 4)</div>

        <p style={{ marginTop: "8px", opacity: 0.85 }}>
          Apasă pe „Alege” ca să selectezi o melodie pentru slot.
        </p>

        {favoritesError ? (
          <p style={{ ...ui.errorText, marginTop: "8px" }} role="alert">
            {favoritesError}
          </p>
        ) : null}

        <div style={{ display: "grid", gap: "10px", marginTop: "10px" }}>
          {[1, 2, 3, 4].map((pos) => {
            const item = favoriteSongs.find((x) => Number(x?.position) === pos);
            const hasSong = Boolean(item?.song_slug && item?.song_title);

            return (
              <div
                key={pos}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "12px",
                  padding: "8px 10px",
                  border: `1px solid ${ui.colors.border}`,
                  borderRadius: "8px",
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 700 }}>#{pos}</div>
                  <div style={{ marginTop: "2px" }}>
                    {hasSong ? (
                      <Link to={`/songs/${item.song_slug}`}>
                        {item.song_title}
                      </Link>
                    ) : (
                      <span style={{ opacity: 0.7 }}>Neales</span>
                    )}
                    {hasSong && item?.artist_slug ? (
                      <span style={{ opacity: 0.85 }}>
                        {" "}
                        —{" "}
                        <Link to={`/artists/${item.artist_slug}`}>
                          {item.artist_name}
                        </Link>
                      </span>
                    ) : null}
                    {hasSong && item?.album_slug ? (
                      <span style={{ opacity: 0.85 }}>
                        {" "}
                        —{" "}
                        <Link to={`/albums/${item.album_slug}`}>
                          {item.album_title}
                        </Link>
                      </span>
                    ) : null}
                  </div>
                </div>

                <div style={{ display: "flex", gap: "8px", flexShrink: 0 }}>
                  <Link
                    to={`/albums?pickFavoriteSongSlot=${pos}`}
                    style={{
                      ...ui.buttonSmall,
                      display: "inline-block",
                      textDecoration: "none",
                      color: "inherit",
                    }}
                  >
                    Alege
                  </Link>
                  <button
                    type="button"
                    onClick={() => clearFavoriteSongSlot(pos)}
                    disabled={isSavingFavorites}
                    style={ui.buttonSmall}
                  >
                    Șterge
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ ...ui.card, maxWidth: "520px" }}>
        <div>
          <strong>Favorite artist:</strong> {favoriteArtist}
        </div>
        <div style={{ marginTop: "8px" }}>
          <strong>Albums rated:</strong> {totalRatings}
        </div>
        <div style={{ marginTop: "8px" }}>
          <strong>Average rating given:</strong> {avgGiven}
        </div>
      </div>

      <div style={{ ...ui.card, maxWidth: "520px" }}>
        <div style={{ fontWeight: 700 }}>Distribuția ratingurilor</div>
        {ratingDistribution.length === 0 ? (
          <p style={{ marginTop: "10px" }}>Nu există date.</p>
        ) : (
          <ul style={{ marginTop: "10px", paddingLeft: "20px" }}>
            {ratingDistribution.map((b) => (
              <li key={b.stars} style={{ marginBottom: "6px" }}>
                {b.stars} stars – {b.count}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div style={{ ...ui.card, maxWidth: "520px" }}>
        <div style={{ fontWeight: 700 }}>Badges</div>
        {badges.length === 0 ? (
          <p style={{ marginTop: "10px", opacity: 0.85 }}>Nu există încă.</p>
        ) : (
          <div style={{ marginTop: "10px", display: "grid", gap: "8px" }}>
            {badges.map((b) => (
              <div
                key={b.key}
                style={{
                  padding: "8px 10px",
                  border: `1px solid ${ui.colors.border}`,
                  borderRadius: "8px",
                  opacity: b.unlocked ? 1 : 0.65,
                }}
              >
                <div style={{ fontWeight: 700 }}>
                  {b.title}
                  <span style={{ marginLeft: "8px", opacity: 0.85 }}>
                    ({b.unlocked ? "Unlocked" : "Locked"})
                  </span>
                </div>
                <div style={{ marginTop: "2px", opacity: 0.85 }}>
                  {b.description}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ ...ui.card, maxWidth: "520px" }}>
        <div style={{ fontWeight: 700 }}>Activitate utilizator</div>
        <ul style={{ marginTop: "10px", paddingLeft: "20px" }}>
          <li style={{ marginBottom: "6px" }}>
            Reviews written: {reviewsWritten}
          </li>
          <li style={{ marginBottom: "6px" }}>Albums rated: {albumsRated}</li>
          <li style={{ marginBottom: "6px" }}>
            Artists followed: {artistsFollowed}
          </li>
          <li style={{ marginBottom: "6px" }}>Lists created: {listsCreated}</li>
        </ul>
      </div>

      <div style={{ ...ui.card, maxWidth: "520px" }}>
        <div style={{ fontWeight: 700 }}>Provocări & Streak</div>

        {isLoadingGami ? (
          <p style={{ marginTop: "10px" }}>Se încarcă...</p>
        ) : null}
        {gamiError ? (
          <p style={{ ...ui.errorText, marginTop: "10px" }} role="alert">
            {gamiError}
          </p>
        ) : null}

        <div style={{ marginTop: "10px", display: "grid", gap: "10px" }}>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <div style={{ opacity: 0.9 }}>
              Streak activitate: <b>{activityStreak}</b> zile
            </div>
            <div style={{ opacity: 0.8 }}>
              (Ascultări: {listenStreak}, Ratinguri: {ratingStreak})
            </div>
          </div>

          {challenges.length ? (
            <div style={{ display: "grid", gap: "8px" }}>
              {challenges.map((c) => (
                <div
                  key={c.key}
                  style={{
                    padding: "8px 10px",
                    border: c.completed
                      ? `1px solid rgba(34, 197, 94, 0.35)`
                      : `1px solid ${ui.colors.border}`,
                    borderRadius: "8px",
                  }}
                >
                  <div style={{ fontWeight: 700 }}>
                    {c.title} {c.completed ? "✓" : ""}
                  </div>
                  <div style={{ marginTop: "2px", opacity: 0.85 }}>
                    {c.description}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      <div style={{ ...ui.card, maxWidth: "520px" }}>
        <div style={{ fontWeight: 700 }}>Confidențialitate & Export</div>

        {isLoadingPrivacy ? (
          <p style={{ marginTop: "10px" }}>Se încarcă setările...</p>
        ) : null}

        {privacyError ? (
          <p style={{ ...ui.errorText, marginTop: "10px" }} role="alert">
            {privacyError}
          </p>
        ) : null}

        <div style={{ display: "grid", gap: "10px", marginTop: "10px" }}>
          <label style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={privacyPublicLists}
              disabled={isSavingPrivacy || isLoadingPrivacy}
              onChange={(e) => setPrivacyPublicLists(e.target.checked)}
            />
            Liste publice (apar în public / pe albume)
          </label>

          <label style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={privacyPublicActivity}
              disabled={isSavingPrivacy || isLoadingPrivacy}
              onChange={(e) => setPrivacyPublicActivity(e.target.checked)}
            />
            Activitate publică (apare în feed / profil public)
          </label>

          <label style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={privacyPublicCompatibility}
              disabled={isSavingPrivacy || isLoadingPrivacy}
              onChange={(e) => setPrivacyPublicCompatibility(e.target.checked)}
            />
            Compatibilitate publică (apare în utilizatori similari / profil)
          </label>
        </div>

        <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
          <button
            type="button"
            onClick={savePrivacy}
            disabled={isSavingPrivacy || isLoadingPrivacy}
            style={ui.buttonSmall}
          >
            {isSavingPrivacy ? "Salvez..." : "Salvează"}
          </button>
          {privacySavedAt ? (
            <span style={{ opacity: 0.8, alignSelf: "center" }}>
              Actualizat: {String(privacySavedAt)}
            </span>
          ) : null}
        </div>

        <div
          style={{
            marginTop: "14px",
            paddingTop: "12px",
            borderTop: `1px solid ${ui.colors.border}`,
          }}
        >
          {exportError ? (
            <p style={{ ...ui.errorText, marginTop: 0 }} role="alert">
              {exportError}
            </p>
          ) : null}

          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
            <button
              type="button"
              onClick={exportJson}
              disabled={isExporting}
              style={ui.buttonSmall}
            >
              Export JSON
            </button>
            <button
              type="button"
              onClick={() => exportCsv("listens")}
              disabled={isExporting}
              style={ui.buttonSmall}
            >
              CSV Listens
            </button>
            <button
              type="button"
              onClick={() => exportCsv("ratings")}
              disabled={isExporting}
              style={ui.buttonSmall}
            >
              CSV Ratings
            </button>
            <button
              type="button"
              onClick={() => exportCsv("reviews")}
              disabled={isExporting}
              style={ui.buttonSmall}
            >
              CSV Reviews
            </button>
          </div>

          {exportSavedAt ? (
            <div style={{ marginTop: "10px", opacity: 0.8 }}>
              Ultimul export: {String(exportSavedAt)}
            </div>
          ) : null}
        </div>

        <div
          style={{
            marginTop: "14px",
            paddingTop: "12px",
            borderTop: `1px solid ${ui.colors.border}`,
          }}
        >
          <div style={{ fontWeight: 700 }}>Import CSV</div>
          <div style={{ marginTop: "10px", display: "grid", gap: "10px" }}>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              Tip
              <select
                value={importResource}
                onChange={(e) => setImportResource(e.target.value)}
                style={ui.input}
              >
                <option value="ratings">Ratings</option>
                <option value="listens">Listens</option>
              </select>
            </label>

            <label style={{ display: "grid", gap: 6 }}>
              Fișier CSV
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => setImportFile(e.target.files?.[0] || null)}
              />
            </label>

            {importError ? (
              <p style={{ ...ui.errorText, margin: 0 }} role="alert">
                {importError}
              </p>
            ) : null}

            <div style={{ display: "flex", gap: "8px" }}>
              <button
                type="button"
                onClick={importCsv}
                disabled={isImporting}
                style={ui.buttonSmall}
              >
                {isImporting ? "Import..." : "Import CSV"}
              </button>
              <div style={{ opacity: 0.85, alignSelf: "center" }}>
                Folosește export-ul CSV ca șablon.
              </div>
            </div>

            {importResult ? (
              <div style={{ opacity: 0.9 }}>
                Import OK: create {String(importResult.created ?? 0)}, update{" "}
                {String(importResult.updated ?? 0)}, skip{" "}
                {String(importResult.skipped ?? 0)}.
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
