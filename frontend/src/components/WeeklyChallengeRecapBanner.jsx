import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getWeeklyChallenges } from "../api/gamification.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

const STORAGE_KEY = "weekly-challenge-recap-seen-week-starts";

function readSeenWeekStarts() {
  if (typeof window === "undefined") return [];

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed)
      ? parsed.map((value) => String(value)).filter(Boolean)
      : [];
  } catch {
    return [];
  }
}

function writeSeenWeekStarts(values) {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(values));
  } catch {
    // Ignore storage failures.
  }
}

function challengeLabel(challenge) {
  const title = String(challenge?.title || "Provocare").trim();
  const progress = Number(challenge?.progress ?? 0);
  const target = Number(challenge?.target ?? 0);
  return `${title} (${progress}/${target})`;
}

export default function WeeklyChallengeRecapBanner({
  challengePayload = null,
} = {}) {
  const { isAuthenticated, isAuthVerified, logout } = useAuth();

  const [payload, setPayload] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [seenWeekStarts, setSeenWeekStarts] = useState(() =>
    readSeenWeekStarts(),
  );

  useEffect(() => {
    writeSeenWeekStarts(seenWeekStarts);
  }, [seenWeekStarts]);

  useEffect(() => {
    if (challengePayload && typeof challengePayload === "object") {
      setError(null);
      setIsLoading(false);
      return;
    }

    let cancelled = false;

    async function load() {
      if (!isAuthenticated || !isAuthVerified) {
        if (!cancelled) {
          setPayload(null);
          setError(null);
          setIsLoading(false);
        }
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const data = await getWeeklyChallenges();
        if (cancelled) return;
        setPayload(data && typeof data === "object" ? data : null);
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!cancelled) {
          setError("Nu am putut încărca recapul provocărilor.");
          setPayload(null);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [challengePayload, isAuthVerified, isAuthenticated, logout]);

  const activePayload =
    challengePayload && typeof challengePayload === "object"
      ? challengePayload
      : payload;
  const previousWeekRecap = activePayload?.previous_week_recap;
  const completedChallenges = useMemo(() => {
    const list = previousWeekRecap?.completed_challenges;
    return Array.isArray(list) ? list : [];
  }, [previousWeekRecap]);

  const missedChallenges = useMemo(() => {
    const list = previousWeekRecap?.incomplete_challenges;
    return Array.isArray(list) ? list : [];
  }, [previousWeekRecap]);

  const previousWeekStart = String(previousWeekRecap?.week_start || "").trim();
  const isDismissed = previousWeekStart
    ? seenWeekStarts.includes(previousWeekStart)
    : false;

  function acknowledge() {
    if (!previousWeekStart) return;
    setSeenWeekStarts((prev) => {
      if (prev.includes(previousWeekStart)) return prev;
      return [...prev, previousWeekStart];
    });
  }

  if (
    !isAuthenticated ||
    !isAuthVerified ||
    isLoading ||
    error ||
    !previousWeekRecap ||
    isDismissed
  ) {
    return null;
  }

  const completedCount = Number(
    previousWeekRecap.completed_count ?? completedChallenges.length,
  );
  const totalCount = Number(
    previousWeekRecap.total_count ??
      completedChallenges.length + missedChallenges.length,
  );
  const incompleteCount = Number(
    previousWeekRecap.incomplete_count ?? missedChallenges.length,
  );

  const linkButtonStyle = {
    ...ui.buttonSmall,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    textDecoration: "none",
  };

  return (
    <div
      style={{
        ...ui.card,
        marginBottom: "22px",
        border: "1px solid rgba(245, 158, 11, 0.28)",
        background:
          "linear-gradient(180deg, rgba(245, 158, 11, 0.12), rgba(15, 23, 42, 0.88))",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "16px",
          flexWrap: "wrap",
        }}
      >
        <div>
          <div style={{ fontSize: "1.15rem", fontWeight: 800 }}>
            Recapul ultimei săptămâni
          </div>
          <div style={{ marginTop: "4px", opacity: 0.82 }}>
            {previousWeekRecap.week_start} - {previousWeekRecap.week_end}
          </div>
        </div>

        <div style={{ fontSize: "2rem", fontWeight: 800, lineHeight: 1 }}>
          {completedCount}/{totalCount}
        </div>
      </div>

      <p style={{ marginTop: "12px", marginBottom: "14px", opacity: 0.92 }}>
        Ai completat {completedCount} provocări și ai rămas cu <br />
        {incompleteCount} nefinalizate.
      </p>

      <div style={{ display: "grid", gap: "12px" }}>
        <section>
          <div style={{ fontWeight: 700, marginBottom: "6px" }}>Finalizate</div>
          {completedChallenges.length ? (
            <ul style={{ margin: 0, paddingLeft: "18px" }}>
              {completedChallenges.map((challenge) => (
                <li key={String(challenge.key || challenge.title)}>
                  {challengeLabel(challenge)}
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ margin: 0, opacity: 0.82 }}>
              Nu ai finalizat nicio provocare săptămâna trecută.
            </p>
          )}
        </section>

        <section>
          <div style={{ fontWeight: 700, marginBottom: "6px" }}>
            Nefinalizate
          </div>
          {missedChallenges.length ? (
            <ul style={{ margin: 0, paddingLeft: "18px" }}>
              {missedChallenges.map((challenge) => (
                <li key={String(challenge.key || challenge.title)}>
                  {challengeLabel(challenge)}
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ margin: 0, opacity: 0.82 }}>
              Nu ai ratat nicio provocare.
            </p>
          )}
        </section>
      </div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "10px",
          marginTop: "16px",
        }}
      >
        <Link to="/profile/challenges/weekly" style={linkButtonStyle}>
          Vezi provocările curente
        </Link>
        <Link to="/recap/weekly" style={linkButtonStyle} onClick={acknowledge}>
          Vezi recap complet
        </Link>
        <button type="button" style={ui.buttonSmall} onClick={acknowledge}>
          Închide
        </button>
      </div>
    </div>
  );
}
