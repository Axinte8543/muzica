import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import ProfileNav from "../components/ProfileNav.jsx";
import WeeklyChallengeRecapBanner from "../components/WeeklyChallengeRecapBanner.jsx";
import { getWeeklyChallenges } from "../api/gamification.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

export default function ProfileWeeklyChallengesPage() {
  const { isAuthenticated, isAuthVerified, logout } = useAuth();

  const [weeklyChallenges, setWeeklyChallenges] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!isAuthenticated || !isAuthVerified) return;

      setIsLoading(true);
      setError(null);
      try {
        const data = await getWeeklyChallenges();
        if (cancelled) return;
        setWeeklyChallenges(data && typeof data === "object" ? data : null);
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!cancelled) {
          setError("Nu am putut încărca provocările săptămânale.");
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

  const challenges = useMemo(() => {
    const list = weeklyChallenges?.challenges;
    return Array.isArray(list) ? list : [];
  }, [weeklyChallenges]);

  if (!isAuthenticated) {
    return (
      <div>
        <ProfileNav />
        <div style={{ padding: "24px" }}>
          <h1 style={{ marginTop: 0 }}>Provocări săptămânale</h1>
          <p>Trebuie să fii logat ca să vezi provocările tale.</p>
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
          <h1 style={{ marginTop: 0 }}>Provocări săptămânale</h1>
          <p style={{ marginTop: "14px" }}>Se încarcă...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <ProfileNav />
      <div style={{ padding: "24px" }}>
        <h1 style={{ marginTop: 0 }}>Provocări săptămânale</h1>

        {weeklyChallenges ? (
          <div style={{ marginTop: "18px" }}>
            <WeeklyChallengeRecapBanner challengePayload={weeklyChallenges} />
          </div>
        ) : null}

        <div style={{ ...ui.card, maxWidth: "760px" }}>
          {isLoading ? <p style={{ margin: 0 }}>Se încarcă...</p> : null}
          {error ? (
            <p style={{ ...ui.errorText, margin: 0 }} role="alert">
              {error}
            </p>
          ) : null}

          {!isLoading && !error && !challenges.length ? (
            <p style={{ margin: 0, opacity: 0.9 }}>
              Nu există provocări active în această săptămână.
            </p>
          ) : null}

          {!isLoading && !error && challenges.length ? (
            <div style={{ display: "grid", gap: "10px" }}>
              {challenges.map((c) => (
                <div
                  key={String(c.key || c.title || Math.random())}
                  style={{
                    padding: "10px",
                    border: `1px solid ${ui.colors.border}`,
                    borderRadius: "8px",
                    opacity: c.completed ? 1 : 0.92,
                    background: c.completed ? "#ecfdf5" : "transparent",
                    color: c.completed ? "#0f172a" : "var(--text-color)",
                  }}
                >
                  <div
                    style={{ display: "flex", gap: 10, alignItems: "center" }}
                  >
                    <div style={{ fontWeight: 700, flex: 1 }}>{c.title}</div>
                    <div style={{ opacity: 0.85 }}>
                      {String(c.progress ?? 0)}/{String(c.target ?? 0)}
                    </div>
                  </div>
                  {c.description ? (
                    <div style={{ marginTop: "4px", opacity: 0.88 }}>
                      {c.description}
                    </div>
                  ) : null}
                  <div style={{ marginTop: "4px", opacity: 0.82 }}>
                    Status: {c.completed ? "Completată" : "În progres"}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
