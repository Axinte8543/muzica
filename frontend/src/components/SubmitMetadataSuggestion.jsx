import { useState } from "react";
import { createMetadataSuggestion } from "../api/metadataSuggestions.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";
import "../styles/SubmitMetadataSuggestion.css";

/**
 * SubmitMetadataSuggestion component
 *
 * Allows users to submit metadata corrections/suggestions for artists, albums, or songs.
 * Props:
 *   - targetType: 'artist' | 'album' | 'song'
 *   - targetId: numeric ID of target
 *   - targetName: display name for UI (e.g., "Your Album Name")
 *   - onSuccess: callback after successful submission
 */
export default function SubmitMetadataSuggestion({
  targetType,
  targetId,
  targetName,
  onSuccess,
}) {
  const { isAuthenticated } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [kind, setKind] = useState("");
  const [payload, setPayload] = useState("");
  const [note, setNote] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const kindOptions = {
    release_date: "Release date",
    cover_url: "Cover URL",
    image_url: "Artist image URL",
    tracklist: "Tracklist",
    bio: "Bio / Description",
    aliases: "Aliases / Other names",
    description: "Description",
    other: "Other",
  };

  if (!isAuthenticated) {
    return (
      <div className="submit-metadata-suggestion-placeholder">
        <p>{ui.mustBeLoggedIn}</p>
      </div>
    );
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!kind || !payload.trim()) {
      setError("Vă rog completați tipul și conținutul sugestiei");
      return;
    }

    setError(null);
    setSuccess(false);
    setIsSubmitting(true);

    try {
      let parsedPayload = payload;
      if (kind === "tracklist") {
        parsedPayload = payload.split("\n").filter((line) => line.trim());
      }

      await createMetadataSuggestion({
        targetType,
        targetId,
        kind,
        payload:
          typeof parsedPayload === "string"
            ? { value: parsedPayload }
            : { value: parsedPayload },
        note,
      });

      setSuccess(true);
      setKind("");
      setPayload("");
      setNote("");
      setTimeout(() => setIsOpen(false), 1500);

      if (onSuccess) onSuccess();
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "A apărut o eroare la trimiterea sugestiei",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="submit-metadata-suggestion-container">
      <button
        className="submit-suggestion-trigger-btn"
        onClick={() => setIsOpen(!isOpen)}
      >
        ✏️ Sugerează corectură
      </button>

      {isOpen && (
        <form className="submit-suggestion-form" onSubmit={handleSubmit}>
          <div className="form-header">
            <h3>Sugerează o corectură pentru {targetName || "material"}</h3>
            <button
              type="button"
              className="close-btn"
              onClick={() => setIsOpen(false)}
            >
              ✕
            </button>
          </div>

          <div className="form-body">
            <div className="form-group">
              <label htmlFor="suggestion-kind">Tip de corectură *</label>
              <select
                id="suggestion-kind"
                value={kind}
                onChange={(e) => setKind(e.target.value)}
                disabled={isSubmitting}
              >
                <option value="">-- Selectați tipul --</option>
                {Object.entries(kindOptions).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="suggestion-payload">
                Conținut {kind === "tracklist" && "(o melodie pe linie)"} *
              </label>
              <textarea
                id="suggestion-payload"
                value={payload}
                onChange={(e) => setPayload(e.target.value)}
                placeholder="Introduceți conținutul sugestiei..."
                rows="4"
                disabled={isSubmitting}
                maxLength="2000"
              />
              <div className="char-count">{payload.length}/2000</div>
            </div>

            <div className="form-group">
              <label htmlFor="suggestion-note">
                Notă (opțional - explicați de ce este această sugestie
                importantă)
              </label>
              <textarea
                id="suggestion-note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="De ex: Această informație este din sursa X..."
                rows="3"
                disabled={isSubmitting}
                maxLength="500"
              />
              <div className="char-count">{note.length}/500</div>
            </div>

            {error && <div className="error-message">{error}</div>}
            {success && (
              <div className="success-message">
                ✓ Sugestie trimisă cu succes! Mulțumim pentru ajutor.
              </div>
            )}
          </div>

          <div className="form-footer">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setIsOpen(false)}
              disabled={isSubmitting}
            >
              Anulează
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={isSubmitting || !kind || !payload.trim()}
            >
              {isSubmitting ? "Se trimite..." : "Trimite sugestie"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
