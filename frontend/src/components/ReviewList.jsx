import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";
import SkeletonLoader from "./SkeletonLoader.jsx";
import {
  getReviewHistory,
  likeReview,
  unlikeReview,
  updateReview,
} from "../api/reviews.js";
import {
  createReviewComment,
  getReviewComments,
} from "../api/reviewComments.js";
import {
  createModerationReport,
  getMyModerationReports,
} from "../api/moderation.js";
import ReviewReactions from "./ReviewReactions.jsx";
import ReviewCommentReactions from "./ReviewCommentReactions.jsx";

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
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

export default function ReviewList({ reviews, onChangeReviews }) {
  const { baseUrl, isAuthenticated, accessToken, user } = useAuth();
  const me = user?.username || null;

  const [pendingLikeIds, setPendingLikeIds] = useState(() => new Set());
  const [likedIds, setLikedIds] = useState(() => new Set());
  const [editState, setEditState] = useState(null);
  const [historyById, setHistoryById] = useState(() => ({}));
  const [historyLoading, setHistoryLoading] = useState(() => new Set());
  const [reportingIds, setReportingIds] = useState(() => new Set());
  const [reportingCommentIds, setReportingCommentIds] = useState(
    () => new Set(),
  );

  const [reportStatusByKey, setReportStatusByKey] = useState(() => ({}));
  const [reportMetaByKey, setReportMetaByKey] = useState(() => ({}));
  const [isLoadingMyReports, setIsLoadingMyReports] = useState(false);

  function formatReportFeedback(meta) {
    if (!meta) return "";
    const reason = String(meta.reason || "").trim();
    const feedback = String(meta.feedback || "").trim();
    const bits = [];
    if (reason) bits.push(`Motiv: ${reason}`);
    if (feedback) bits.push(`Feedback: ${feedback}`);
    return bits.join(" · ");
  }

  function ReportState({ status, meta }) {
    if (!status) return null;

    const isResolved = String(status).toLowerCase() === "resolved";
    const feedback = formatReportFeedback(meta);

    return (
      <div
        style={{
          marginTop: "8px",
          padding: "10px 12px",
          borderRadius: "10px",
          border: `1px solid ${isResolved ? "rgba(34, 197, 94, 0.35)" : "rgba(245, 158, 11, 0.35)"}`,
          background: isResolved
            ? "rgba(34, 197, 94, 0.08)"
            : "rgba(245, 158, 11, 0.08)",
          fontSize: "0.92rem",
        }}
      >
        <div style={{ fontWeight: 700 }}>
          {isResolved ? "Rezolvat" : "În analiză"}
        </div>
        {isResolved && feedback ? (
          <div style={{ marginTop: "4px" }}>{feedback}</div>
        ) : null}
      </div>
    );
  }

  useEffect(() => {
    let cancelled = false;
    async function loadMine() {
      if (!isAuthenticated || !accessToken) {
        setReportStatusByKey({});
        setReportMetaByKey({});
        return;
      }
      setIsLoadingMyReports(true);
      try {
        const data = await getMyModerationReports({
          baseUrl,
          accessToken,
        });
        if (cancelled) return;
        const arr = Array.isArray(data) ? data : [];
        const next = {};
        const nextMeta = {};
        for (const r of arr) {
          const t = String(r?.target_type || "");
          const id = Number(r?.target_id);
          const st = String(r?.status || "");
          if (!t || !Number.isFinite(id) || id <= 0 || !st) continue;
          next[`${t}:${id}`] = st;
          nextMeta[`${t}:${id}`] = {
            status: st,
            reason: String(r?.resolution_reason || "").trim(),
            feedback: String(r?.resolution_feedback || "").trim(),
            resolvedAt: r?.resolved_at || null,
            resolvedBy: String(r?.resolved_by_username || "").trim(),
          };
        }
        setReportStatusByKey(next);
        setReportMetaByKey(nextMeta);
      } catch (err) {
        console.error(err);
      } finally {
        if (!cancelled) setIsLoadingMyReports(false);
      }
    }
    loadMine();
    return () => {
      cancelled = true;
    };
  }, [accessToken, baseUrl, isAuthenticated]);

  const [commentsByReviewId, setCommentsByReviewId] = useState(() => ({}));
  const [commentsLoading, setCommentsLoading] = useState(() => new Set());
  const [commentsErrorByReviewId, setCommentsErrorByReviewId] = useState(
    () => ({}),
  );
  const [commentDraftByReviewId, setCommentDraftByReviewId] = useState(
    () => ({}),
  );
  const [replyToByReviewId, setReplyToByReviewId] = useState(() => ({}));
  const [optimisticLikesByReviewId, setOptimisticLikesByReviewId] = useState(
    () => ({}),
  );

  const sourceReviews = useMemo(() => {
    return Array.isArray(reviews) ? reviews : [];
  }, [reviews]);

  if (!Array.isArray(sourceReviews) || sourceReviews.length === 0) {
    return <p style={{ marginTop: "10px" }}>Nu există încă review-uri.</p>;
  }

  async function handleLike(reviewId) {
    if (!isAuthenticated || !accessToken) return;
    if (!reviewId) return;
    if (pendingLikeIds.has(reviewId)) return;

    // Optimistic update
    const alreadyLiked = likedIds.has(reviewId);
    const currentLikes =
      optimisticLikesByReviewId[reviewId] ||
      sourceReviews.find((r) => r.id === reviewId)?.likes_count ||
      0;
    const newLikes = alreadyLiked ? currentLikes - 1 : currentLikes + 1;

    setOptimisticLikesByReviewId((prev) => ({
      ...prev,
      [reviewId]: newLikes,
    }));

    setPendingLikeIds((prev) => new Set(prev).add(reviewId));
    try {
      const res = alreadyLiked
        ? await unlikeReview({ baseUrl, reviewId, accessToken })
        : await likeReview({ baseUrl, reviewId, accessToken });

      setLikedIds((prev) => {
        const next = new Set(prev);
        if (res?.liked) next.add(reviewId);
        else next.delete(reviewId);
        return next;
      });

      const nextLikes = Number(res?.likes_count);
      if (Number.isFinite(nextLikes)) {
        setOptimisticLikesByReviewId((prev) => ({
          ...prev,
          [reviewId]: nextLikes,
        }));
        onChangeReviews?.((prev) => {
          const prevArr = Array.isArray(prev) ? prev : [];
          return prevArr.map((r) =>
            r?.id === reviewId ? { ...r, likes_count: nextLikes } : r,
          );
        });
      }
    } catch (err) {
      console.error(err);
      // Revert optimistic update on error
      setOptimisticLikesByReviewId((prev) => {
        const next = { ...prev };
        delete next[reviewId];
        return next;
      });
    } finally {
      setPendingLikeIds((prev) => {
        const next = new Set(prev);
        next.delete(reviewId);
        return next;
      });
    }
  }

  function beginEdit(review) {
    setEditState({
      reviewId: review.id,
      title: review.title || "",
      content: review.content || "",
      isSaving: false,
      error: null,
    });
  }

  async function saveEdit() {
    if (!editState?.reviewId) return;
    if (!isAuthenticated || !accessToken) return;

    setEditState((prev) => ({ ...prev, isSaving: true, error: null }));
    try {
      const updated = await updateReview({
        baseUrl,
        reviewId: editState.reviewId,
        title: (editState.title || "").trim(),
        content: (editState.content || "").trim(),
        accessToken,
      });

      onChangeReviews?.((prev) => {
        const prevArr = Array.isArray(prev) ? prev : [];
        return prevArr.map((r) => (r?.id === updated?.id ? updated : r));
      });
      setEditState(null);
    } catch (err) {
      console.error(err);
      setEditState((prev) => ({
        ...prev,
        isSaving: false,
        error: "Nu am putut salva modificările.",
      }));
    }
  }

  async function ensureHistoryLoaded(reviewId) {
    if (!reviewId) return;
    if (historyById[String(reviewId)]) return;
    if (historyLoading.has(reviewId)) return;

    setHistoryLoading((prev) => new Set(prev).add(reviewId));
    try {
      const edits = await getReviewHistory({ baseUrl, reviewId });
      setHistoryById((prev) => ({ ...prev, [String(reviewId)]: edits }));
    } catch (err) {
      console.error(err);
      setHistoryById((prev) => ({ ...prev, [String(reviewId)]: [] }));
    } finally {
      setHistoryLoading((prev) => {
        const next = new Set(prev);
        next.delete(reviewId);
        return next;
      });
    }
  }

  async function reportReview(reviewId) {
    if (!isAuthenticated || !accessToken) return;
    if (!reviewId) return;
    if (reportingIds.has(reviewId)) return;

    setReportingIds((prev) => new Set(prev).add(reviewId));
    try {
      const created = await createModerationReport({
        baseUrl,
        targetType: "review",
        targetId: reviewId,
        reason: "",
        accessToken,
      });
      const st = created?.status;
      if (st) {
        setReportStatusByKey((prev) => ({
          ...prev,
          [`review:${reviewId}`]: String(st),
        }));
        setReportMetaByKey((prev) => ({
          ...prev,
          [`review:${reviewId}`]: {
            status: String(st),
            reason: String(created?.resolution_reason || "").trim(),
            feedback: String(created?.resolution_feedback || "").trim(),
            resolvedAt: created?.resolved_at || null,
            resolvedBy: String(created?.resolved_by_username || "").trim(),
          },
        }));
      }
    } catch (err) {
      console.error(err);
    } finally {
      setReportingIds((prev) => {
        const next = new Set(prev);
        next.delete(reviewId);
        return next;
      });
    }
  }

  async function reportReviewComment(commentId) {
    if (!isAuthenticated || !accessToken) return;
    if (!commentId) return;
    if (reportingCommentIds.has(commentId)) return;

    setReportingCommentIds((prev) => new Set(prev).add(commentId));
    try {
      const created = await createModerationReport({
        baseUrl,
        targetType: "review_comment",
        targetId: commentId,
        reason: "",
        accessToken,
      });
      const st = created?.status;
      if (st) {
        setReportStatusByKey((prev) => ({
          ...prev,
          [`review_comment:${commentId}`]: String(st),
        }));
        setReportMetaByKey((prev) => ({
          ...prev,
          [`review_comment:${commentId}`]: {
            status: String(st),
            reason: String(created?.resolution_reason || "").trim(),
            feedback: String(created?.resolution_feedback || "").trim(),
            resolvedAt: created?.resolved_at || null,
            resolvedBy: String(created?.resolved_by_username || "").trim(),
          },
        }));
      }
    } catch (err) {
      console.error(err);
    } finally {
      setReportingCommentIds((prev) => {
        const next = new Set(prev);
        next.delete(commentId);
        return next;
      });
    }
  }

  async function ensureCommentsLoaded(reviewId) {
    if (!reviewId) return;
    if (commentsByReviewId[String(reviewId)]) return;
    if (commentsLoading.has(reviewId)) return;

    setCommentsLoading((prev) => new Set(prev).add(reviewId));
    setCommentsErrorByReviewId((prev) => ({
      ...prev,
      [String(reviewId)]: null,
    }));
    try {
      const items = await getReviewComments({ baseUrl, reviewId });
      setCommentsByReviewId((prev) => ({
        ...prev,
        [String(reviewId)]: Array.isArray(items) ? items : [],
      }));
    } catch (err) {
      console.error(err);
      setCommentsByReviewId((prev) => ({ ...prev, [String(reviewId)]: [] }));
      setCommentsErrorByReviewId((prev) => ({
        ...prev,
        [String(reviewId)]: "Nu am putut încărca comentariile.",
      }));
    } finally {
      setCommentsLoading((prev) => {
        const next = new Set(prev);
        next.delete(reviewId);
        return next;
      });
    }
  }

  function getThreadedComments(comments) {
    const list = Array.isArray(comments) ? comments : [];
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
        const content = String(c?.content || "");
        const username = c?.user_username || "user";
        const createdAt = formatDate(c?.created_at);
        const nextDepth = Math.min(depth + 1, 6);

        return (
          <div
            key={cid}
            style={{
              marginLeft: depth ? `${depth * 14}px` : 0,
              padding: "8px 10px",
              border: `1px solid ${ui.colors.border}`,
              borderRadius: "8px",
              background: ui.colors.mutedBg,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "10px",
              }}
            >
              <div style={{ fontWeight: 700 }}>
                <Link
                  to={`/users/${encodeURIComponent(String(username))}`}
                  style={{ textDecoration: "none", color: "inherit" }}
                >
                  {username}
                </Link>
              </div>
              <div style={{ opacity: 0.8, fontSize: "0.9em" }}>{createdAt}</div>
            </div>

            <div style={{ marginTop: "6px", whiteSpace: "pre-wrap" }}>
              {renderWithMentions(content)}
            </div>

            {isAuthenticated ? (
              <div style={{ marginTop: "6px" }}>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    onClick={() => {
                      setReplyToByReviewId((prev) => ({
                        ...prev,
                        [String(c.review_id)]: {
                          id: cid,
                          username,
                        },
                      }));
                      setCommentDraftByReviewId((prev) => {
                        const key = String(c.review_id);
                        const existing = String(prev?.[key] || "");
                        const prefix = `@${username} `;
                        return {
                          ...prev,
                          [key]: existing.startsWith(prefix)
                            ? existing
                            : prefix + existing,
                        };
                      });
                    }}
                    style={ui.buttonSmall}
                  >
                    Reply
                  </button>

                  <button
                    type="button"
                    disabled={
                      reportingCommentIds.has(cid) ||
                      reportStatusByKey[`review_comment:${cid}`] === "pending"
                    }
                    onClick={() => reportReviewComment(cid)}
                    style={ui.buttonSmall}
                  >
                    {reportingCommentIds.has(cid)
                      ? "Raportez..."
                      : "Raportează"}
                  </button>

                  <ReportState
                    status={reportStatusByKey[`review_comment:${cid}`]}
                    meta={reportMetaByKey[`review_comment:${cid}`]}
                  />
                </div>

                <ReviewCommentReactions commentId={cid} baseUrl={baseUrl} />
              </div>
            ) : null}

            {renderLevel(cid, nextDepth)}
          </div>
        );
      });
    }

    return renderLevel(0, 0);
  }

  async function submitComment(reviewId) {
    if (!isAuthenticated || !accessToken) return;
    if (!reviewId) return;

    const key = String(reviewId);
    const content = String(commentDraftByReviewId?.[key] || "").trim();
    if (!content) return;

    const replyTo = replyToByReviewId?.[key] || null;
    const parentId = replyTo?.id ? Number(replyTo.id) : null;

    try {
      const created = await createReviewComment({
        baseUrl,
        reviewId,
        content,
        parentId,
        accessToken,
      });

      setCommentsByReviewId((prev) => {
        const arr = Array.isArray(prev?.[key]) ? prev[key] : [];
        return { ...prev, [key]: [...arr, created] };
      });
      setCommentDraftByReviewId((prev) => ({ ...prev, [key]: "" }));
      setReplyToByReviewId((prev) => ({ ...prev, [key]: null }));
    } catch (err) {
      console.error(err);
      setCommentsErrorByReviewId((prev) => ({
        ...prev,
        [key]: "Nu am putut salva comentariul.",
      }));
    }
  }

  return (
    <div style={{ marginTop: "10px", display: "grid", gap: "12px" }}>
      {sourceReviews.map((review) => {
        const title = review.title || "";
        const username = review.user_username || "user";
        const userId = review.user_id;
        const createdAt = formatDate(review.created_at);
        const baselikesCount = Number.isFinite(Number(review.likes_count))
          ? Number(review.likes_count)
          : 0;
        const likesCount =
          optimisticLikesByReviewId[review.id] !== undefined
            ? optimisticLikesByReviewId[review.id]
            : baselikesCount;
        const canEdit = Boolean(me && username && me === username);
        const isEditing = editState?.reviewId === review.id;
        const isLikePending = pendingLikeIds.has(review.id);
        const isLiked = likedIds.has(review.id);
        const isReporting = reportingIds.has(review.id);
        const reportKey = `review:${review.id}`;
        const myReportStatus = reportStatusByKey[reportKey] || "";

        const profileTo = userId
          ? `/users/${encodeURIComponent(String(username))}?id=${encodeURIComponent(
              String(userId),
            )}`
          : `/users/${encodeURIComponent(String(username))}`;

        return (
          <div
            key={review.id}
            style={{
              border: "1px solid #e5e7eb",
              borderRadius: "10px",
              padding: "12px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <Link
                to={profileTo}
                style={{
                  fontWeight: 700,
                  textDecoration: "none",
                  color: "inherit",
                }}
              >
                {username}
              </Link>
              <div style={{ opacity: 0.8, fontSize: "0.9em" }}>{createdAt}</div>
            </div>

            <div
              style={{
                marginTop: "8px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "12px",
                flexWrap: "wrap",
              }}
            >
              <div style={{ opacity: 0.9, fontWeight: 600 }}>
                ❤️ {likesCount}
              </div>
              {isAuthenticated ? (
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    disabled={isLikePending}
                    onClick={() => handleLike(review.id)}
                    className={isLikePending ? "updating" : ""}
                    style={{
                      ...ui.actionButton,
                      background: isLiked
                        ? "linear-gradient(135deg, #e11d48, #be123c)"
                        : ui.actionButton.background,
                      color: isLiked ? "white" : "inherit",
                      opacity: isLikePending ? 0.7 : 1,
                    }}
                  >
                    {isLikePending ? "⏳" : isLiked ? "❤️ Unlike" : "🤍 Like"}
                  </button>
                  <button
                    type="button"
                    disabled={isReporting || myReportStatus === "pending"}
                    onClick={() => reportReview(review.id)}
                    style={ui.actionButton}
                  >
                    {isReporting ? "Raportez..." : "⚠️ Raportează"}
                  </button>
                  <ReportState
                    status={myReportStatus}
                    meta={reportMetaByKey[reportKey]}
                  />
                  {canEdit ? (
                    <button
                      type="button"
                      onClick={() => beginEdit(review)}
                      disabled={isEditing}
                      style={ui.actionButton}
                    >
                      ✏️ Editează
                    </button>
                  ) : null}
                </div>
              ) : (
                <div style={{ opacity: 0.75, fontSize: "0.9em" }}>
                  Please log in to like/edit.
                </div>
              )}
            </div>

            {isAuthenticated ? (
              <ReviewReactions reviewId={review.id} baseUrl={baseUrl} />
            ) : null}

            {isAuthenticated && isLoadingMyReports ? (
              <div style={{ marginTop: "6px", opacity: 0.75 }}>
                Se încarcă statusul raportărilor...
              </div>
            ) : null}

            {title ? (
              <div style={{ marginTop: "8px", fontWeight: 700 }}>{title}</div>
            ) : null}

            {isEditing ? (
              <div style={{ marginTop: "10px", display: "grid", gap: "8px" }}>
                <input
                  value={editState.title}
                  onChange={(e) =>
                    setEditState((prev) => ({ ...prev, title: e.target.value }))
                  }
                  placeholder="Title"
                  style={{ width: "100%", ...ui.input }}
                />
                <textarea
                  value={editState.content}
                  onChange={(e) =>
                    setEditState((prev) => ({
                      ...prev,
                      content: e.target.value,
                    }))
                  }
                  required
                  rows={4}
                  style={{ width: "100%", ...ui.input }}
                />
                {editState.error ? (
                  <div style={ui.errorText}>{editState.error}</div>
                ) : null}
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    onClick={saveEdit}
                    disabled={editState.isSaving || !editState.content.trim()}
                    style={ui.actionButton}
                  >
                    {editState.isSaving ? "💾 Se salvează..." : "💾 Salvează"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditState(null)}
                    disabled={editState.isSaving}
                    style={ui.actionButton}
                  >
                    ❌ Anulare
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ marginTop: "8px", whiteSpace: "pre-wrap" }}>
                {review.content}
              </div>
            )}

            <details
              style={{ marginTop: "10px" }}
              onToggle={(e) => {
                if (e.currentTarget.open) ensureHistoryLoaded(review.id);
              }}
            >
              <summary style={{ cursor: "pointer", opacity: 0.9 }}>
                Istoric editări
              </summary>

              {historyLoading.has(review.id) ? (
                <div style={{ marginTop: "8px", opacity: 0.85 }}>
                  Se încarcă...
                </div>
              ) : null}

              {!historyLoading.has(review.id) ? (
                Array.isArray(historyById[String(review.id)]) &&
                historyById[String(review.id)].length ? (
                  <div
                    style={{ marginTop: "8px", display: "grid", gap: "8px" }}
                  >
                    {historyById[String(review.id)].map((h) => (
                      <div
                        key={h.id}
                        style={{
                          padding: "8px",
                          border: `1px solid ${ui.colors.border}`,
                          borderRadius: "8px",
                          background: ui.colors.mutedBg,
                        }}
                      >
                        <div style={{ opacity: 0.85, fontSize: "0.9em" }}>
                          {formatDate(h.edited_at)}
                          {h.edited_by_username ? (
                            <span> · {h.edited_by_username}</span>
                          ) : null}
                        </div>
                        {h.previous_title ? (
                          <div style={{ marginTop: "6px", fontWeight: 700 }}>
                            {h.previous_title}
                          </div>
                        ) : null}
                        <div
                          style={{ marginTop: "6px", whiteSpace: "pre-wrap" }}
                        >
                          {h.previous_content}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ marginTop: "8px", opacity: 0.85 }}>
                    Nu există editări.
                  </div>
                )
              ) : null}
            </details>

            <details
              style={{ marginTop: "10px" }}
              onToggle={(e) => {
                if (e.currentTarget.open) ensureCommentsLoaded(review.id);
              }}
            >
              <summary style={{ cursor: "pointer", opacity: 0.9 }}>
                Comentarii
              </summary>

              {commentsLoading.has(review.id) ? (
                <div style={{ marginTop: "8px" }}>
                  <SkeletonLoader variant="comment" count={3} />
                </div>
              ) : null}

              {commentsErrorByReviewId[String(review.id)] ? (
                <div style={{ ...ui.errorText, marginTop: "8px" }}>
                  {commentsErrorByReviewId[String(review.id)]}
                </div>
              ) : null}

              {!commentsLoading.has(review.id) ? (
                <div style={{ marginTop: "8px", display: "grid", gap: "8px" }}>
                  {(() => {
                    const threaded = getThreadedComments(
                      commentsByReviewId[String(review.id)],
                    );
                    return threaded.length ? (
                      threaded
                    ) : (
                      <div
                        style={{
                          opacity: 0.85,
                          padding: "8px",
                          fontSize: "14px",
                        }}
                      >
                        Nu există comentarii. Emoji-urile apar sub fiecare
                        comentariu existent.
                      </div>
                    );
                  })()}
                </div>
              ) : null}

              {isAuthenticated ? (
                <div
                  style={{
                    marginTop: "10px",
                    paddingTop: "10px",
                    borderTop: `1px solid ${ui.colors.border}`,
                    display: "grid",
                    gap: "8px",
                  }}
                >
                  {replyToByReviewId[String(review.id)]?.id ? (
                    <div style={{ opacity: 0.9, fontSize: "14px" }}>
                      Răspund la{" "}
                      <strong>
                        @{replyToByReviewId[String(review.id)]?.username}
                      </strong>{" "}
                      <button
                        type="button"
                        onClick={() =>
                          setReplyToByReviewId((prev) => ({
                            ...prev,
                            [String(review.id)]: null,
                          }))
                        }
                        style={{
                          ...ui.actionButton,
                          marginLeft: "8px",
                          fontSize: "12px",
                          padding: "6px 10px",
                        }}
                      >
                        Anulare
                      </button>
                    </div>
                  ) : null}

                  <textarea
                    rows={3}
                    value={String(
                      commentDraftByReviewId[String(review.id)] || "",
                    )}
                    onChange={(e) =>
                      setCommentDraftByReviewId((prev) => ({
                        ...prev,
                        [String(review.id)]: e.target.value,
                      }))
                    }
                    placeholder="Scrie un comentariu..."
                    style={{ width: "100%", ...ui.input }}
                  />
                  <div
                    style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}
                  >
                    <button
                      type="button"
                      onClick={() => submitComment(review.id)}
                      disabled={
                        !String(
                          commentDraftByReviewId[String(review.id)] || "",
                        ).trim()
                      }
                      style={ui.actionButton}
                    >
                      ✅ Trimite
                    </button>
                  </div>
                </div>
              ) : (
                <div
                  style={{ marginTop: "8px", opacity: 0.75, fontSize: "0.9em" }}
                >
                  Loghează-te ca să comentezi.
                </div>
              )}
            </details>
          </div>
        );
      })}
    </div>
  );
}
