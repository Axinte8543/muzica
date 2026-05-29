import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ui } from "../ui/ui.js";
import { NoticeContext } from "./NoticeContext.js";

function NoticeHost({ notice, dismiss }) {
  if (!notice) return null;

  const isError = notice.type === "error";

  return (
    <div
      style={{
        position: "fixed",
        top: 12,
        left: 0,
        right: 0,
        zIndex: 1000,
        pointerEvents: "none",
        padding: "0 12px",
      }}
      aria-live={isError ? "assertive" : "polite"}
      role={isError ? "alert" : "status"}
    >
      <div
        style={{
          maxWidth: 920,
          margin: "0 auto",
          pointerEvents: "auto",
        }}
      >
        <div style={{ ...ui.card, ...(isError ? ui.errorText : null) }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: 12,
            }}
          >
            <div style={{ whiteSpace: "pre-wrap" }}>{notice.message}</div>
            <button
              type="button"
              onClick={() => dismiss()}
              style={{
                ...ui.buttonSmall,
                padding: "2px 8px",
                lineHeight: 1.2,
              }}
              aria-label="Închide"
            >
              ×
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * A single global notice/toast.
 * - Supports `success` and `error`.
 * - Dedupes identical messages to prevent spam from parallel requests.
 * - Auto-dismisses `success` after a short delay.
 */
export function NoticeProvider({ children }) {
  const [notice, setNotice] = useState(null);
  const lastMessageRef = useRef(null);
  const autoDismissTimerRef = useRef(null);

  const dismiss = useCallback((options) => {
    const scope = options?.scope || null;

    setNotice((current) => {
      if (!current) return null;
      if (scope && current.scope !== scope) return current;
      return null;
    });

    lastMessageRef.current = null;

    if (autoDismissTimerRef.current) {
      window.clearTimeout(autoDismissTimerRef.current);
      autoDismissTimerRef.current = null;
    }
  }, []);

  const notify = useCallback(
    (input) => {
      const type = input?.type || "success";
      const message = input?.message || "";
      const scope = input?.scope || null;

      if (!message) return;

      const fingerprint = `${type}:${scope || "_"}:${message}`;
      if (lastMessageRef.current === fingerprint) return;

      lastMessageRef.current = fingerprint;

      if (autoDismissTimerRef.current) {
        window.clearTimeout(autoDismissTimerRef.current);
        autoDismissTimerRef.current = null;
      }

      setNotice({ type, message, scope });

      if (type === "success") {
        autoDismissTimerRef.current = window.setTimeout(() => {
          dismiss({ scope });
        }, 2500);
      }
    },
    [dismiss],
  );

  useEffect(() => {
    return () => {
      if (autoDismissTimerRef.current) {
        window.clearTimeout(autoDismissTimerRef.current);
        autoDismissTimerRef.current = null;
      }
    };
  }, []);

  const value = useMemo(() => {
    return {
      notice,
      notify,
      dismiss,
    };
  }, [notice, notify, dismiss]);

  return (
    <NoticeContext.Provider value={value}>
      <NoticeHost notice={notice} dismiss={dismiss} />
      {children}
    </NoticeContext.Provider>
  );
}
