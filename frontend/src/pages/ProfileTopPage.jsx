import { Link } from "react-router-dom";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import ProfileNav from "../components/ProfileNav.jsx";
import { useAuth } from "../context/useAuth.js";
import { getMyTopStats } from "../api/profileStats.js";
import { ui } from "../ui/ui.js";

function formatHMS(totalSeconds) {
  const sec = Number(totalSeconds || 0);
  if (!Number.isFinite(sec) || sec <= 0) return "0m";
  const hours = Math.floor(sec / 3600);
  const minutes = Math.floor((sec % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function formatDelta(deltaObj) {
  const delta = Number(deltaObj?.delta || 0);
  const pct = deltaObj?.pct_change;
  const sign = delta > 0 ? "+" : "";
  const pctText = Number.isFinite(pct) ? ` (${sign}${pct}%)` : "";
  return `${sign}${delta}${pctText}`;
}

export default function ProfileTopPage() {
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken } = useAuth();

  const today = useMemo(() => new Date(), []);
  const [period, setPeriod] = useState("month");
  const [year, setYear] = useState(String(today.getFullYear()));
  const [month, setMonth] = useState(String(today.getMonth() + 1));
  const [limit, setLimit] = useState(10);

  const topQuery = useQuery({
    queryKey: [
      "myTopStats",
      baseUrl,
      accessToken || "",
      isAuthVerified,
      period,
      year,
      month,
      limit,
    ],
    enabled: Boolean(isAuthVerified && accessToken),
    placeholderData: (prev) => prev,
    queryFn: async () => {
      const payload = await getMyTopStats({
        baseUrl,
        accessToken,
        period,
        year: period === "all" ? undefined : year,
        month: period === "month" ? month : undefined,
        limit,
      });
      return payload;
    },
  });

  const data = topQuery.data || null;
  const isLoading = topQuery.isLoading;
  const error = topQuery.isError ? "Nu am putut încărca top-ul tău." : null;

  if (!isAuthenticated) {
    return (
      <div>
        <ProfileNav />
        <div style={{ padding: "24px" }}>
          <h1 style={{ marginTop: 0 }}>Top-ul meu</h1>
          <p>Trebuie să fii logat ca să vezi statistici personale.</p>
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
          <h1 style={{ marginTop: 0 }}>Top-ul meu</h1>
          <p style={{ marginTop: "14px" }}>Se încarcă...</p>
        </div>
      </div>
    );
  }

  const totals = data?.totals || {};
  const streak = data?.streak || {};
  const comparison = data?.comparison || null;

  return (
    <div>
      <ProfileNav />
      <div style={{ padding: "24px" }}>
        <h1 style={{ marginTop: 0 }}>Top-ul meu</h1>

        <div style={{ ...ui.card, marginBottom: "16px" }}>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: "0.9em", opacity: 0.85 }}>Perioadă</span>
              <select
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                style={ui.input}
              >
                <option value="month">Lună</option>
                <option value="year">An</option>
                <option value="all">All-time</option>
              </select>
            </label>

            {period !== "all" ? (
              <label
                style={{ display: "flex", flexDirection: "column", gap: 4 }}
              >
                <span style={{ fontSize: "0.9em", opacity: 0.85 }}>An</span>
                <input
                  value={year}
                  onChange={(e) => setYear(e.target.value)}
                  inputMode="numeric"
                  style={ui.input}
                />
              </label>
            ) : null}

            {period === "month" ? (
              <label
                style={{ display: "flex", flexDirection: "column", gap: 4 }}
              >
                <span style={{ fontSize: "0.9em", opacity: 0.85 }}>
                  Lună (1-12)
                </span>
                <input
                  value={month}
                  onChange={(e) => setMonth(e.target.value)}
                  inputMode="numeric"
                  style={ui.input}
                />
              </label>
            ) : null}

            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: "0.9em", opacity: 0.85 }}>Limit</span>
              <input
                value={String(limit)}
                onChange={(e) => {
                  const n = Number(e.target.value);
                  setLimit(Number.isFinite(n) ? n : 10);
                }}
                inputMode="numeric"
                style={ui.input}
              />
            </label>
          </div>

          {isLoading && !data ? (
            <div style={{ display: "grid", gap: "10px", marginTop: "12px" }}>
              <div
                style={{
                  height: "18px",
                  width: "55%",
                  background: ui.colors.mutedBg,
                  border: `1px solid ${ui.colors.border}`,
                  borderRadius: "6px",
                }}
              />
              <div
                style={{
                  height: "18px",
                  width: "70%",
                  background: ui.colors.mutedBg,
                  border: `1px solid ${ui.colors.border}`,
                  borderRadius: "6px",
                }}
              />
            </div>
          ) : null}

          {error ? (
            <p style={{ ...ui.errorText, marginTop: "12px" }}>{error}</p>
          ) : null}
        </div>

        {isLoading && !data ? (
          <div style={{ display: "grid", gap: "16px" }}>
            <div style={ui.card}>
              <div
                style={{
                  height: "20px",
                  width: "30%",
                  background: ui.colors.mutedBg,
                  border: `1px solid ${ui.colors.border}`,
                  borderRadius: "6px",
                  marginBottom: "10px",
                }}
              />
              <div
                style={{
                  height: "18px",
                  width: "80%",
                  background: ui.colors.mutedBg,
                  border: `1px solid ${ui.colors.border}`,
                  borderRadius: "6px",
                  marginBottom: "8px",
                }}
              />
              <div
                style={{
                  height: "18px",
                  width: "70%",
                  background: ui.colors.mutedBg,
                  border: `1px solid ${ui.colors.border}`,
                  borderRadius: "6px",
                  marginBottom: "8px",
                }}
              />
              <div
                style={{
                  height: "18px",
                  width: "60%",
                  background: ui.colors.mutedBg,
                  border: `1px solid ${ui.colors.border}`,
                  borderRadius: "6px",
                }}
              />
            </div>
          </div>
        ) : null}

        {data ? (
          <div style={{ display: "grid", gap: "16px" }}>
            {comparison?.available ? (
              <div style={ui.card}>
                <h3 style={{ marginTop: 0 }}>Wrapped comparison</h3>
                <div style={{ opacity: 0.85, marginBottom: "8px" }}>
                  Față de perioada anterioară
                </div>
                <div style={{ display: "grid", gap: "6px" }}>
                  <div>
                    Listen events:{" "}
                    {formatDelta(comparison?.totals?.listen_events)}
                  </div>
                  <div>
                    Zile active: {formatDelta(comparison?.totals?.listen_days)}
                  </div>
                  <div>
                    Albume distincte:{" "}
                    {formatDelta(comparison?.totals?.distinct_albums)}
                  </div>
                  <div>
                    Timp total:{" "}
                    {formatDelta(comparison?.totals?.total_listen_seconds)} sec
                  </div>
                </div>
              </div>
            ) : null}

            <div style={ui.card}>
              <h3 style={{ marginTop: 0 }}>Rezumat</h3>
              <div>Listens (evenimente): {totals.listen_events ?? 0}</div>
              <div>Zile cu listens: {totals.listen_days ?? 0}</div>
              <div>Albume distincte: {totals.distinct_albums ?? 0}</div>
              <div>
                Timp total (estimare): {formatHMS(totals.total_listen_seconds)}
              </div>
              <div style={{ marginTop: "8px", opacity: 0.9 }}>
                Streak curent: {streak.current_days ?? 0} zile · Best:{" "}
                {streak.best_days ?? 0} zile
              </div>
            </div>

            <div style={ui.card}>
              <h3 style={{ marginTop: 0 }}>Top artiști</h3>
              {Array.isArray(data.top_artists) && data.top_artists.length ? (
                <ol style={{ paddingLeft: "18px", margin: 0 }}>
                  {data.top_artists.map((a) => (
                    <li key={a.artist_id} style={{ marginBottom: "6px" }}>
                      <Link
                        to={`/artists/${encodeURIComponent(a.artist_slug)}`}
                      >
                        {a.artist_name}
                      </Link>{" "}
                      — {a.listens} listens
                    </li>
                  ))}
                </ol>
              ) : (
                <p style={{ margin: 0, opacity: 0.85 }}>Nu există date.</p>
              )}
            </div>

            <div style={ui.card}>
              <h3 style={{ marginTop: 0 }}>Top albume</h3>
              {Array.isArray(data.top_albums) && data.top_albums.length ? (
                <ol style={{ paddingLeft: "18px", margin: 0 }}>
                  {data.top_albums.map((a) => (
                    <li key={a.album_id} style={{ marginBottom: "6px" }}>
                      <Link to={`/albums/${encodeURIComponent(a.album_slug)}`}>
                        {a.album_title}
                      </Link>{" "}
                      — {a.listens} listens
                      {a.artist_slug ? (
                        <span style={{ opacity: 0.85 }}>
                          {" "}
                          (de{" "}
                          <Link
                            to={`/artists/${encodeURIComponent(a.artist_slug)}`}
                          >
                            {a.artist_name}
                          </Link>
                          )
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ol>
              ) : (
                <p style={{ margin: 0, opacity: 0.85 }}>Nu există date.</p>
              )}
            </div>

            <div style={ui.card}>
              <h3 style={{ marginTop: 0 }}>Top melodii</h3>
              <div
                style={{
                  fontSize: "0.9em",
                  opacity: 0.85,
                  marginBottom: "8px",
                }}
              >
                Sursa:{" "}
                {data.top_songs_source === "song_ratings"
                  ? "notele tale"
                  : data.top_songs_source}
              </div>
              {Array.isArray(data.top_songs) && data.top_songs.length ? (
                <ol style={{ paddingLeft: "18px", margin: 0 }}>
                  {data.top_songs.map((s) => (
                    <li key={s.song_id} style={{ marginBottom: "6px" }}>
                      <Link to={`/songs/${encodeURIComponent(s.song_slug)}`}>
                        {s.song_title}
                      </Link>{" "}
                      — ⭐ {s.rating}
                      {s.artist_slug ? (
                        <span style={{ opacity: 0.85 }}>
                          {" "}
                          (de{" "}
                          <Link
                            to={`/artists/${encodeURIComponent(s.artist_slug)}`}
                          >
                            {s.artist_name}
                          </Link>
                          )
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ol>
              ) : (
                <p style={{ margin: 0, opacity: 0.85 }}>Nu există date.</p>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
