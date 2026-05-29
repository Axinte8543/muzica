import { useCallback, useEffect, useState } from "react";
import ReactionPicker from "./ReactionPicker.jsx";
import ReactionsList from "./ReactionsList.jsx";
import { useAuth } from "../context/useAuth.js";
import {
  getReviewCommentReactions,
  toggleReviewCommentReaction,
} from "../api/reactions.js";

export default function ReviewCommentReactions({ commentId, baseUrl }) {
  const { accessToken } = useAuth();
  const [reactions, setReactions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadReactions = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await getReviewCommentReactions({
        baseUrl,
        accessToken,
        commentId,
      });
      setReactions(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to load reactions:", err);
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, baseUrl, commentId]);

  useEffect(() => {
    void loadReactions();
  }, [loadReactions]);

  async function handleReactionClick(emoji) {
    try {
      setIsLoading(true);
      await toggleReviewCommentReaction({
        baseUrl,
        accessToken,
        commentId,
        emoji,
      });
      await loadReactions();
    } catch (err) {
      console.error("Failed to toggle reaction:", err);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
        marginTop: "0.5rem",
      }}
    >
      <ReactionsList
        reactions={reactions}
        onReactionClick={handleReactionClick}
        isLoading={isLoading}
      />
      <ReactionPicker
        onSelectEmoji={handleReactionClick}
        isLoading={isLoading}
      />
    </div>
  );
}
