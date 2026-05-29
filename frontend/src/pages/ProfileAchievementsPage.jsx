import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import ProfileNav from "../components/ProfileNav.jsx";
import AchievementCard from "../components/AchievementCard.jsx";
import { getMyAchievements, getAllAchievements } from "../api/gamification.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

export default function ProfileAchievementsPage() {
  const { isAuthenticated, isAuthVerified, logout } = useAuth();
  const [myAchievements, setMyAchievements] = useState([]);
  const [allAchievements, setAllAchievements] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedType, setSelectedType] = useState(null);
  const [filter, setFilter] = useState("all"); // all, unlocked, in-progress

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!isAuthenticated || !isAuthVerified) return;

      setIsLoading(true);
      setError(null);
      try {
        const [myData, allData] = await Promise.all([
          getMyAchievements(),
          getAllAchievements(),
        ]);

        if (cancelled) return;

        setMyAchievements(Array.isArray(myData) ? myData : []);
        setAllAchievements(Array.isArray(allData) ? allData : []);
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!cancelled) {
          setError("Nu am putut încărca realizările.");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, isAuthVerified, logout]);

  if (!isAuthenticated) {
    return (
      <div>
        <ProfileNav />
        <div style={{ padding: "24px" }}>
          <h1 style={{ marginTop: 0 }}>Realizările mele</h1>
          <p>Trebuie să fii logat ca să vezi realizările tale.</p>
          <p>
            <Link to="/login">Mergi la Login</Link>
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthVerified) {
    return (
      <div>
        <ProfileNav />
        <div style={{ padding: "24px" }}>
          <h1 style={{ marginTop: 0 }}>Realizările mele</h1>
          <p style={{ marginTop: "14px" }}>Se încarcă...</p>
        </div>
      </div>
    );
  }

  // Map user achievements by id for quick lookup
  const myAchievementMap = {};
  myAchievements.forEach((ua) => {
    myAchievementMap[ua.achievement.id] = ua;
  });

  const types = [...new Set(allAchievements.map((a) => a.type))].sort();

  let displayedAchievements = allAchievements;

  if (selectedType) {
    displayedAchievements = displayedAchievements.filter(
      (a) => a.type === selectedType,
    );
  }

  if (filter === "unlocked") {
    displayedAchievements = displayedAchievements.filter(
      (a) => myAchievementMap[a.id]?.is_completed,
    );
  } else if (filter === "in-progress") {
    displayedAchievements = displayedAchievements.filter(
      (a) => myAchievementMap[a.id] && !myAchievementMap[a.id]?.is_completed,
    );
  }

  const unlockedCount = myAchievements.filter((a) => a.is_completed).length;
  const inProgressCount = myAchievements.filter((a) => !a.is_completed).length;

  return (
    <div>
      <ProfileNav />
      <div style={{ padding: "24px" }}>
        <h1 style={{ marginTop: 0 }}>Realizările mele</h1>

        {isLoading && <p>Se încarcă...</p>}
        {error && (
          <p style={{ ...ui.errorText, marginTop: "14px" }} role="alert">
            {error}
          </p>
        )}

        {!isLoading && !error && (
          <>
            <div
              style={{
                display: "flex",
                gap: "20px",
                marginTop: "20px",
                flexWrap: "wrap",
              }}
            >
              <div style={{ ...ui.card }}>
                <div style={{ fontSize: "20px", fontWeight: "bold" }}>
                  {unlockedCount}
                </div>
                <div style={{ fontSize: "12px", color: "#666" }}>
                  Desblocate
                </div>
              </div>
              <div style={{ ...ui.card }}>
                <div style={{ fontSize: "20px", fontWeight: "bold" }}>
                  {inProgressCount}
                </div>
                <div style={{ fontSize: "12px", color: "#666" }}>
                  În progres
                </div>
              </div>
              <div style={{ ...ui.card }}>
                <div style={{ fontSize: "20px", fontWeight: "bold" }}>
                  {allAchievements.length}
                </div>
                <div style={{ fontSize: "12px", color: "#666" }}>Total</div>
              </div>
            </div>

            <div style={{ marginTop: "24px" }}>
              <div
                style={{
                  display: "flex",
                  gap: "8px",
                  marginBottom: "16px",
                  flexWrap: "wrap",
                }}
              >
                <button
                  onClick={() => setFilter("all")}
                  style={{
                    ...ui.button,
                    backgroundColor: filter === "all" ? "#3498db" : "#ddd",
                    color: filter === "all" ? "white" : "black",
                  }}
                >
                  Toate
                </button>
                <button
                  onClick={() => setFilter("unlocked")}
                  style={{
                    ...ui.button,
                    backgroundColor: filter === "unlocked" ? "#3498db" : "#ddd",
                    color: filter === "unlocked" ? "white" : "black",
                  }}
                >
                  Desblocate
                </button>
                <button
                  onClick={() => setFilter("in-progress")}
                  style={{
                    ...ui.button,
                    backgroundColor:
                      filter === "in-progress" ? "#3498db" : "#ddd",
                    color: filter === "in-progress" ? "white" : "black",
                  }}
                >
                  În progres
                </button>
              </div>

              {types.length > 0 && (
                <div
                  style={{
                    display: "flex",
                    gap: "8px",
                    marginBottom: "16px",
                    flexWrap: "wrap",
                  }}
                >
                  <button
                    onClick={() => setSelectedType(null)}
                    style={{
                      ...ui.button,
                      backgroundColor:
                        selectedType === null ? "#27ae60" : "#ddd",
                      color: selectedType === null ? "white" : "black",
                    }}
                  >
                    Toate tipurile
                  </button>
                  {types.map((t) => (
                    <button
                      key={t}
                      onClick={() => setSelectedType(t)}
                      style={{
                        ...ui.button,
                        backgroundColor:
                          selectedType === t ? "#27ae60" : "#ddd",
                        color: selectedType === t ? "white" : "black",
                      }}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
                gap: "16px",
                marginTop: "16px",
              }}
            >
              {displayedAchievements.length > 0 ? (
                displayedAchievements.map((a) => (
                  <AchievementCard
                    key={a.id}
                    achievement={a}
                    userProgress={myAchievementMap[a.id]}
                  />
                ))
              ) : (
                <p style={{ color: "#666" }}>
                  Nu sunt realizări care să corespundă filtrelor.
                </p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
