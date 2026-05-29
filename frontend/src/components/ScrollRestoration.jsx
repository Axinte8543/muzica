import { useEffect, useLayoutEffect } from "react";
import { useLocation, useNavigationType } from "react-router-dom";

function getScrollKey(locationKey) {
  return `scroll:${locationKey}`;
}

function safeParseInt(value) {
  const n = Number.parseInt(value, 10);
  return Number.isFinite(n) ? n : 0;
}

export default function ScrollRestoration() {
  const location = useLocation();
  const navigationType = useNavigationType();

  // Save scroll for the current history entry when we navigate away.
  useEffect(() => {
    const key = location.key;

    return () => {
      try {
        sessionStorage.setItem(getScrollKey(key), String(window.scrollY));
      } catch {
        // ignore storage failures
      }
    };
  }, [location.key]);

  // Restore scroll on POP (Back/Forward); otherwise scroll to top.
  useLayoutEffect(() => {
    const key = location.key;

    if (navigationType === "POP") {
      let y = 0;
      try {
        y = safeParseInt(sessionStorage.getItem(getScrollKey(key)));
      } catch {
        y = 0;
      }
      window.scrollTo(0, y);
      return;
    }

    window.scrollTo(0, 0);
  }, [location.key, navigationType]);

  return null;
}
