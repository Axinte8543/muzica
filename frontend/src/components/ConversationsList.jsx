import { useMemo } from "react";

export default function ConversationsList({
  conversations,
  friends,
  selectedUserId,
  onSelectUser,
  isLoading,
  isLoadingFriends,
  friendsError,
  friendSearchValue,
  onFriendSearchChange,
}) {
  const normalizedSearch = String(friendSearchValue || "")
    .trim()
    .toLowerCase();

  const conversationsByUserId = useMemo(() => {
    const map = new Map();
    (Array.isArray(conversations) ? conversations : []).forEach((conv) => {
      map.set(String(conv?.user_id ?? ""), conv);
    });
    return map;
  }, [conversations]);

  const filteredFriends = useMemo(() => {
    const list = Array.isArray(friends) ? friends : [];
    const sorted = [...list].sort((a, b) =>
      String(a?.username || "").localeCompare(String(b?.username || ""), "ro"),
    );

    if (!normalizedSearch) {
      return sorted;
    }

    return sorted.filter((friend) =>
      String(friend?.username || "")
        .toLowerCase()
        .includes(normalizedSearch),
    );
  }, [friends, normalizedSearch]);

  const renderConversationItem = (conv, subtitle, badge) => (
    <div
      key={conv.user_id}
      className={`conversation-item ${selectedUserId === conv.user_id ? "active" : ""}`}
      onClick={() => onSelectUser(conv.user_id)}
    >
      <div className="conversation-info">
        <div className="conversation-info-username">{conv.username}</div>
        <div className="conversation-info-message">{subtitle}</div>
      </div>
      {badge}
    </div>
  );

  if (isLoading) {
    return (
      <div className="conversations-list">
        <div className="conversations-list-header">
          <div className="conversations-list-title">Conversații</div>
          <input
            type="search"
            className="conversations-search-input"
            placeholder="Caută prieteni..."
            value={friendSearchValue}
            onChange={(e) => onFriendSearchChange?.(e.target.value)}
          />
        </div>
        <div className="conversations-list-content">
          <div className="conversations-empty">Se încarcă...</div>
        </div>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="conversations-list">
        <div className="conversations-list-header">
          <div className="conversations-list-title">Conversații</div>
          <input
            type="search"
            className="conversations-search-input"
            placeholder="Caută prieteni..."
            value={friendSearchValue}
            onChange={(e) => onFriendSearchChange?.(e.target.value)}
          />
        </div>
        <div className="conversations-list-content">
          {isLoadingFriends ? (
            <div className="conversations-empty">Se încarcă prietenii...</div>
          ) : friendsError ? (
            <div className="conversations-empty" role="alert">
              {friendsError}
            </div>
          ) : filteredFriends.length ? (
            filteredFriends.map((friend) => {
              const conversation = conversationsByUserId.get(
                String(friend?.id ?? ""),
              );
              const badge =
                conversation?.unread_count > 0 ? (
                  <div className="conversation-unread-badge">
                    {conversation.unread_count}
                  </div>
                ) : null;

              return renderConversationItem(
                {
                  user_id: friend.id,
                  username: friend.username,
                },
                conversation?.last_message || "Prieten · apasă pentru mesaj",
                badge,
              );
            })
          ) : (
            <div className="conversations-empty">
              Nu ai prieteni. Mergi la{" "}
              <a
                href="/profile/friends"
                style={{ color: "inherit", textDecoration: "underline" }}
              >
                secțiunea prieteni
              </a>{" "}
              pentru a adăuga.
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="conversations-list">
      <div className="conversations-list-header">
        <div className="conversations-list-title">Conversații</div>
        <input
          type="search"
          className="conversations-search-input"
          placeholder="Caută prieteni..."
          value={friendSearchValue}
          onChange={(e) => onFriendSearchChange?.(e.target.value)}
        />
      </div>
      <div className="conversations-list-content">
        {normalizedSearch ? (
          isLoadingFriends ? (
            <div className="conversations-empty">Se încarcă prietenii...</div>
          ) : friendsError ? (
            <div className="conversations-empty" role="alert">
              {friendsError}
            </div>
          ) : filteredFriends.length ? (
            filteredFriends.map((friend) => {
              const conversation = conversationsByUserId.get(
                String(friend?.id ?? ""),
              );
              const badge =
                conversation?.unread_count > 0 ? (
                  <div className="conversation-unread-badge">
                    {conversation.unread_count}
                  </div>
                ) : null;

              return renderConversationItem(
                {
                  user_id: friend.id,
                  username: friend.username,
                },
                conversation
                  ? `${conversation.is_from_current_user ? "Tu: " : ""}${conversation.last_message}`
                  : "Prieten · apasă pentru mesaj",
                badge,
              );
            })
          ) : (
            <div className="conversations-empty">Niciun prieten găsit.</div>
          )
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.user_id}
              className={`conversation-item ${
                selectedUserId === conv.user_id ? "active" : ""
              }`}
              onClick={() => onSelectUser(conv.user_id)}
            >
              <div className="conversation-info">
                <div className="conversation-info-username">
                  {conv.username}
                </div>
                <div className="conversation-info-message">
                  {conv.is_from_current_user && "Tu: "}
                  {conv.last_message}
                </div>
              </div>
              {conv.unread_count > 0 && (
                <div className="conversation-unread-badge">
                  {conv.unread_count}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
