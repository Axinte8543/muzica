import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ui } from "../ui/ui.js";

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function ellipsize(value, maxLen = 18) {
  const s = String(value || "");
  if (s.length <= maxLen) return s;
  return `${s.slice(0, Math.max(0, maxLen - 1))}…`;
}

function sumBy(rows, key) {
  return rows.reduce((total, row) => total + (Number(row?.[key]) || 0), 0);
}

function isDemoAlbumTitle(value) {
  return /^demo fresh release\b/i.test(String(value || "").trim());
}

function SummaryCard({ label, value, detail }) {
  return (
    <div
      style={{
        ...ui.card,
        padding: "14px",
        minHeight: "96px",
        display: "grid",
        alignContent: "center",
      }}
    >
      <div style={{ opacity: 0.72 }}>{label}</div>
      <div style={{ fontWeight: 900, fontSize: "1.75rem", marginTop: "4px" }}>
        {value}
      </div>
      {detail ? (
        <div style={{ opacity: 0.75, marginTop: "2px" }}>{detail}</div>
      ) : null}
    </div>
  );
}

function ChartCard({ title, subtitle, children, empty }) {
  return (
    <section style={{ ...ui.card, padding: "16px" }}>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          gap: "12px",
          flexWrap: "wrap",
          marginBottom: "12px",
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: "1.08rem" }}>{title}</h2>
          {subtitle ? (
            <div style={{ opacity: 0.72, marginTop: "3px" }}>{subtitle}</div>
          ) : null}
        </div>
      </div>
      {empty ? <p style={{ margin: 0, opacity: 0.82 }}>{empty}</p> : children}
    </section>
  );
}

const tooltipStyle = {
  background: "rgba(15, 23, 42, 0.96)",
  border: "1px solid rgba(245, 158, 11, 0.28)",
  borderRadius: 8,
  color: "inherit",
};

const barColors = ["#f59e0b", "#38bdf8", "#22c55e", "#f472b6", "#a78bfa"];

export default function MusicStats({ stats }) {
  const albumsByYear = safeArray(stats?.albums_listened_by_year).map((row) => ({
    ...row,
    year: String(row?.year || ""),
    albums: Number(row?.albums || 0),
    listens: Number(row?.listens || 0),
  }));

  const topArtists = safeArray(stats?.top_artists).map((row) => ({
    ...row,
    name: String(row?.name || "Artist"),
    ratings: Number(row?.ratings || 0),
  }));

  const topAlbums = safeArray(stats?.top_albums)
    .map((row) => ({
      ...row,
      title: String(row?.title || "Album"),
      reviews: Number(row?.reviews || 0),
    }))
    .filter((row) => !isDemoAlbumTitle(row.title));

  const totalAlbums = sumBy(albumsByYear, "albums");
  const totalListens = sumBy(albumsByYear, "listens");
  const bestYear = albumsByYear.reduce((best, row) => {
    if (!best) return row;
    return row.albums > best.albums ? row : best;
  }, null);
  const topArtist = topArtists[0] || null;

  return (
    <div style={{ display: "grid", gap: "16px", marginTop: "16px" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "12px",
        }}
      >
        <SummaryCard
          label="Albume ascultate"
          value={totalAlbums}
          detail={`${totalListens} ascultări totale`}
        />
        <SummaryCard
          label="Ani activi"
          value={albumsByYear.length}
          detail={bestYear ? `Cel mai bun: ${bestYear.year}` : "Fără date"}
        />
        <SummaryCard
          label="Top artist"
          value={topArtist ? ellipsize(topArtist.name, 20) : "-"}
          detail={topArtist ? `${topArtist.ratings} ratinguri` : "Fără ratinguri"}
        />
      </div>

      <ChartCard
        title="Albume ascultate pe ani"
        subtitle="Evoluția albumelor distincte ascultate"
        empty={albumsByYear.length === 0 ? "Nu există date." : ""}
      >
        <div style={{ width: "100%", height: 340 }}>
          <ResponsiveContainer>
            <AreaChart
              data={albumsByYear}
              margin={{ top: 18, right: 22, left: 0, bottom: 24 }}
            >
              <defs>
                <linearGradient id="albumsByYearGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.55} />
                  <stop offset="70%" stopColor="#38bdf8" stopOpacity={0.14} />
                  <stop offset="100%" stopColor="#38bdf8" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid
                stroke="rgba(148, 163, 184, 0.22)"
                strokeDasharray="4 4"
                vertical={false}
              />
              <XAxis
                dataKey="year"
                tickLine={false}
                axisLine={{ stroke: "rgba(148, 163, 184, 0.35)" }}
              />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={36} />
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(value, name) => [
                  Number(value) || 0,
                  name === "albums" ? "albume distincte" : "ascultări",
                ]}
              />
              <Area
                type="monotone"
                dataKey="albums"
                stroke="#f59e0b"
                strokeWidth={3}
                fill="url(#albumsByYearGradient)"
                activeDot={{ r: 6, strokeWidth: 2 }}
                dot={{ r: 4, strokeWidth: 2, fill: "#0f172a" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "16px",
        }}
      >
        <ChartCard
          title="Top artiști după ratinguri"
          subtitle="Cei mai evaluați artiști"
          empty={topArtists.length === 0 ? "Nu există date." : ""}
        >
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer>
              <BarChart
                data={topArtists}
                layout="vertical"
                margin={{ top: 8, right: 18, left: 70, bottom: 8 }}
              >
                <CartesianGrid
                  stroke="rgba(148, 163, 184, 0.18)"
                  strokeDasharray="3 3"
                  horizontal={false}
                />
                <XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={78}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => ellipsize(v, 13)}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="ratings" radius={[0, 7, 7, 0]}>
                  {topArtists.map((_, index) => (
                    <Cell key={`artist-cell-${index}`} fill={barColors[index % barColors.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard
          title="Albume cu cele mai multe review-uri"
          subtitle="Discuțiile cele mai active"
          empty={topAlbums.length === 0 ? "Nu există date." : ""}
        >
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer>
              <BarChart
                data={topAlbums}
                layout="vertical"
                margin={{ top: 8, right: 18, left: 84, bottom: 8 }}
              >
                <CartesianGrid
                  stroke="rgba(148, 163, 184, 0.18)"
                  strokeDasharray="3 3"
                  horizontal={false}
                />
                <XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} />
                <YAxis
                  type="category"
                  dataKey="title"
                  width={92}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => ellipsize(v, 15)}
                />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="reviews" radius={[0, 7, 7, 0]}>
                  {topAlbums.map((_, index) => (
                    <Cell key={`album-cell-${index}`} fill={barColors[(index + 1) % barColors.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </div>
    </div>
  );
}
