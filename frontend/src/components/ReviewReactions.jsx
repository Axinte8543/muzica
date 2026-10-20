import { useCallback, useEffect, useState } from "react";

import { useAuth } from "../context/useAuth.js";
import {
  getAlbumReviewReactions,
  toggleAlbumReviewReaction,
} from "../api/reactions.js";
import ReactionPicker from "./ReactionPicker.jsx";
import ReactionsList from "./ReactionsList.jsx";

export default function ReviewReactions({ reviewId, baseUrl }) {
  const { accessToken } = useAuth();
  const [reactions, setReactions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [optimisticReactions, setOptimisticReactions] = useState(null);
  const [lastError, setLastError] = useState(null);

  const loadReactions = useCallback(async () => {
    try {
      setIsLoading(true);
      setLastError(null);
      const data = await getAlbumReviewReactions({
        baseUrl,
        accessToken,
        reviewId,
      });
      setReactions(Array.isArray(data) ? data : []);
      setOptimisticReactions(null); // Clear optimistic state on successful load
    } catch (err) {
      console.error("Failed to load review reactions:", err);
      setLastError("Nu am putut încărca reacțiile");
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, baseUrl, reviewId]);

  useEffect(() => {
    // Defer initial load to avoid calling setState synchronously inside effect
    const id = setTimeout(() => {
      void loadReactions();
    }, 0);
    return () => clearTimeout(id);
  }, [loadReactions]);

  async function handleReactionClick(emoji) {
    // Optimistic update
    const optimistic = reactions.map((r) => {
      if (r.emoji === emoji) {
        return {
          ...r,
          user_reacted: !r.user_reacted,
          count: r.user_reacted ? r.count - 1 : r.count + 1,
        };
      }
      return r;
    });

    // Add new reaction if it doesn't exist
    if (!optimistic.find((r) => r.emoji === emoji)) {
      optimistic.push({ emoji, count: 1, user_reacted: true });
    }

    setOptimisticReactions(optimistic);

    try {
      await toggleAlbumReviewReaction({
        baseUrl,
        accessToken,
        reviewId,
        emoji,
      });
      // Reload to sync with server
      await loadReactions();
    } catch (err) {
      console.error("Failed to toggle review reaction:", err);
      setLastError("Eroare la reacție");
      // Revert optimistic update on error
      setOptimisticReactions(null);
      setReactions(reactions);
    }
  }

  const displayReactions = optimisticReactions || reactions;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        marginTop: "12px",
        flexWrap: "wrap",
      }}
    >
      <ReactionsList
        reactions={displayReactions}
        onReactionClick={handleReactionClick}
        isLoading={isLoading}
        isOptimistic={optimisticReactions !== null}
      />
      <ReactionPicker
        onSelectEmoji={handleReactionClick}
        isLoading={isLoading}
      />
      {lastError && (
        <span
          style={{
            fontSize: "12px",
            color: "var(--error-color)",
            width: "100%",
          }}
        >
          {lastError}
        </span>
      )}
    </div>
  );
}
