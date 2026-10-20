import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import RatingWidget from "../components/RatingWidget.jsx";
import SongCommentReactions from "../components/SongCommentReactions.jsx";
import { getSongLikeStatus, likeSong, unlikeSong } from "../api/likedSongs.js";
import {
  createMetadataSuggestion,
  createModerationReport,
  getMyModerationReports,
} from "../api/moderation.js";
import { apiClient } from "../api/apiClient.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return "";
  const totalSeconds = Number(seconds);
  if (Number.isNaN(totalSeconds)) return "";

  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

function releaseLabelForSong(song) {
  const type = String(song?.album_release_type || "").toLowerCase();
  if (type === "single") return "Single";
  if (type === "ep") return "EP";
  if (type === "compilation") return "Compilație";
  return "Release";
}

function renderWithMentions(text) {
  const src = String(text ?? "");
  const parts = src.split(/(\s+)/);
  return parts.map((p, idx) => {
    if (!p.startsWith("@")) return <span key={idx}>{p}</span>;

    const raw = p.slice(1);
    const match = raw.match(/^([A-Za-z0-9_]+)(.*)$/);
    if (!match) return <span key={idx}>{p}</span>;
    const username = match[1];
    const tail = match[2] || "";
    if (!username) return <span key={idx}>{p}</span>;

    return (
      <span key={idx}>
        <Link to={`/users/${encodeURIComponent(username)}`}>@{username}</Link>
        {tail}
      </span>
    );
  });
}

export default function SongPage({ slug }) {
  const [searchParams] = useSearchParams();
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken, logout } =
    useAuth();

  const [song, setSong] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [likeStatus, setLikeStatus] = useState({ liked: false, likesCount: 0 });
  const [isLoadingLike, setIsLoadingLike] = useState(false);
  const [isSubmittingLiked, setIsSubmittingLiked] = useState(false);
  const [likeError, setLikeError] = useState(null);

  const [comments, setComments] = useState([]);
  const [isLoadingComments, setIsLoadingComments] = useState(false);
  const [commentsError, setCommentsError] = useState(null);
  const [commentText, setCommentText] = useState("");
  const [replyToComment, setReplyToComment] = useState(null);
  const [isPostingComment, setIsPostingComment] = useState(false);
  const [highlightedCommentId, setHighlightedCommentId] = useState(null);
  const [reportingCommentIds, setReportingCommentIds] = useState(
    () => new Set(),
  );

  const [reportStatusByKey, setReportStatusByKey] = useState(() => ({}));
  const [isLoadingMyReports, setIsLoadingMyReports] = useState(false);

  const [showSuggest, setShowSuggest] = useState(false);
  const [suggestDescription, setSuggestDescription] = useState("");
  const [isSubmittingSuggest, setIsSubmittingSuggest] = useState(false);
  const [suggestError, setSuggestError] = useState(null);
  const [suggestSuccess, setSuggestSuccess] = useState(null);

  useEffect(() => {
    const raw =
      searchParams.get("comment") ||
      searchParams.get("comment_id") ||
      searchParams.get("c") ||
      "";
    const parsed = Number(raw);
    if (Number.isFinite(parsed) && parsed > 0) {
      queueMicrotask(() => setHighlightedCommentId(parsed));
      return;
    }
    queueMicrotask(() => setHighlightedCommentId(null));
  }, [searchParams]);

  function statusLabel(raw) {
    const s = String(raw || "").toLowerCase();
    if (s === "pending") return "În așteptare";
    if (s === "resolved") return "Rezolvat";
    return "";
  }

  async function reportSongComment(commentId) {
    if (!isAuthVerified || !accessToken) return;
    if (!commentId) return;
    if (reportingCommentIds.has(commentId)) return;

    setReportingCommentIds((prev) => new Set(prev).add(commentId));
    try {
      const created = await createModerationReport({
        baseUrl,
        targetType: "song_comment",
        targetId: commentId,
        reason: "",
        accessToken,
      });
      const st = created?.status;
      if (st) {
        setReportStatusByKey((prev) => ({
          ...prev,
          [`song_comment:${commentId}`]: String(st),
        }));
      }
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
    } finally {
      setReportingCommentIds((prev) => {
        const next = new Set(prev);
        next.delete(commentId);
        return next;
      });
    }
  }

  useEffect(() => {
    if (!slug) return;

    let isCancelled = false;

    apiClient
      .get(`/api/songs/${slug}/`)
      .then((response) => {
        if (isCancelled) return;
        setSong(response.data);
        setError(null);
      })
      .catch((err) => {
        if (isCancelled) return;
        console.error(err);
        setSong(null);
        setError("Melodia nu a putut fi încărcată.");
      })
      .finally(() => {
        if (isCancelled) return;
        setIsLoading(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [slug]);

  useEffect(() => {
    if (!isAuthVerified || !accessToken) return;
    if (!song?.id) return;

    let isCancelled = false;
    queueMicrotask(() => {
      setIsLoadingLike(true);
      setLikeError(null);
    });

    getSongLikeStatus({
      baseUrl,
      accessToken,
      songId: song.id,
    })
      .then((data) => {
        if (isCancelled) return;
        setLikeStatus({
          liked: Boolean(data?.liked),
          likesCount: Number(data?.likes_count ?? 0) || 0,
        });
      })
      .catch((err) => {
        if (isCancelled) return;
        console.error(err);
        setLikeError("Nu am putut încărca statusul de Like.");
      })
      .finally(() => {
        if (isCancelled) return;
        setIsLoadingLike(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [accessToken, baseUrl, isAuthVerified, song?.id]);

  useEffect(() => {
    if (!song?.id) return;

    let isCancelled = false;
    queueMicrotask(() => {
      setIsLoadingComments(true);
      setCommentsError(null);
    });

    apiClient
      .get(`/api/songs/${song.id}/comments/`)
      .then((response) => {
        if (isCancelled) return;
        setComments(Array.isArray(response.data) ? response.data : []);
      })
      .catch((err) => {
        if (isCancelled) return;
        console.error(err);
        setComments([]);
        setCommentsError("Nu am putut încărca comentariile.");
      })
      .finally(() => {
        if (isCancelled) return;
        setIsLoadingComments(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [song?.id]);

  useEffect(() => {
    let cancelled = false;
    async function loadMyReports() {
      if (!isAuthVerified || !accessToken) {
        setReportStatusByKey({});
        return;
      }
      setIsLoadingMyReports(true);
      try {
        const data = await getMyModerationReports({ baseUrl, accessToken });
        if (cancelled) return;
        const arr = Array.isArray(data) ? data : [];
        const next = {};
        for (const r of arr) {
          const t = String(r?.target_type || "");
          const id = Number(r?.target_id);
          const st = String(r?.status || "");
          if (t !== "song_comment") continue;
          if (!Number.isFinite(id) || id <= 0 || !st) continue;
          next[`song_comment:${id}`] = st;
        }
        setReportStatusByKey(next);
      } catch (err) {
        console.error(err);
      } finally {
        if (!cancelled) setIsLoadingMyReports(false);
      }
    }
    loadMyReports();
    return () => {
      cancelled = true;
    };
  }, [accessToken, baseUrl, isAuthVerified]);

  async function submitSuggestion() {
    if (!isAuthVerified || !accessToken) return;
    if (!song?.id) return;
    const text = String(suggestDescription || "").trim();
    if (!text) return;

    setIsSubmittingSuggest(true);
    setSuggestError(null);
    setSuggestSuccess(null);
    try {
      await createMetadataSuggestion({
        baseUrl,
        targetType: "song",
        targetId: song.id,
        kind: "description",
        payload: { description: text },
        note: "",
        accessToken,
      });
      setSuggestSuccess("Sugestia a fost trimisă (pending).");
      setSuggestDescription("");
      setShowSuggest(false);
    } catch (err) {
      console.error(err);
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      const httpStatus = err?.response?.status;
      const data = err?.response?.data;
      let details = "";
      if (data) {
        try {
          details =
            typeof data === "string" ? data : JSON.stringify(data, null, 2);
        } catch {
          details = "";
        }
      }
      const msg =
        `Nu am putut trimite sugestia${httpStatus ? ` (HTTP ${httpStatus})` : ""}.` +
        (details ? `\n${details}` : "");
      setSuggestError(msg.slice(0, 1200));
    } finally {
      setIsSubmittingSuggest(false);
    }
  }

  async function handlePostComment() {
    if (!isAuthVerified || !accessToken) return;
    if (!song?.id) return;

    const content = String(commentText || "").trim();
    if (!content) {
      setCommentsError("Scrie un comentariu înainte să trimiți.");
      return;
    }

    setIsPostingComment(true);
    setCommentsError(null);

    try {
      const payload = { content };
      if (replyToComment?.id) {
        payload.parent_id = Number(replyToComment.id);
      }
      const response = await apiClient.post(
        `/api/songs/${song.id}/comments/`,
        payload,
      );
      const created = response?.data;
      setComments((prev) => [...prev, created].filter(Boolean));
      setCommentText("");
      setReplyToComment(null);
    } catch (err) {
      console.error(err);
      setCommentsError("Nu am putut posta comentariul.");
    } finally {
      setIsPostingComment(false);
    }
  }

  async function handleToggleLike() {
    if (!isAuthVerified || !accessToken) return;
    if (!song?.id) return;

    setIsSubmittingLiked(true);
    setLikeError(null);

    try {
      const result = likeStatus.liked
        ? await unlikeSong({
            baseUrl,
            accessToken,
            songId: song.id,
          })
        : await likeSong({
            baseUrl,
            accessToken,
            songId: song.id,
          });

      setLikeStatus({
        liked: Boolean(result?.liked),
        likesCount: Number(result?.likes_count ?? 0) || 0,
      });
    } catch (err) {
      console.error(err);
      setLikeError("Nu am putut actualiza Like.");
    } finally {
      setIsSubmittingLiked(false);
    }
  }

  function getThreadedComments(sourceComments) {
    const list = Array.isArray(sourceComments) ? sourceComments : [];
    const childrenByParent = new Map();

    for (const c of list) {
      const parentId = c?.parent_id ? Number(c.parent_id) : 0;
      if (!childrenByParent.has(parentId)) childrenByParent.set(parentId, []);
      childrenByParent.get(parentId).push(c);
    }

    function renderLevel(parentId, depth) {
      const items = childrenByParent.get(parentId) || [];
      return items.map((c) => {
        const cid = Number(c?.id);
        const username = c?.user_username || `User ${c?.user_id || ""}`;
        const isHighlighted =
          highlightedCommentId && cid === highlightedCommentId;
        const nextDepth = Math.min(depth + 1, 6);

        return (
          <div
            key={c.id ?? `${c.user_id}-${c.created_at}`}
            id={`song-comment-${cid}`}
            style={{
              marginLeft: depth ? `${depth * 14}px` : 0,
              border: isHighlighted
                ? "2px solid var(--link-color)"
                : `1px solid ${ui.colors.border}`,
              borderRadius: "10px",
              padding: "10px",
              background: ui.colors.mutedBg,
              boxShadow: isHighlighted
                ? "0 0 0 2px color-mix(in srgb, var(--link-color) 25%, transparent)"
                : "none",
            }}
          >
            <div style={{ fontSize: "0.95rem", opacity: 0.9 }}>
              <strong>{username}</strong>
              {c.created_at ? (
                <span style={{ marginLeft: "8px", opacity: 0.75 }}>
                  {new Date(c.created_at).toLocaleString()}
                </span>
              ) : null}
              {isHighlighted ? (
                <span
                  style={{ marginLeft: 8, fontSize: "0.85em", fontWeight: 700 }}
                >
                  mention
                </span>
              ) : null}
            </div>

            <div style={{ marginTop: "6px", whiteSpace: "pre-wrap" }}>
              {renderWithMentions(c.content)}
            </div>

            {isAuthenticated ? (
              <div
                style={{
                  marginTop: "8px",
                  display: "flex",
                  gap: "8px",
                  flexWrap: "wrap",
                }}
              >
                <button
                  type="button"
                  style={ui.buttonSmall}
                  onClick={() => {
                    setReplyToComment({
                      id: cid,
                      username,
                    });
                    setCommentText((prev) => {
                      const existing = String(prev || "");
                      const prefix = `@${username} `;
                      return existing.startsWith(prefix)
                        ? existing
                        : prefix + existing;
                    });
                  }}
                >
                  Reply
                </button>

                <button
                  type="button"
                  style={ui.buttonSmall}
                  disabled={
                    reportingCommentIds.has(cid) ||
                    reportStatusByKey[`song_comment:${cid}`] === "pending"
                  }
                  onClick={() => reportSongComment(cid)}
                >
                  {reportingCommentIds.has(cid) ? "Raportez..." : "Raportează"}
                </button>

                {reportStatusByKey[`song_comment:${cid}`] ? (
                  <span style={{ opacity: 0.85, alignSelf: "center" }}>
                    Raport:{" "}
                    {statusLabel(reportStatusByKey[`song_comment:${cid}`])}
                  </span>
                ) : null}
              </div>
            ) : null}

            <SongCommentReactions commentId={cid} baseUrl={baseUrl} />

            {renderLevel(cid, nextDepth)}
          </div>
        );
      });
    }

    return renderLevel(0, 0);
  }

  useEffect(() => {
    if (!highlightedCommentId) return;
    if (!Array.isArray(comments) || !comments.length) return;

    const exists = comments.some(
      (c) => Number(c?.id) === Number(highlightedCommentId),
    );
    if (!exists) return;

    const el = document.getElementById(
      `song-comment-${Number(highlightedCommentId)}`,
    );
    if (!el) return;

    el.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [comments, highlightedCommentId]);

  if (isLoading) {
    return (
      <div style={{ padding: "24px" }}>
        <p>Se încarcă...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "24px" }}>
        <p style={{ marginTop: 0 }}>
          <Link to="/">← Înapoi la albume</Link>
        </p>
        <p style={{ color: "crimson" }}>{error}</p>
      </div>
    );
  }

  if (!song) {
    return (
      <div style={{ padding: "24px" }}>
        <p style={{ marginTop: 0 }}>
          <Link to="/">← Înapoi la albume</Link>
        </p>
        <p>Melodie indisponibilă.</p>
      </div>
    );
  }

  return (
    <div style={{ padding: "24px" }}>
      <p style={{ marginTop: 0 }}>
        <Link to="/">← Înapoi la albume</Link>
      </p>

      <div
        style={{
          display: "flex",
          gap: "24px",
          marginBottom: "24px",
          alignItems: "flex-start",
          flexWrap: "wrap",
        }}
      >
        {song.album_cover_url ? (
          <div
            style={{
              flex: "0 0 160px",
              borderRadius: "12px",
              overflow: "hidden",
              border: "1px solid var(--border-color)",
              boxShadow: "var(--shadow-soft)",
            }}
          >
            <img
              src={song.album_cover_url}
              alt={`Coperta albumului ${song.album_title || "necunoscut"}`}
              style={{
                width: "100%",
                height: "160px",
                objectFit: "cover",
                display: "block",
              }}
            />
          </div>
        ) : null}

        <div style={{ flex: "1 1 300px", minWidth: 0 }}>
          <h1 style={{ margin: 0 }}>
            {song.title}
            {Array.isArray(song.featured_artists) &&
            song.featured_artists.length ? (
              <span style={{ opacity: 0.9, fontWeight: 400 }}>
                {" "}
                (feat.{" "}
                {song.featured_artists
                  .filter((a) => a && (a.name || a.slug))
                  .map((a) => {
                    const key = a.id || a.slug || a.name;
                    const name = String(a.name || "Artist");
                    const slug = String(a.slug || "").trim();
                    return slug ? (
                      <Link
                        key={key}
                        to={`/artists/${encodeURIComponent(slug)}`}
                      >
                        {name}
                      </Link>
                    ) : (
                      <span key={key}>{name}</span>
                    );
                  })
                  .reduce((acc, el, idx) => {
                    if (idx === 0) return [el];
                    return [...acc, ", ", el];
                  }, [])}
                )
              </span>
            ) : null}
          </h1>

          {song.id ? <RatingWidget kind="song" itemId={song.id} /> : null}

          <div style={{ marginTop: "16px" }}>
            <div style={{ marginTop: "6px" }}>
              <p style={{ margin: "6px 0" }}>
                <strong>Artist:</strong>{" "}
                {song.artist_slug ? (
                  <Link to={`/artists/${song.artist_slug}`}>
                    {song.artist_name}
                  </Link>
                ) : (
                  song.artist_name
                )}
              </p>

              <p style={{ margin: "6px 0" }}>
                <strong>{releaseLabelForSong(song)}:</strong>{" "}
                {song.album_slug ? (
                  <Link to={`/albums/${song.album_slug}`}>
                    {song.album_title}
                  </Link>
                ) : (
                  song.album_title || "-"
                )}
              </p>

              <p style={{ margin: "6px 0" }}>
                <strong>Track number:</strong> {song.track_number ?? "-"}
              </p>

              <p style={{ margin: "6px 0" }}>
                <strong>Durată:</strong>{" "}
                {song.duration_seconds
                  ? formatDuration(song.duration_seconds)
                  : "-"}
              </p>

              {song.genres?.length ? (
                <p style={{ margin: "6px 0" }}>
                  <strong>Genuri:</strong>{" "}
                  {song.genres.map((g) => g.name).join(", ")}
                </p>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: "12px" }}>
        <h3>Like</h3>

        {!isAuthenticated ? (
          <p style={{ marginTop: "8px", opacity: 0.9 }}>
            Loghează-te ca să dai Like la melodii.
          </p>
        ) : null}

        {isAuthenticated ? (
          <button
            type="button"
            onClick={handleToggleLike}
            disabled={!song?.id || isLoadingLike || isSubmittingLiked}
            style={ui.button}
          >
            {likeStatus.liked ? "Unlike" : "Like"}
          </button>
        ) : null}

        {isAuthenticated && !isLoadingLike ? (
          <div style={{ marginTop: "8px", opacity: 0.9 }}>
            Like-uri: {likeStatus.likesCount}
          </div>
        ) : null}

        {isLoadingLike ? (
          <div style={{ marginTop: "8px", opacity: 0.85 }}>
            Se încarcă statusul...
          </div>
        ) : null}

        {isSubmittingLiked ? (
          <div style={{ marginTop: "8px", opacity: 0.85 }}>Se salvează...</div>
        ) : null}

        {likeError ? (
          <p style={{ ...ui.errorText, marginTop: "8px" }}>{likeError}</p>
        ) : null}
      </div>

      {song.description ? (
        <div style={{ marginTop: "16px" }}>
          <h3>Descriere</h3>
          <p style={{ whiteSpace: "pre-wrap" }}>{song.description}</p>
        </div>
      ) : null}

      <div style={{ marginTop: "16px", ...ui.card }}>
        <div style={{ fontWeight: 700, marginBottom: "8px" }}>
          Sugerează corecție
        </div>
        {!isAuthenticated ? (
          <div style={{ opacity: 0.9 }}>
            <Link to="/login">Login</Link> ca să trimiți o sugestie.
          </div>
        ) : (
          <>
            <button
              type="button"
              onClick={() => {
                setShowSuggest((v) => !v);
                setSuggestError(null);
                setSuggestSuccess(null);
              }}
              style={ui.buttonSmall}
            >
              {showSuggest ? "Ascunde" : "Descriere"}
            </button>

            {showSuggest ? (
              <div style={{ marginTop: "10px", display: "grid", gap: 8 }}>
                <textarea
                  value={suggestDescription}
                  onChange={(e) => setSuggestDescription(e.target.value)}
                  placeholder="Propune o descriere corectă..."
                  rows={4}
                  style={{ ...ui.input, width: "100%" }}
                />
                <button
                  type="button"
                  onClick={submitSuggestion}
                  disabled={isSubmittingSuggest || !suggestDescription.trim()}
                  style={ui.button}
                >
                  {isSubmittingSuggest ? "Trimit..." : "Trimite"}
                </button>
              </div>
            ) : null}
          </>
        )}
        {suggestError ? (
          <div style={{ ...ui.errorText, marginTop: 8 }}>{suggestError}</div>
        ) : null}
        {suggestSuccess ? (
          <div style={{ marginTop: 8, opacity: 0.9 }}>{suggestSuccess}</div>
        ) : null}
      </div>

      <div style={{ marginTop: "20px" }}>
        <h3 style={{ marginBottom: "10px" }}>
          Comentarii ({Array.isArray(comments) ? comments.length : 0})
        </h3>

        {isLoadingComments ? (
          <p style={{ marginTop: 0, opacity: 0.85 }}>
            Se încarcă comentariile...
          </p>
        ) : null}

        {!isLoadingComments && (!comments || comments.length === 0) ? (
          <p style={{ marginTop: 0, opacity: 0.85 }}>
            Nu există comentarii încă. Emoji-urile apar sub fiecare comentariu
            existent.
          </p>
        ) : null}

        {Array.isArray(comments) && comments.length ? (
          <div style={{ display: "grid", gap: "10px" }}>
            {getThreadedComments(comments)}
          </div>
        ) : null}

        {isAuthenticated && isLoadingMyReports ? (
          <div style={{ marginTop: 10, opacity: 0.75 }}>
            Se încarcă statusul raportărilor...
          </div>
        ) : null}

        <div style={{ marginTop: "12px" }}>
          {!isAuthenticated ? (
            <p style={{ marginTop: 0, opacity: 0.9 }}>
              Loghează-te ca să lași un comentariu.
            </p>
          ) : (
            <>
              {replyToComment?.id ? (
                <div
                  style={{
                    marginBottom: "8px",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    flexWrap: "wrap",
                  }}
                >
                  <span style={{ opacity: 0.9 }}>
                    Răspunzi la{" "}
                    <strong>@{replyToComment.username || "user"}</strong>
                  </span>
                  <button
                    type="button"
                    style={ui.buttonSmall}
                    onClick={() => setReplyToComment(null)}
                  >
                    Anulează reply
                  </button>
                </div>
              ) : null}

              <textarea
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                placeholder={
                  replyToComment?.id
                    ? "Scrie răspunsul tău (mențiunile @user sunt suportate)..."
                    : "Scrie un comentariu..."
                }
                style={{ ...ui.input, width: "100%", minHeight: "80px" }}
              />
              <div style={{ marginTop: "8px" }}>
                <button
                  type="button"
                  onClick={handlePostComment}
                  disabled={isPostingComment}
                  style={ui.button}
                >
                  {isPostingComment ? "Se postează..." : "Postează"}
                </button>
              </div>
            </>
          )}

          {commentsError ? (
            <p style={{ ...ui.errorText, marginTop: "8px" }}>{commentsError}</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
