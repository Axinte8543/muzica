import { useEffect, useState } from "react";
import { getMetadataSuggestions } from "../api/metadataSuggestions.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";
import "../styles/MetadataSuggestionsPage.css";

const KIND_LABELS = {
  release_date: "Data lansării",
  cover_url: "URL copertă",
  image_url: "URL imagine artist",
  tracklist: "Tracklist",
  bio: "Bio / Descriere",
  aliases: "Alias-uri",
  description: "Descriere",
  other: "Altele",
};

const STATUS_LABELS = {
  pending: "În așteptare",
  approved: "Aprobată",
  rejected: "Respingă",
};

const STATUS_COLORS = {
  pending: "#ffc107",
  approved: "#28a745",
  rejected: "#dc3545",
};

export default function MetadataSuggestionsPage() {
  const { isAuthenticated } = useAuth();
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    if (!isAuthenticated) return;

    async function fetchSuggestions() {
      try {
        setLoading(true);
        setError(null);
        const data = await getMetadataSuggestions({
          status: statusFilter,
        });
        setSuggestions(data);
      } catch (err) {
        setError(
          err?.response?.data?.detail ||
            err?.message ||
            "A apărut o eroare la încărcarea sugestiilor",
        );
      } finally {
        setLoading(false);
      }
    }

    fetchSuggestions();
  }, [isAuthenticated, statusFilter]);

  if (!isAuthenticated) {
    return (
      <div className="page-container metadata-suggestions-page">
        <div className="error-state">
          <p>{ui.mustBeLoggedIn}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container metadata-suggestions-page">
      <div className="page-header">
        <h1>Sugestiile mele de corectură</h1>
        <p className="subtitle">
          Urmăriți status-ul sugestiilor trimise pentru material muzical
        </p>
      </div>

      <div className="filter-section">
        <label htmlFor="status-filter">Filtru după status:</label>
        <select
          id="status-filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">-- Toate --</option>
          <option value="pending">În așteptare</option>
          <option value="approved">Aprobate</option>
          <option value="rejected">Respinse</option>
        </select>
      </div>

      {loading && <div className="loading-state">Se încarcă...</div>}

      {error && <div className="error-state">{error}</div>}

      {!loading && suggestions.length === 0 && (
        <div className="empty-state">
          <p>
            {statusFilter
              ? `Nu aveți sugestii cu status "${STATUS_LABELS[statusFilter]}"`
              : "Nu aveți nici o sugestie de corectură"}
          </p>
          <p className="hint">
            Puteți trimite sugestii din pagina unui artist, album sau cântec.
          </p>
        </div>
      )}

      <div className="suggestions-list">
        {suggestions.map((suggestion) => (
          <SuggestionCard key={suggestion.id} suggestion={suggestion} />
        ))}
      </div>
    </div>
  );
}

function SuggestionCard({ suggestion }) {
  const [expanded, setExpanded] = useState(false);

  const targetName =
    suggestion.artist?.name ||
    suggestion.album?.name ||
    suggestion.song?.name ||
    "Material necunoscut";

  const targetType = suggestion.artist
    ? "Artist"
    : suggestion.album
      ? "Album"
      : "Cântec";

  return (
    <div className="suggestion-card">
      <div className="card-header" onClick={() => setExpanded(!expanded)}>
        <div className="card-title-section">
          <h3 className="card-title">{targetName}</h3>
          <span className="card-type-badge">{targetType}</span>
        </div>

        <div className="card-right-section">
          <span
            className="status-badge"
            style={{ backgroundColor: STATUS_COLORS[suggestion.status] }}
          >
            {STATUS_LABELS[suggestion.status]}
          </span>
          <span className="expand-icon">{expanded ? "▼" : "▶"}</span>
        </div>
      </div>

      {expanded && (
        <div className="card-content">
          <div className="content-row">
            <span className="label">Tip de corectură:</span>
            <span className="value">
              {KIND_LABELS[suggestion.kind] || suggestion.kind}
            </span>
          </div>

          <div className="content-row">
            <span className="label">Sugestie:</span>
            <div className="value payload-value">
              {typeof suggestion.payload === "string"
                ? suggestion.payload
                : JSON.stringify(suggestion.payload, null, 2)}
            </div>
          </div>

          {suggestion.note && (
            <div className="content-row">
              <span className="label">Notă:</span>
              <span className="value">{suggestion.note}</span>
            </div>
          )}

          <div className="content-row">
            <span className="label">Trimis pe:</span>
            <span className="value">
              {new Date(suggestion.created_at).toLocaleDateString("ro-RO", {
                year: "numeric",
                month: "long",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>

          {suggestion.reviewed_at && (
            <>
              <div className="content-row">
                <span className="label">Revizuit pe:</span>
                <span className="value">
                  {new Date(suggestion.reviewed_at).toLocaleDateString(
                    "ro-RO",
                    {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    },
                  )}
                </span>
              </div>

              {suggestion.reviewed_by && (
                <div className="content-row">
                  <span className="label">Revizuit de:</span>
                  <span className="value">
                    {suggestion.reviewed_by.username}
                  </span>
                </div>
              )}
            </>
          )}

          {suggestion.decision_note && (
            <div className="content-row">
              <span className="label">Feedback:</span>
              <span className="value decision-note">
                {suggestion.decision_note}
              </span>
            </div>
          )}

          {suggestion.applied && (
            <div className="content-row applied-info">
              <span className="applied-badge">✓ Modificări aplicate</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
