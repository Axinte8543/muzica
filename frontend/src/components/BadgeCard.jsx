import React from "react";
import { ui } from "../ui/ui.js";

export default function BadgeCard({ badge, earned = false, size = "medium" }) {
  const sizeStyles = {
    small: { fontSize: "24px", padding: "8px", borderRadius: "8px" },
    medium: { fontSize: "32px", padding: "12px", borderRadius: "12px" },
    large: { fontSize: "48px", padding: "16px", borderRadius: "16px" },
  };

  const rarityColors = {
    common: "#808080",
    uncommon: "#1abc9c",
    rare: "#3498db",
    epic: "#9b59b6",
    legendary: "#f39c12",
  };

  const style = {
    ...ui.card,
    ...sizeStyles[size],
    textAlign: "center",
    opacity: earned ? 1 : 0.4,
    border: `2px solid ${rarityColors[badge.rarity] || "#999"}`,
    cursor: earned ? "pointer" : "default",
    transition: "transform 0.2s",
  };

  return (
    <div
      style={style}
      title={badge.name}
      onMouseEnter={(e) => {
        if (earned) e.currentTarget.style.transform = "scale(1.05)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = "scale(1)";
      }}
    >
      <div style={{ fontSize: sizeStyles[size].fontSize }}>{badge.emoji}</div>
      <div style={{ fontSize: "12px", marginTop: "4px", fontWeight: "bold" }}>
        {badge.name}
      </div>
      <div style={{ fontSize: "10px", marginTop: "2px", color: "#666" }}>
        {badge.category}
      </div>
    </div>
  );
}
