import React from "react";
import { ui } from "../ui/ui.js";

export default function AchievementCard({ achievement, userProgress = null }) {
  const isUnlocked = userProgress && userProgress.is_completed;
  const progress = userProgress ? userProgress.progress || 0 : 0;
  const target = achievement.target;
  const progressPercent =
    target > 0 ? Math.min((progress / target) * 100, 100) : 0;

  const typeColors = {
    streak: "#f39c12",
    milestone: "#3498db",
    social: "#e74c3c",
    discovery: "#2ecc71",
  };

  return (
    <div
      style={{
        ...ui.card,
        maxWidth: "300px",
        opacity: isUnlocked ? 1 : 0.6,
        borderLeft: `4px solid ${typeColors[achievement.type] || "#999"}`,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <div style={{ fontSize: "40px" }}>{achievement.emoji}</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: "bold", fontSize: "14px" }}>
            {achievement.name}
          </div>
          <div style={{ fontSize: "12px", color: "#666", marginTop: "4px" }}>
            {achievement.description}
          </div>
          <div style={{ fontSize: "11px", color: "#999", marginTop: "4px" }}>
            {achievement.points} XP
          </div>
        </div>
        <div style={{ textAlign: "center" }}>
          {isUnlocked ? (
            <div style={{ fontSize: "24px", color: "#2ecc71" }}>✓</div>
          ) : (
            <div style={{ fontSize: "12px", color: "#999" }}>
              {progress}/{target}
            </div>
          )}
        </div>
      </div>

      {!isUnlocked && target > 0 && (
        <div
          style={{
            marginTop: "12px",
            height: "4px",
            backgroundColor: "#eee",
            borderRadius: "2px",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              backgroundColor: typeColors[achievement.type] || "#999",
              width: `${progressPercent}%`,
              transition: "width 0.3s",
            }}
          />
        </div>
      )}
    </div>
  );
}
