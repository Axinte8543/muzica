import { useMemo, useState } from "react";

import { postCorrectionReport } from "../api/corrections.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

export default function CorrectionsPage() {
  const { baseUrl, accessToken, isAuthenticated } = useAuth();

  const [pageUrl, setPageUrl] = useState("");
  const [description, setDescription] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successId, setSuccessId] = useState(null);

  const canSubmit = useMemo(() => {
    const text = String(description || "").trim();
    return text.length > 0 && text.length <= 5000;
  }, [description]);

  function formatApiError(err, fallback) {
    const maybeStatus = err?.response?.status;
    const data = err?.response?.data;

    let details = "";
    if (typeof data === "string") {
      details = data;
    } else if (data && typeof data === "object") {
      if (typeof data.detail === "string") details = data.detail;
      else if (Array.isArray(data.description) && data.description[0]) {
        details = String(data.description[0]);
      } else if (typeof data.description === "string") {
        details = data.description;
      } else {
        try {
          details = JSON.stringify(data);
        } catch {
          details = "";
        }
      }
    }

    const base = fallback || "A apărut o eroare.";
    if (!maybeStatus && !details) return base;
    if (maybeStatus && details) return `${base} (${maybeStatus}) ${details}`;
    if (maybeStatus) return `${base} (${maybeStatus})`;
    return `${base} ${details}`;
  }

  async function onSubmit(e) {
    e.preventDefault();
    if (!canSubmit) return;

    setIsSubmitting(true);
    setError(null);
    setSuccessId(null);

    try {
      const created = await postCorrectionReport({
        baseUrl,
        accessToken: isAuthenticated ? accessToken : null,
        pageUrl: String(pageUrl || "").trim(),
        description: String(description || "").trim(),
      });

      setSuccessId(created?.id || true);
      setPageUrl("");
      setDescription("");
    } catch (err) {
      console.error(err);
      setError(formatApiError(err, "Nu am putut trimite corecția."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Corrections</h1>

      <div style={{ marginTop: 10, opacity: 0.9 }}>
        <p>
          Ai găsit o informație greșită? Trimite-ne o corecție (link +
          descriere) și o vom verifica.
        </p>
        <p style={{ marginTop: 6 }}>
          {isAuthenticated
            ? "Ești logat — raportul va fi asociat contului tău."
            : "Poți trimite și fără cont."}
        </p>
      </div>

      <div style={{ ...ui.card, marginTop: 14 }}>
        <form onSubmit={onSubmit}>
          <label style={{ display: "block", marginBottom: 6 }}>
            Link (opțional)
          </label>
          <input
            type="url"
            value={pageUrl}
            onChange={(e) => setPageUrl(e.target.value)}
            placeholder="https://..."
            style={{ ...ui.input, width: "100%" }}
            maxLength={500}
            disabled={isSubmitting}
          />

          <label style={{ display: "block", marginTop: 12, marginBottom: 6 }}>
            Descriere
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Ce este greșit și care este corect?"
            style={{
              ...ui.input,
              width: "100%",
              minHeight: 140,
              resize: "vertical",
            }}
            maxLength={5000}
            disabled={isSubmitting}
          />

          {error && (
            <p style={{ ...ui.errorText, marginTop: 12 }} role="alert">
              {error}
            </p>
          )}

          {successId && (
            <p style={{ marginTop: 12 }} role="status">
              Mulțumim! Corecția a fost trimisă.
            </p>
          )}

          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button
              type="submit"
              style={ui.button}
              disabled={!canSubmit || isSubmitting}
            >
              {isSubmitting ? "Se trimite..." : "Trimite"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
