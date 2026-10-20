import { useEffect, useRef, useState } from "react";
import SkeletonLoader from "./SkeletonLoader.jsx";

export default function ChatWindow({
  conversation,
  messages,
  isLoading,
  isSending,
  onSendMessage,
  onTypingChange,
  onReplyToMessage,
  replyToMessage,
  isOtherUserTyping,
  currentUserId,
}) {
  const [inputValue, setInputValue] = useState("");
  const [visibleCount, setVisibleCount] = useState(10);
  const messagesEndRef = useRef(null);
  const typingTimeoutRef = useRef(null);
  const normalizedCurrentUserId = Number(currentUserId);

  const prevMessagesLengthRef = useRef(messages.length);
  useEffect(() => {
    const endEl = messagesEndRef.current;
    const container = endEl?.parentElement;
    const prevLen = prevMessagesLengthRef.current ?? 0;
    const newLen = messages.length;

    const tolerance = 50; // px from bottom to consider "at bottom"
    const isAtBottom = () => {
      if (!container) return false;
      return (
        container.scrollHeight - container.clientHeight - container.scrollTop <=
        tolerance
      );
    };

    const lastMsg = messages[newLen - 1];

    const shouldScroll = (() => {
      if (prevLen === 0) return false;
      if (newLen > prevLen) {
        if (lastMsg && Number(lastMsg.sender_id) === normalizedCurrentUserId) {
          return true;
        }
        return isAtBottom();
      }
      return false;
    })();

    if (shouldScroll) {
      endEl?.scrollIntoView({ behavior: "smooth" });
    }

    prevMessagesLengthRef.current = newLen;
  }, [messages, normalizedCurrentUserId]);

  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  const handleSend = (e) => {
    e.preventDefault();
    if (inputValue.trim() && !isSending) {
      onSendMessage(inputValue, replyToMessage?.id ?? null);
      setInputValue("");
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
        typingTimeoutRef.current = null;
      }
      onTypingChange?.(false);
    }
  };

  const handleInputChange = (e) => {
    setInputValue(e.target.value);
    onTypingChange?.(true);

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    typingTimeoutRef.current = setTimeout(() => {
      onTypingChange?.(false);
      typingTimeoutRef.current = null;
    }, 1200);
  };

  const latestSentMessageId = [...messages]
    .reverse()
    .find((msg) => Number(msg.sender_id) === normalizedCurrentUserId)?.id;

  if (!conversation) {
    return (
      <div className="chat-window">
        <div className="chat-empty">
          Selectează o conversație pentru a vedea mesajele
        </div>
      </div>
    );
  }

  return (
    <div className="chat-window">
      <div className="chat-header">{conversation.username}</div>

      <div className="chat-messages">
        {isLoading ? (
          <SkeletonLoader variant="message" count={5} />
        ) : messages.length === 0 ? (
          <div className="chat-empty">
            Nicio conversație încă. Trimite un mesaj pentru a începe!
          </div>
        ) : (
          <>
            {messages.length > visibleCount ? (
              <div className="load-more-wrapper">
                <button
                  type="button"
                  className="load-more-btn"
                  onClick={() => {
                    const endEl = messagesEndRef.current;
                    const container = endEl?.parentElement;
                    const prevScroll = container ? container.scrollHeight : 0;
                    setVisibleCount((v) => v + 10);
                    requestAnimationFrame(() => {
                      if (!container) return;
                      container.scrollTop = container.scrollHeight - prevScroll;
                    });
                  }}
                >
                  Încarcă mesaje vechi ({messages.length - visibleCount})
                </button>
              </div>
            ) : null}

            {messages
              .slice(Math.max(0, messages.length - visibleCount))
              .map((msg) => {
                const isSent =
                  Number(msg.sender_id) === normalizedCurrentUserId;
                const isLatestSent = isSent && msg.id === latestSentMessageId;
                return (
                  <div
                    key={msg.id}
                    className={`message ${isSent ? "sent" : "received"}`}
                  >
                    <div className="message-content">
                      {msg.reply_to_id ? (
                        <button
                          type="button"
                          className="message-reply-preview"
                          onClick={() =>
                            onReplyToMessage?.({
                              id: msg.reply_to_id,
                              content: msg.reply_to_content,
                              sender_username: msg.reply_to_sender_username,
                            })
                          }
                          title="Răspunde la acest mesaj"
                        >
                          ↩ {msg.reply_to_sender_username}:{" "}
                          {msg.reply_to_content}
                        </button>
                      ) : null}

                      <div className="message-bubble">{msg.content}</div>
                      <div className="message-meta-row">
                        <div className="message-timestamp">
                          {new Date(msg.created_at).toLocaleTimeString(
                            "ro-RO",
                            {
                              hour: "2-digit",
                              minute: "2-digit",
                            },
                          )}
                        </div>
                        {isLatestSent ? (
                          <div className="message-seen-status">
                            {msg.is_read ? "Seen" : "Sent"}
                          </div>
                        ) : null}
                        <button
                          type="button"
                          className="message-reply-action"
                          onClick={() =>
                            onReplyToMessage?.({
                              id: msg.id,
                              content: msg.content,
                              sender_username: msg.sender_username,
                            })
                          }
                        >
                          Reply
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            {isOtherUserTyping ? (
              <div className="typing-indicator">
                {conversation.username} scrie...
              </div>
            ) : null}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {replyToMessage?.id ? (
        <div className="chat-reply-bar">
          <div className="chat-reply-text">
            Răspunzi la <strong>{replyToMessage.sender_username}</strong>:{" "}
            {replyToMessage.content}
          </div>
          <button
            type="button"
            className="chat-reply-cancel"
            onClick={() => onReplyToMessage?.(null)}
          >
            Anulează
          </button>
        </div>
      ) : null}

      <form className="chat-input-area" onSubmit={handleSend}>
        <div className="chat-input-wrapper">
          <textarea
            className="chat-input"
            value={inputValue}
            onChange={handleInputChange}
            placeholder="Scrie un mesaj..."
            disabled={isSending}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend(e);
              }
            }}
          />
        </div>
        <button
          type="submit"
          className="chat-send-btn"
          disabled={isSending || !inputValue.trim()}
        >
          {isSending ? "..." : "Trimite"}
        </button>
      </form>
    </div>
  );
}
