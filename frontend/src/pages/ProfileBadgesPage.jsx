import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import ProfileNav from "../components/ProfileNav.jsx";
import BadgeCard from "../components/BadgeCard.jsx";
import { getMyBadges, getBadges } from "../api/gamification.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

export default function ProfileBadgesPage() {
  const { isAuthenticated, isAuthVerified, logout } = useAuth();
  const [myBadges, setMyBadges] = useState([]);
  const [allBadges, setAllBadges] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!isAuthenticated || !isAuthVerified) return;

      setIsLoading(true);
      setError(null);
      try {
        const [myBadgesData, allBadgesData] = await Promise.all([
          getMyBadges(),
          getBadges(),
        ]);

        if (cancelled) return;

        setMyBadges(Array.isArray(myBadgesData) ? myBadgesData : []);
        setAllBadges(Array.isArray(allBadgesData) ? allBadgesData : []);
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!cancelled) {
          setError("Nu am putut încărca insignele.");
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
          <h1 style={{ marginTop: 0 }}>Insignele mele</h1>
          <p>Trebuie să fii logat ca să vezi insignele tale.</p>
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
          <h1 style={{ marginTop: 0 }}>Insignele mele</h1>
          <p style={{ marginTop: "14px" }}>Se încarcă...</p>
        </div>
      </div>
    );
  }

  const myBadgeIds = new Set(myBadges.map((b) => b.badge.id));
  const categories = [...new Set(allBadges.map((b) => b.category))].sort();

  const filteredBadges = selectedCategory
    ? allBadges.filter((b) => b.category === selectedCategory)
    : allBadges;

  return (
    <div>
      <ProfileNav />
      <div style={{ padding: "24px" }}>
        <h1 style={{ marginTop: 0 }}>Insignele mele</h1>

        {isLoading && <p>Se încarcă...</p>}
        {error && (
          <p style={{ ...ui.errorText, marginTop: "14px" }} role="alert">
            {error}
          </p>
        )}

        {!isLoading && !error && (
          <>
            <div style={{ marginTop: "24px" }}>
              <h2>Insignele câștigate ({myBadges.length})</h2>
              {myBadges.length > 0 ? (
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(auto-fill, minmax(100px, 1fr))",
                    gap: "12px",
                    marginTop: "12px",
                  }}
                >
                  {myBadges.map((b) => (
                    <BadgeCard key={b.id} badge={b.badge} earned={true} />
                  ))}
                </div>
              ) : (
                <p style={{ color: "#666", marginTop: "12px" }}>
                  Nu ai câștigat încă nicio insignă.
                </p>
              )}
            </div>

            <div style={{ marginTop: "40px" }}>
              <h2>Toate insignele disponibile</h2>

              {categories.length > 0 && (
                <div
                  style={{
                    display: "flex",
                    gap: "8px",
                    marginTop: "12px",
                    flexWrap: "wrap",
                  }}
                >
                  <button
                    onClick={() => setSelectedCategory(null)}
                    style={{
                      ...ui.button,
                      backgroundColor:
                        selectedCategory === null ? "#3498db" : "#ddd",
                      color: selectedCategory === null ? "white" : "black",
                    }}
                  >
                    Toate
                  </button>
                  {categories.map((cat) => (
                    <button
                      key={cat}
                      onClick={() => setSelectedCategory(cat)}
                      style={{
                        ...ui.button,
                        backgroundColor:
                          selectedCategory === cat ? "#3498db" : "#ddd",
                        color: selectedCategory === cat ? "white" : "black",
                      }}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              )}

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(100px, 1fr))",
                  gap: "12px",
                  marginTop: "12px",
                }}
              >
                {filteredBadges.map((b) => (
                  <BadgeCard
                    key={b.id}
                    badge={b}
                    earned={myBadgeIds.has(b.id)}
                  />
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
