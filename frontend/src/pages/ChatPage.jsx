import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { getChatMessages, postChatMessage } from "../api/chat.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

export default function ChatPage() {
  const {
    baseUrl,
    accessToken,
    isAuthenticated,
    isAuthVerified,
    logout,
    user,
  } = useAuth();

  const [messages, setMessages] = useState([]);
  const [content, setContent] = useState("");

  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);

  const listRef = useRef(null);

  function formatApiError(err, fallback) {
    const maybeStatus = err?.response?.status;
    const data = err?.response?.data;

    let details = "";
    if (typeof data === "string") {
      details = data;
    } else if (data && typeof data === "object") {
      if (typeof data.detail === "string") details = data.detail;
      else if (Array.isArray(data.content) && data.content[0]) {
        details = String(data.content[0]);
      } else if (typeof data.content === "string") {
        details = data.content;
      } else {
        try {
          details = JSON.stringify(data);
        } catch {
          details = "";
        }
      }
    }

    const base = fallback || "A apărut o eroare.";
    if (!maybeStatus && !details) return base;
    if (maybeStatus && details) return `${base} (${maybeStatus}) ${details}`;
    if (maybeStatus) return `${base} (${maybeStatus})`;
    return `${base} ${details}`;
  }

  const canLoad = useMemo(() => {
    return Boolean(isAuthVerified && accessToken);
  }, [isAuthVerified, accessToken]);

  useEffect(() => {
    let isCancelled = false;

    async function load() {
      if (!canLoad) {
        if (!isCancelled) {
          setMessages([]);
          setIsLoading(false);
          setError(null);
        }
        return;
      }

      if (!isCancelled) {
        setIsLoading(true);
        setError(null);
      }

      try {
        const data = await getChatMessages({
          baseUrl,
          accessToken,
          limit: 100,
        });
        if (!isCancelled) setMessages(Array.isArray(data) ? data : []);
      } catch (err) {
        const status = err?.response?.status;
        if (status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled)
          setError(formatApiError(err, "Nu am putut încărca mesajele."));
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      isCancelled = true;
    };
  }, [canLoad, baseUrl, accessToken, logout]);

  useEffect(() => {
    if (!listRef.current) return;
    // keep view scrolled to bottom when messages change
    listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages.length]);

  async function onSend(e) {
    e.preventDefault();
    if (!canLoad) return;

    const text = String(content || "").trim();
    if (!text) return;

    setIsSending(true);
    setError(null);

    try {
      const created = await postChatMessage({
        baseUrl,
        accessToken,
        content: text,
      });

      setMessages((prev) => {
        const next = Array.isArray(prev) ? [...prev] : [];
        if (created && created.id) next.push(created);
        return next;
      });
      setContent("");
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError(formatApiError(err, "Nu am putut trimite mesajul."));
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Chat</h1>

      {!isAuthenticated && (
        <div style={{ marginTop: "14px" }}>
          <p>Trebuie să fii logat ca să folosești chat-ul.</p>
          <p>
            <Link to="/login">Mergi la Login</Link>
          </p>
        </div>
      )}

      {isAuthenticated && isLoading && (
        <p style={{ marginTop: "14px" }}>Se încarcă...</p>
      )}

      {isAuthenticated && !isAuthVerified && (
        <p style={{ marginTop: "14px" }}>Se încarcă...</p>
      )}

      {isAuthVerified && error && (
        <p style={{ ...ui.errorText, marginTop: "14px" }} role="alert">
          {error}
        </p>
      )}

      {isAuthVerified && !isLoading && (
        <div style={{ ...ui.card, marginTop: "14px" }}>
          <div
            ref={listRef}
            style={{
              height: 360,
              overflowY: "auto",
              padding: "8px",
              border: `1px solid ${ui.colors.border}`,
              borderRadius: 8,
            }}
            aria-live="polite"
          >
            {messages.length ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {messages.map((m) => {
                  const isMine =
                    user &&
                    m &&
                    m.user_id &&
                    Number(m.user_id) === Number(user.id);

                  return (
                    <div
                      key={m.id}
                      style={{
                        alignSelf: isMine ? "flex-end" : "flex-start",
                        maxWidth: "85%",
                        padding: "8px 10px",
                        borderRadius: 10,
                        border: `1px solid ${ui.colors.border}`,
                      }}
                    >
                      <div style={{ opacity: 0.85, fontSize: 13 }}>
                        {m.username}
                      </div>
                      <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ opacity: 0.9 }}>Încă nu există mesaje.</div>
            )}
          </div>

          <form onSubmit={onSend} style={{ marginTop: 10 }}>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                type="text"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Scrie un mesaj..."
                style={{ ...ui.input, flex: 1 }}
                maxLength={1000}
                disabled={isSending}
              />
              <button type="submit" style={ui.button} disabled={isSending}>
                {isSending ? "Se trimite..." : "Trimite"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
