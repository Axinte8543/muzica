import "./ReactionsList.css";

export default function ReactionsList({
  reactions,
  onReactionClick,
  isLoading,
}) {
  if (!reactions || reactions.length === 0) {
    return null;
  }

  return (
    <div className="reactions-list">
      {reactions.map((reaction) => (
        <button
          type="button"
          aria-pressed={Boolean(reaction.user_reacted)}
          key={reaction.emoji}
          className={`reaction-item ${reaction.user_reacted ? "active" : ""}`}
          onClick={() => onReactionClick(reaction.emoji)}
          disabled={isLoading}
          title={`${reaction.count} ${reaction.emoji}`}
        >
          <span className="reaction-emoji">{reaction.emoji}</span>
          <span className="reaction-count">{reaction.count}</span>
        </button>
      ))}
    </div>
  );
}
