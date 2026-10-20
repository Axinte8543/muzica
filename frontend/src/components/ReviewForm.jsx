import { useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";
import {
  createAlbumReview,
  deleteReviewDraft,
  getReviewDraft,
  saveReviewDraft,
} from "../api/reviews.js";

export default function ReviewForm({ albumId, onCreated }) {
  const { baseUrl, isAuthenticated, accessToken, user } = useAuth();

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const draftKey = useMemo(() => {
    const uid = user?.id ?? user?.username ?? "me";
    return `reviewDraft:${String(uid)}:${String(albumId ?? "")}`;
  }, [albumId, user?.id, user?.username]);

  const lastSavedServerRef = useRef(0);
  const didLoadRef = useRef(false);

  useEffect(() => {
    if (!albumId) return;

    // 1) Load local draft (fast) - defer state updates to next tick
    let localDraftTimeout = null;
    try {
      const raw = localStorage.getItem(draftKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === "object") {
          const t = typeof parsed.title === "string" ? parsed.title : null;
          const c = typeof parsed.content === "string" ? parsed.content : null;
          localDraftTimeout = setTimeout(() => {
            if (t !== null) setTitle(t);
            if (c !== null) setContent(c);
          }, 0);
        }
      }
    } catch {
      // ignore
    }

    // 2) Load server draft (authoritative-ish)
    let cancelled = false;
    async function loadServerDraft() {
      if (!isAuthenticated || !accessToken) return;
      try {
        const draft = await getReviewDraft({ baseUrl, albumId, accessToken });
        if (cancelled) return;
        const t = typeof draft?.title === "string" ? draft.title : "";
        const c = typeof draft?.content === "string" ? draft.content : "";

        // Only overwrite if we don't already have local input.
        setTitle((prev) => (prev ? prev : t));
        setContent((prev) => (prev ? prev : c));
      } catch {
        // ignore draft load failures
      } finally {
        didLoadRef.current = true;
      }
    }
    loadServerDraft();

    return () => {
      cancelled = true;
      if (localDraftTimeout) {
        clearTimeout(localDraftTimeout);
      }
    };
  }, [albumId, accessToken, baseUrl, draftKey, isAuthenticated]);

  useEffect(() => {
    if (!albumId) return;
    if (!didLoadRef.current) return;

    // Local autosave (always)
    try {
      localStorage.setItem(
        draftKey,
        JSON.stringify({
          title,
          content,
          updatedAt: Date.now(),
        }),
      );
    } catch {
      // ignore
    }

    // Server autosave (debounced)
    if (!isAuthenticated || !accessToken) return;
    const handle = window.setTimeout(async () => {
      try {
        const now = Date.now();
        // simple rate-limit: don't spam server
        if (now - lastSavedServerRef.current < 1200) return;
        lastSavedServerRef.current = now;

        await saveReviewDraft({
          baseUrl,
          albumId,
          title,
          content,
          accessToken,
        });
      } catch {
        // ignore autosave failures
      }
    }, 700);

    return () => {
      window.clearTimeout(handle);
    };
  }, [
    accessToken,
    albumId,
    baseUrl,
    content,
    draftKey,
    isAuthenticated,
    title,
  ]);

  async function handleSubmit(event) {
    event.preventDefault();

    if (!isAuthenticated || !accessToken) return;
    if (!albumId) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const created = await createAlbumReview({
        baseUrl,
        albumId,
        title: title.trim(),
        content: content.trim(),
        accessToken,
      });

      setTitle("");
      setContent("");

      try {
        localStorage.removeItem(draftKey);
      } catch {
        // ignore
      }
      try {
        await deleteReviewDraft({ baseUrl, albumId, accessToken });
      } catch {
        // ignore
      }

      if (typeof onCreated === "function") {
        onCreated(created);
      }
    } catch (err) {
      console.error(err);
      setError("Nu am putut salva review-ul.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!isAuthenticated) {
    return (
      <p style={{ marginTop: "10px", opacity: 0.9 }}>
        Loghează-te ca să scrii un review.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} style={{ marginTop: "10px" }}>
      <label style={{ display: "block", marginTop: "10px" }}>
        <div style={{ fontWeight: 600 }}>Titlu</div>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Foarte bun"
          style={{ width: "100%", marginTop: "6px", ...ui.input }}
        />
      </label>

      <label style={{ display: "block", marginTop: "10px" }}>
        <div style={{ fontWeight: 600 }}>Conținut</div>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          required
          rows={4}
          placeholder="Album foarte bine produs..."
          style={{ width: "100%", marginTop: "6px", ...ui.input }}
        />
      </label>

      {error ? (
        <p style={{ ...ui.errorText, marginTop: "10px" }}>{error}</p>
      ) : null}

      <button
        type="submit"
        disabled={isSubmitting || !content.trim()}
        style={{ marginTop: "12px", ...ui.button }}
      >
        {isSubmitting ? "Se trimite..." : "Trimite review"}
      </button>
    </form>
  );
}
