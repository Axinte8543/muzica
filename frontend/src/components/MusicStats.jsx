import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ui } from "../ui/ui.js";

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function formatPercentLabel(name, percent) {
  const p = Number(percent);
  if (!Number.isFinite(p)) return String(name || "");
  return `${name} (${p}%)`;
}

function ellipsize(value, maxLen = 14) {
  const s = String(value || "");
  if (s.length <= maxLen) return s;
  return `${s.slice(0, Math.max(0, maxLen - 1))}…`;
}

export default function MusicStats({ stats }) {
  const topGenres = safeArray(stats?.top_genres);
  const topArtists = safeArray(stats?.top_artists);
  const topAlbums = safeArray(stats?.top_albums);

  return (
    <div style={{ display: "grid", gap: "16px", marginTop: "16px" }}>
      <div style={ui.card}>
        <div style={{ fontWeight: 700 }}>Genre distribution</div>

        {topGenres.length === 0 ? (
          <p style={{ marginTop: "10px" }}>Nu există date.</p>
        ) : (
          <div style={{ width: "100%", height: 280, marginTop: "10px" }}>
            <ResponsiveContainer>
              <PieChart>
                <Tooltip
                  formatter={(value, name, props) => {
                    const payload = props?.payload;
                    const pct = payload?.percent;
                    return [
                      `${Number(value) || 0} ratings`,
                      formatPercentLabel(name, pct),
                    ];
                  }}
                />
                <Legend
                  formatter={(value, entry) => {
                    const pct = entry?.payload?.payload?.percent;
                    return formatPercentLabel(value, pct);
                  }}
                />
                <Pie
                  data={topGenres}
                  dataKey="ratings"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div style={ui.card}>
        <div style={{ fontWeight: 700 }}>Top artists by ratings</div>

        {topArtists.length === 0 ? (
          <p style={{ marginTop: "10px" }}>Nu există date.</p>
        ) : (
          <div style={{ width: "100%", height: 300, marginTop: "10px" }}>
            <ResponsiveContainer>
              <BarChart
                data={topArtists}
                margin={{ top: 8, right: 12, left: 0, bottom: 40 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="name"
                  interval={0}
                  angle={-20}
                  textAnchor="end"
                  tickFormatter={(v) => ellipsize(v, 16)}
                  height={60}
                />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="ratings" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div style={ui.card}>
        <div style={{ fontWeight: 700 }}>Most reviewed albums</div>

        {topAlbums.length === 0 ? (
          <p style={{ marginTop: "10px" }}>Nu există date.</p>
        ) : (
          <div style={{ width: "100%", height: 320, marginTop: "10px" }}>
            <ResponsiveContainer>
              <BarChart
                data={topAlbums}
                margin={{ top: 8, right: 12, left: 0, bottom: 60 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="title"
                  interval={0}
                  angle={-20}
                  textAnchor="end"
                  tickFormatter={(v) => ellipsize(v, 18)}
                  height={70}
                />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="reviews" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
