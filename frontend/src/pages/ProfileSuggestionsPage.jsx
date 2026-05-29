import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import ProfileNav from "../components/ProfileNav.jsx";
import { getMyMetadataSuggestions } from "../api/moderation.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

function formatDate(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString();
}

function statusLabel(raw) {
  const s = String(raw || "").toLowerCase();
  if (s === "pending") return "În așteptare";
  if (s === "approved") return "Aprobat";
  if (s === "rejected") return "Respins";
  return String(raw || "");
}

function statusTone(raw) {
  const s = String(raw || "").toLowerCase();
  if (s === "approved") return { bg: "#14532d", fg: "#dcfce7" };
  if (s === "rejected") return { bg: "#7f1d1d", fg: "#fee2e2" };
  if (s === "pending") return { bg: "#78350f", fg: "#ffedd5" };
  return { bg: "#374151", fg: "#f3f4f6" };
}

export default function ProfileSuggestionsPage() {
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken, logout } =
    useAuth();

  const [items, setItems] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!isAuthenticated || !isAuthVerified || !accessToken) return;

      setIsLoading(true);
      setError(null);
      try {
        const data = await getMyMetadataSuggestions({ baseUrl, accessToken });
        if (cancelled) return;
        setItems(Array.isArray(data) ? data : []);
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!cancelled) setError("Nu am putut încărca sugestiile.");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [accessToken, baseUrl, isAuthenticated, isAuthVerified, logout]);

  const suggestions = useMemo(() => {
    return Array.isArray(items) ? items : [];
  }, [items]);

  if (!isAuthenticated) {
    return (
      <div>
        <ProfileNav />
        <div style={{ padding: "24px" }}>
          <h1 style={{ marginTop: 0 }}>Sugestiile mele</h1>
          <p>Trebuie să fii logat ca să vezi sugestiile tale.</p>
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
          <h1 style={{ marginTop: 0 }}>Sugestiile mele</h1>
          <p style={{ marginTop: "14px" }}>Se încarcă...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <ProfileNav />
      <div style={{ padding: "24px" }}>
        <h1 style={{ marginTop: 0 }}>Sugestiile mele</h1>

        <div
          style={{
            ...ui.card,
            maxWidth: "760px",
          }}
        >
          {isLoading ? (
            <div style={{ opacity: 0.85 }}>Se încarcă...</div>
          ) : null}
          {error ? <div style={ui.errorText}>{error}</div> : null}

          {!isLoading && !error && !suggestions.length ? (
            <div style={{ opacity: 0.9 }}>Nu ai sugestii încă.</div>
          ) : null}

          {!isLoading && !error && suggestions.length ? (
            <div style={{ display: "grid", gap: 10 }}>
              {suggestions.map((s) => (
                <div
                  key={s.id}
                  style={{
                    padding: "10px",
                    border: "1px solid var(--border-color)",
                    borderRadius: "10px",
                    background: "var(--surface-strong)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      gap: 10,
                      flexWrap: "wrap",
                      alignItems: "center",
                    }}
                  >
                    <div
                      style={{
                        fontWeight: 700,
                        padding: "3px 8px",
                        borderRadius: 999,
                        background: statusTone(s.status).bg,
                        color: statusTone(s.status).fg,
                      }}
                    >
                      {s.kind} · {statusLabel(s.status)}
                    </div>
                    <div style={{ opacity: 0.75 }}>
                      {formatDate(s.created_at)}
                    </div>
                  </div>
                  <div style={{ marginTop: 6, opacity: 0.9 }}>
                    Țintă: {s.target_type}:{s.target_id}
                  </div>
                  {s.note ? (
                    <div
                      style={{
                        marginTop: 6,
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {s.note}
                    </div>
                  ) : null}

                  {s.decision_note ? (
                    <div style={{ marginTop: 6, opacity: 0.85 }}>
                      <strong>Răspuns moderator:</strong> {s.decision_note}
                    </div>
                  ) : null}
                  {s.applied !== null && s.applied !== undefined ? (
                    <div style={{ marginTop: 6, opacity: 0.8 }}>
                      Aplicată: {s.applied ? "Da" : "Nu"}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
