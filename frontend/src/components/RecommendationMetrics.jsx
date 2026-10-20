/**
 * RecommendationMetrics.jsx
 *
 * Shows detailed breakdown of recommendation scores:
 * - Genre score
 * - Similar users score
 * - Popularity score
 * - Overall score
 *
 * Can be used in a tooltip, modal, or detail view
 */

function formatScore(value) {
  if (value === null || value === undefined) return "—";
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  return num.toFixed(2);
}

function ScoreBar({ label, value, weight, icon }) {
  const percentage = Math.max(0, Math.min(100, Number(value || 0) * 100));

  return (
    <div style={{ marginBottom: "12px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "4px",
        }}
      >
        <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
          <span style={{ fontSize: "16px" }}>{icon}</span>
          <span style={{ fontSize: "13px", fontWeight: 500 }}>{label}</span>
        </div>
        <div
          style={{
            display: "flex",
            gap: "8px",
            alignItems: "center",
            fontSize: "12px",
          }}
        >
          <strong>{formatScore(value)}</strong>
          {weight ? (
            <span style={{ opacity: 0.7 }}>
              (wt: {Number(weight * 100).toFixed(0)}%)
            </span>
          ) : null}
        </div>
      </div>

      {/* Progress bar */}
      <div
        style={{
          width: "100%",
          height: "6px",
          backgroundColor: "rgba(0,0,0,0.1)",
          borderRadius: "3px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${percentage}%`,
            height: "100%",
            backgroundColor: "rgba(59, 130, 246, 0.7)",
            borderRadius: "3px",
            transition: "width 0.2s ease",
          }}
        />
      </div>
    </div>
  );
}

export default function RecommendationMetrics({
  recommendation,
  compact = false,
}) {
  if (!recommendation) return null;

  const genreScore = Number(recommendation.genre_score) || 0;
  const simScore = Number(recommendation.similar_users_score) || 0;
  const popScore = Number(recommendation.popularity_score) || 0;
  const totalScore = Number(recommendation.score) || 0;

  // Weights from backend
  const W_GENRE = 0.3;
  const W_SIMILAR = 0.2;
  const W_POP = 0.1;

  if (compact) {
    // Minimal version for inline display
    return (
      <div
        style={{
          fontSize: "12px",
          padding: "8px",
          backgroundColor: "rgba(59, 130, 246, 0.06)",
          borderRadius: "6px",
          border: "1px solid rgba(59, 130, 246, 0.2)",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "8px",
          }}
        >
          <div>
            <span style={{ opacity: 0.7 }}>Genre:</span>{" "}
            <strong>{formatScore(genreScore)}</strong>
          </div>
          <div>
            <span style={{ opacity: 0.7 }}>Similar:</span>{" "}
            <strong>{formatScore(simScore)}</strong>
          </div>
          <div>
            <span style={{ opacity: 0.7 }}>Popular:</span>{" "}
            <strong>{formatScore(popScore)}</strong>
          </div>
          <div>
            <span style={{ opacity: 0.7 }}>Total:</span>{" "}
            <strong>{formatScore(totalScore)}</strong>
          </div>
        </div>
      </div>
    );
  }

  // Full detailed version
  return (
    <div
      style={{
        padding: "16px",
        backgroundColor: "rgba(59, 130, 246, 0.06)",
        borderRadius: "8px",
        border: "1px solid rgba(59, 130, 246, 0.2)",
      }}
    >
      <div style={{ fontWeight: 700, marginBottom: "12px" }}>
        📊 Detalii recomandare
      </div>

      <ScoreBar
        icon="🎵"
        label="Scor gen muzical"
        value={genreScore}
        weight={W_GENRE}
      />

      <ScoreBar
        icon="🎯"
        label="Scor utilizatori similari"
        value={simScore}
        weight={W_SIMILAR}
      />

      <ScoreBar
        icon="📈"
        label="Scor popularitate"
        value={popScore}
        weight={W_POP}
      />

      {/* Total score */}
      <div
        style={{
          marginTop: "14px",
          paddingTop: "12px",
          borderTop: "1px solid rgba(0,0,0,0.1)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ fontWeight: 600 }}>Scor total recomandare</div>
        <div
          style={{
            fontSize: "18px",
            fontWeight: 700,
            color: "rgb(59, 130, 246)",
          }}
        >
          {formatScore(totalScore)}
          <span style={{ fontSize: "12px", opacity: 0.7 }}> / 1.00</span>
        </div>
      </div>

      {/* Info */}
      <div
        style={{
          marginTop: "12px",
          fontSize: "12px",
          opacity: 0.75,
          fontStyle: "italic",
        }}
      >
        Scorurile se bazează pe activitatea ta (ratinguri, review-uri,
        ascultări), artiștii pe care îi urmărești, genurile tale preferate, și
        gusturile utilizatorilor similari cu tine.
      </div>
    </div>
  );
}
