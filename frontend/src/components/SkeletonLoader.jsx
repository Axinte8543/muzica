import { useState, useEffect } from "react";
import "./SkeletonLoader.css";

/**
 * Reusable skeleton loader component with shimmer animation
 */
export default function SkeletonLoader({
  variant = "card",
  count = 1,
  height = 100,
}) {
  // Compute message widths after mount to avoid calling impure Math.random() during render
  const [messageWidths, setMessageWidths] = useState(() => {
    if (variant !== "message") return null;
    // initial fallback widths to avoid layout jank on first paint
    return Array.from({ length: count }).map(() => "60%");
  });

  useEffect(() => {
    let timer = null;
    if (variant !== "message") {
      // Defer to avoid synchronous setState inside effect
      timer = setTimeout(() => setMessageWidths(null), 0);
      return () => clearTimeout(timer);
    }
    timer = setTimeout(() => {
      const widths = Array.from({ length: count }).map(
        () => `${40 + Math.random() * 40}%`,
      );
      setMessageWidths(widths);
    }, 0);
    return () => clearTimeout(timer);
  }, [variant, count]);
  if (variant === "card") {
    return (
      <div className="skeleton-container">
        {Array.from({ length: count }).map((_, idx) => (
          <div key={idx} className="skeleton-card">
            <div className="skeleton-image" />
            <div className="skeleton-text skeleton-text-title" />
            <div className="skeleton-text skeleton-text-subtitle" />
          </div>
        ))}
      </div>
    );
  }

  if (variant === "review") {
    return (
      <div className="skeleton-container">
        {Array.from({ length: count }).map((_, idx) => (
          <div key={idx} className="skeleton-review">
            <div className="skeleton-avatar" />
            <div style={{ flex: 1 }}>
              <div className="skeleton-text skeleton-text-title" />
              <div className="skeleton-text skeleton-text-body" />
              <div
                className="skeleton-text skeleton-text-body"
                style={{ width: "80%" }}
              />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (variant === "comment") {
    return (
      <div className="skeleton-container">
        {Array.from({ length: count }).map((_, idx) => (
          <div key={idx} className="skeleton-comment">
            <div className="skeleton-avatar-small" />
            <div style={{ flex: 1 }}>
              <div
                className="skeleton-text skeleton-text-title"
                style={{ width: "40%" }}
              />
              <div className="skeleton-text skeleton-text-body" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (variant === "message") {
    // Use the top-level `messageWidths` computed with `useMemo`
    return (
      <div className="skeleton-container">
        {Array.from({ length: count }).map((_, idx) => (
          <div
            key={idx}
            className="skeleton-message"
            style={{
              justifyContent: idx % 2 === 0 ? "flex-start" : "flex-end",
            }}
          >
            <div
              className="skeleton-text"
              style={{
                width: messageWidths ? messageWidths[idx] : "60%",
                maxWidth: "200px",
                height: "24px",
              }}
            />
          </div>
        ))}
      </div>
    );
  }

  // Default text skeleton
  return (
    <div className="skeleton-container">
      {Array.from({ length: count }).map((_, idx) => (
        <div
          key={idx}
          className="skeleton-text"
          style={{ height: `${height}px` }}
        />
      ))}
    </div>
  );
}
