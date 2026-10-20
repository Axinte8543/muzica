import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "../context/useAuth.js";
import { trackAnalyticsEvent } from "../api/analytics.js";
import { getFriendsList } from "../api/friends.js";
import {
  getConversations,
  getTypingStatus,
  getMessagesWithUser,
  setTypingStatus,
  sendMessageToUser,
} from "../api/chat.js";
import ConversationsList from "../components/ConversationsList.jsx";
import ChatWindow from "../components/ChatWindow.jsx";
import "./MessagesPage.css";

export default function MessagesPage() {
  const { isAuthVerified, accessToken, baseUrl, logout, user } = useAuth();

  const [conversations, setConversations] = useState([]);
  const [friends, setFriends] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [friendSearchValue, setFriendSearchValue] = useState("");

  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isLoadingFriends, setIsLoadingFriends] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isOtherUserTyping, setIsOtherUserTyping] = useState(false);
  const [replyToMessage, setReplyToMessage] = useState(null);
  const [, setError] = useState(null);
  const [friendsError, setFriendsError] = useState(null);

  // Load conversations
  useEffect(() => {
    if (!isAuthVerified || !accessToken) return;

    const loadConversations = async () => {
      try {
        setIsLoadingConversations(true);
        setError(null);
        const data = await getConversations({ baseUrl, accessToken });
        setConversations(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error(err);
        if (err?.response?.status === 401) {
          logout();
        } else {
          setError("Nu am putut încărca conversațiile.");
        }
      } finally {
        setIsLoadingConversations(false);
      }
    };

    loadConversations();
  }, [isAuthVerified, accessToken, baseUrl, logout]);

  useEffect(() => {
    if (!isAuthVerified || !accessToken) {
      const t = setTimeout(() => {
        setFriends([]);
        setIsLoadingFriends(false);
        setFriendsError(null);
      }, 0);
      return () => clearTimeout(t);
    }

    const loadFriends = async () => {
      try {
        setIsLoadingFriends(true);
        setFriendsError(null);
        const data = await getFriendsList({ baseUrl, accessToken });
        setFriends(
          Array.isArray(data?.friends?.results) ? data.friends.results : [],
        );
      } catch (err) {
        console.error(err);
        if (err?.response?.status === 401) {
          logout();
        } else {
          setFriendsError("Nu am putut încărca lista de prieteni.");
        }
      } finally {
        setIsLoadingFriends(false);
      }
    };

    loadFriends();
  }, [isAuthVerified, accessToken, baseUrl, logout]);

  const loadMessages = useCallback(
    async ({ silent = false } = {}) => {
      if (!isAuthVerified || !accessToken || !selectedUserId) {
        setMessages([]);
        return;
      }

      try {
        if (!silent) {
          setIsLoadingMessages(true);
        }
        setError(null);
        const data = await getMessagesWithUser({
          baseUrl,
          accessToken,
          userId: selectedUserId,
        });
        setMessages(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error(err);
        if (err?.response?.status === 401) {
          logout();
        } else {
          setError("Nu am putut încărca mesajele.");
        }
      } finally {
        if (!silent) {
          setIsLoadingMessages(false);
        }
      }
    },
    [selectedUserId, isAuthVerified, accessToken, baseUrl, logout],
  );

  // Load and poll messages when selected user changes
  useEffect(() => {
    if (!selectedUserId) {
      const t = setTimeout(() => {
        setMessages([]);
        setReplyToMessage(null);
      }, 0);
      return () => clearTimeout(t);
    }

    const t = setTimeout(() => {
      void loadMessages();
    }, 0);
    const intervalId = setInterval(() => {
      void loadMessages({ silent: true });
    }, 3000);

    return () => {
      clearTimeout(t);
      clearInterval(intervalId);
    };
  }, [selectedUserId, loadMessages]);

  useEffect(() => {
    if (!selectedUserId || !isAuthVerified || !accessToken) return;
    void trackAnalyticsEvent({
      baseUrl,
      accessToken,
      eventName: "dm_open",
      targetType: "dm_thread",
      targetId: selectedUserId,
      properties: {
        source: "messages_page",
      },
    }).catch(() => {});
  }, [accessToken, baseUrl, isAuthVerified, selectedUserId]);

  // Poll typing status for selected conversation
  useEffect(() => {
    if (!selectedUserId || !isAuthVerified || !accessToken) {
      const t = setTimeout(() => {
        setIsOtherUserTyping(false);
      }, 0);
      return () => clearTimeout(t);
    }

    let cancelled = false;
    const checkTyping = async () => {
      try {
        const data = await getTypingStatus({
          baseUrl,
          accessToken,
          userId: selectedUserId,
        });
        if (!cancelled) {
          setIsOtherUserTyping(Boolean(data?.is_typing));
        }
      } catch {
        if (!cancelled) {
          setIsOtherUserTyping(false);
        }
      }
    };

    void checkTyping();
    const intervalId = setInterval(() => {
      void checkTyping();
    }, 2000);

    return () => {
      cancelled = true;
      clearInterval(intervalId);

      // Best effort: clear typing when leaving current conversation.
      void setTypingStatus({
        baseUrl,
        accessToken,
        userId: selectedUserId,
        isTyping: false,
      }).catch(() => {});
    };
  }, [selectedUserId, isAuthVerified, accessToken, baseUrl]);

  const selectedUserIdKey = String(selectedUserId ?? "");

  const selectedFriend = useMemo(() => {
    return (
      friends.find(
        (friend) => String(friend?.id ?? "") === selectedUserIdKey,
      ) || null
    );
  }, [friends, selectedUserIdKey]);

  const selectedConversation = useMemo(() => {
    const existingConversation =
      conversations.find(
        (conversation) =>
          String(conversation?.user_id ?? "") === selectedUserIdKey,
      ) || null;

    if (existingConversation) {
      return existingConversation;
    }

    if (!selectedFriend) {
      return null;
    }

    return {
      user_id: selectedFriend.id,
      username: selectedFriend.username,
      last_message: "",
      last_message_at: new Date().toISOString(),
      unread_count: 0,
      is_from_current_user: false,
    };
  }, [conversations, selectedFriend, selectedUserIdKey]);

  const handleSendMessage = async (content, replyToId = null) => {
    if (!selectedUserId || !content.trim()) return;

    try {
      setIsSending(true);
      setError(null);
      const newMessage = await sendMessageToUser({
        baseUrl,
        accessToken,
        userId: selectedUserId,
        content,
        replyToId,
      });

      const now = new Date().toISOString();
      const conversationUsername =
        selectedConversation?.username || selectedFriend?.username || "User";

      // Add to messages list
      setMessages((prev) => [...prev, newMessage]);

      // Update conversations list - move to top and update last message
      setConversations((prev) => {
        const nextConversation = {
          user_id: selectedUserId,
          username: conversationUsername,
          last_message: content,
          last_message_at: now,
          unread_count: 0,
          is_from_current_user: true,
        };

        const existingIndex = prev.findIndex(
          (conv) => conv.user_id === selectedUserId,
        );

        if (existingIndex === -1) {
          return [nextConversation, ...prev];
        }

        const updated = prev.map((conv) =>
          conv.user_id === selectedUserId
            ? {
                ...conv,
                last_message: content,
                last_message_at: now,
                is_from_current_user: true,
              }
            : conv,
        );

        const conv = updated.find((c) => c.user_id === selectedUserId);
        if (conv) {
          updated.splice(updated.indexOf(conv), 1);
          updated.unshift(conv);
        }

        return updated;
      });

      setReplyToMessage(null);
      setIsOtherUserTyping(false);
    } catch (err) {
      console.error(err);
      if (err?.response?.status === 401) {
        logout();
      } else {
        setError("Nu am putut trimite mesajul.");
      }
    } finally {
      setIsSending(false);
    }
  };

  const handleTypingChange = async (isTyping) => {
    if (!selectedUserId || !isAuthVerified || !accessToken) return;
    try {
      await setTypingStatus({
        baseUrl,
        accessToken,
        userId: selectedUserId,
        isTyping,
      });
    } catch {
      // Keep typing updates best-effort to avoid noisy UI errors.
    }
  };

  if (!isAuthVerified) {
    return (
      <div className="messages-page">
        <div style={{ padding: "2rem", textAlign: "center" }}>
          <h1 style={{ marginTop: 0 }}>Mesaje</h1>
          <p>Te rugăm să te autentifici pentru a accesa mesajele.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="messages-page">
      <h1 style={{ margin: "0 0 1rem" }}>Mesaje</h1>
      <div className="messages-container">
        <ConversationsList
          conversations={conversations}
          friends={friends}
          selectedUserId={selectedUserId}
          onSelectUser={setSelectedUserId}
          isLoading={isLoadingConversations}
          isLoadingFriends={isLoadingFriends}
          friendsError={friendsError}
          friendSearchValue={friendSearchValue}
          onFriendSearchChange={setFriendSearchValue}
        />
        <ChatWindow
          conversation={selectedConversation}
          messages={messages}
          isLoading={isLoadingMessages}
          isSending={isSending}
          onSendMessage={handleSendMessage}
          onTypingChange={handleTypingChange}
          onReplyToMessage={setReplyToMessage}
          replyToMessage={replyToMessage}
          isOtherUserTyping={isOtherUserTyping}
          currentUserId={user?.id ?? user?.user_id ?? user?.pk}
        />
      </div>
    </div>
  );
}
