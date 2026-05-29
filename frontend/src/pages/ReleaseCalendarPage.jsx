import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  getNotificationPreferences,
  getReleaseCalendar,
  updateNotificationPreferences,
} from "../api/notifications.js";
import { useAuth } from "../context/useAuth.js";
import { useNotice } from "../context/useNotice.js";
import { ui } from "../ui/ui.js";

function formatMonth(d) {
  const dt = d instanceof Date ? d : new Date();
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

function toRomanianDate(value) {
  if (!value) return "";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return String(value);
  return dt.toLocaleDateString("ro-RO", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

export default function ReleaseCalendarPage() {
  const { baseUrl, accessToken, isAuthenticated, isAuthVerified } = useAuth();
  const { notify } = useNotice();

  const [prefs, setPrefs] = useState(null);
  const [month, setMonth] = useState(() => formatMonth(new Date()));
  const [remindersOnly, setRemindersOnly] = useState(false);
  const [includePast, setIncludePast] = useState(false);
  const [reminderDays, setReminderDays] = useState(3);

  const [items, setItems] = useState([]);
  const [meta, setMeta] = useState(null);

  const [isLoading, setIsLoading] = useState(false);
  const [isSavingPrefs, setIsSavingPrefs] = useState(false);
  const [error, setError] = useState("");

  const canLoad = useMemo(() => {
    return Boolean(isAuthVerified && accessToken);
  }, [isAuthVerified, accessToken]);

  const load = useCallback(async () => {
    if (!canLoad) {
      setItems([]);
      setPrefs(null);
      setMeta(null);
      setError("");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const nextPrefs = await getNotificationPreferences({
        baseUrl,
        accessToken,
      });
      setPrefs(nextPrefs || null);
      const effectiveReminderDays = Number(
        nextPrefs?.release_reminder_days || reminderDays || 3,
      );
      if (!Number.isNaN(effectiveReminderDays)) {
        setReminderDays(Math.max(1, Math.min(30, effectiveReminderDays)));
      }

      const data = await getReleaseCalendar({
        baseUrl,
        accessToken,
        month,
        remindersOnly,
        includePast,
        reminderDays: Math.max(
          1,
          Math.min(
            30,
            Number(nextPrefs?.release_reminder_days || reminderDays || 3),
          ),
        ),
      });

      setItems(Array.isArray(data?.items) ? data.items : []);
      setMeta(data || null);
    } catch (err) {
      console.error(err);
      setError("Nu am putut încărca calendarul de release-uri.");
      setItems([]);
      setMeta(null);
    } finally {
      setIsLoading(false);
    }
  }, [
    accessToken,
    baseUrl,
    canLoad,
    includePast,
    month,
    reminderDays,
    remindersOnly,
  ]);

  useEffect(() => {
    if (!canLoad) return;
    void load();
  }, [canLoad, load]);

  async function handleSaveReminderPrefs() {
    if (!canLoad) return;
    setIsSavingPrefs(true);
    try {
      const next = await updateNotificationPreferences({
        baseUrl,
        accessToken,
        preferences: {
          notify_release_reminders: Boolean(
            prefs?.notify_release_reminders ?? true,
          ),
          release_reminder_days: Math.max(
            1,
            Math.min(30, Number(reminderDays) || 3),
          ),
        },
      });
      setPrefs(next || null);
      notify({
        type: "success",
        message: "Setările de reminder au fost salvate.",
      });
      await load();
    } catch (err) {
      console.error(err);
      notify({
        type: "error",
        message: "Nu am putut salva setările de reminder.",
      });
    } finally {
      setIsSavingPrefs(false);
    }
  }

  async function handleToggleReminderEnabled(nextValue) {
    if (!canLoad) return;
    setPrefs((prev) => ({
      ...(prev || {}),
      notify_release_reminders: Boolean(nextValue),
    }));
    try {
      const next = await updateNotificationPreferences({
        baseUrl,
        accessToken,
        preferences: {
          notify_release_reminders: Boolean(nextValue),
        },
      });
      setPrefs(next || null);
      await load();
    } catch (err) {
      console.error(err);
      notify({ type: "error", message: "Nu am putut actualiza reminderele." });
    }
  }

  const groupedByDate = useMemo(() => {
    const map = new Map();
    for (const item of Array.isArray(items) ? items : []) {
      const key = String(item?.release_date || "");
      if (!key) continue;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(item);
    }
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [items]);

  if (!isAuthenticated) {
    return (
      <div style={ui.container}>
        <h1 style={{ marginTop: 0 }}>Calendar muzical</h1>
        <p>Trebuie să fii logat ca să vezi calendarul personalizat.</p>
        <p>
          <Link to="/login">Mergi la Login</Link>
        </p>
      </div>
    );
  }

  if (isAuthenticated && !isAuthVerified) {
    return (
      <div style={ui.container}>
        <h1 style={{ marginTop: 0 }}>Calendar muzical</h1>
        <p>Se încarcă...</p>
      </div>
    );
  }

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Calendar muzical personalizat</h1>
      <p style={{ marginTop: 0, opacity: 0.9 }}>
        Release-uri pe artiștii urmăriți și pe genurile tale preferate.
      </p>

      <section style={{ ...ui.card, marginTop: "12px" }}>
        <div
          style={{
            display: "flex",
            gap: 12,
            flexWrap: "wrap",
            alignItems: "end",
          }}
        >
          <label style={{ display: "grid", gap: 6 }}>
            Luna
            <input
              type="month"
              value={month}
              onChange={(e) =>
                setMonth(String(e.target.value || formatMonth(new Date())))
              }
              style={ui.input}
            />
          </label>

          <label style={{ display: "grid", gap: 6 }}>
            Reminder cu X zile înainte
            <input
              type="number"
              min={1}
              max={30}
              value={reminderDays}
              onChange={(e) =>
                setReminderDays(
                  Math.max(1, Math.min(30, Number(e.target.value) || 1)),
                )
              }
              style={{ ...ui.input, width: 120 }}
            />
          </label>

          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={Boolean(remindersOnly)}
              onChange={(e) => setRemindersOnly(e.target.checked)}
            />
            Doar reminder-ele
          </label>

          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={Boolean(includePast)}
              onChange={(e) => setIncludePast(e.target.checked)}
            />
            Include release-uri deja trecute
          </label>

          <button type="button" style={ui.button} onClick={load}>
            Actualizează
          </button>
        </div>

        <div
          style={{
            marginTop: 14,
            display: "flex",
            gap: 12,
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={Boolean(prefs?.notify_release_reminders ?? true)}
              onChange={(e) => handleToggleReminderEnabled(e.target.checked)}
            />
            Activează remindere de release în notificări
          </label>

          <button
            type="button"
            style={ui.buttonSmall}
            onClick={handleSaveReminderPrefs}
            disabled={isSavingPrefs}
          >
            {isSavingPrefs ? "Salvez..." : "Salvează setările reminder"}
          </button>
        </div>
      </section>

      {meta ? (
        <div style={{ marginTop: 14, opacity: 0.9 }}>
          Interval: <b>{toRomanianDate(meta.from)}</b> -{" "}
          <b>{toRomanianDate(meta.to)}</b>
        </div>
      ) : null}

      {isLoading ? <p style={{ marginTop: 14 }}>Se încarcă...</p> : null}
      {error ? (
        <p style={{ ...ui.errorText, marginTop: 14 }} role="alert">
          {error}
        </p>
      ) : null}

      {!isLoading && !error ? (
        <section style={{ marginTop: 18 }}>
          {groupedByDate.length ? (
            <div style={{ display: "grid", gap: 12 }}>
              {groupedByDate.map(([releaseDate, dateItems]) => (
                <div key={releaseDate} style={ui.card}>
                  <h3 style={{ marginTop: 0, marginBottom: 8 }}>
                    {toRomanianDate(releaseDate)}
                  </h3>

                  <div style={{ display: "grid", gap: 8 }}>
                    {dateItems.map((item) => {
                      const albumSlug = String(item?.album_slug || "");
                      const albumTitle = String(item?.album_title || "Album");
                      const artistSlug = String(item?.artist_slug || "");
                      const artistName = String(item?.artist_name || "Artist");
                      const matchedGenres = Array.isArray(item?.matched_genres)
                        ? item.matched_genres.filter(Boolean)
                        : [];
                      const daysUntil = Number(item?.days_until_release || 0);

                      return (
                        <div
                          key={`${item?.album_id}-${item?.reason}`}
                          style={{
                            borderTop: `1px dashed ${ui.colors.border}`,
                            paddingTop: 8,
                          }}
                        >
                          <div>
                            {albumSlug ? (
                              <Link
                                to={`/albums/${encodeURIComponent(albumSlug)}`}
                              >
                                {albumTitle}
                              </Link>
                            ) : (
                              <strong>{albumTitle}</strong>
                            )}{" "}
                            de{" "}
                            {artistSlug ? (
                              <Link
                                to={`/artists/${encodeURIComponent(artistSlug)}`}
                              >
                                {artistName}
                              </Link>
                            ) : (
                              <strong>{artistName}</strong>
                            )}
                          </div>

                          <div
                            style={{
                              marginTop: 4,
                              opacity: 0.85,
                              fontSize: "0.95rem",
                            }}
                          >
                            {item?.reason === "followed_artist"
                              ? "Sursă: artist urmărit"
                              : "Sursă: gen preferat"}
                            {matchedGenres.length
                              ? ` · Genuri: ${matchedGenres.join(", ")}`
                              : ""}
                          </div>

                          <div style={{ marginTop: 6 }}>
                            {item?.is_reminder ? (
                              <span
                                style={{
                                  display: "inline-block",
                                  border: `1px solid ${ui.colors.border}`,
                                  borderRadius: 999,
                                  padding: "3px 8px",
                                  background: ui.colors.mutedBg,
                                  fontSize: "0.9rem",
                                }}
                              >
                                Reminder:{" "}
                                {daysUntil === 0
                                  ? "azi"
                                  : `în ${daysUntil} zile`}
                              </span>
                            ) : (
                              <span
                                style={{ opacity: 0.8, fontSize: "0.9rem" }}
                              >
                                {daysUntil < 0
                                  ? `Lansat acum ${Math.abs(daysUntil)} zile`
                                  : `În ${daysUntil} zile`}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={ui.card}>
              Nu există release-uri în acest interval pentru preferințele tale.
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}
