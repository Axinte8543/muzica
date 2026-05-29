import { useState } from "react";
import "./ReactionPicker.css";

const EMOJI_OPTIONS = ["👍", "❤️", "😂", "😮", "😢", "🔥", "👏", "🎉"];

export default function ReactionPicker({ onSelectEmoji, isLoading }) {
  const [isOpen, setIsOpen] = useState(false);

  const handleEmojiClick = (emoji) => {
    onSelectEmoji(emoji);
    setIsOpen(false);
  };

  return (
    <div className="reaction-picker">
      <button
        className="reaction-picker-btn"
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        title="Add reaction"
      >
        😊
      </button>

      {isOpen && (
        <div className="reaction-picker-menu">
          {EMOJI_OPTIONS.map((emoji) => (
            <button
              key={emoji}
              className="emoji-btn"
              onClick={() => handleEmojiClick(emoji)}
              disabled={isLoading}
              title={emoji}
            >
              {emoji}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
