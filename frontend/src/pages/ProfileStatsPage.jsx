import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import ProfileNav from "../components/ProfileNav.jsx";
import ProfileStats from "../components/ProfileStats.jsx";
import { getMyModerationReports } from "../api/moderation.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

export default function ProfileStatsPage() {
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken, logout } =
    useAuth();

  const [reports, setReports] = useState(null);
  const [isLoadingReports, setIsLoadingReports] = useState(false);
  const [reportsError, setReportsError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function loadReports() {
      if (!isAuthenticated || !isAuthVerified || !accessToken) return;
      setIsLoadingReports(true);
      setReportsError(null);
      try {
        const data = await getMyModerationReports({ baseUrl, accessToken });
        if (cancelled) return;
        setReports(Array.isArray(data) ? data : []);
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!cancelled) setReportsError("Nu am putut încărca raportările.");
      } finally {
        if (!cancelled) setIsLoadingReports(false);
      }
    }
    loadReports();
    return () => {
      cancelled = true;
    };
  }, [accessToken, baseUrl, isAuthenticated, isAuthVerified, logout]);

  const reportCounts = useMemo(() => {
    const arr = Array.isArray(reports) ? reports : [];
    let pending = 0;
    let resolved = 0;
    for (const r of arr) {
      const s = String(r?.status || "").toLowerCase();
      if (s === "pending") pending += 1;
      else if (s === "resolved") resolved += 1;
    }
    return { pending, resolved, total: arr.length };
  }, [reports]);

  if (!isAuthenticated) {
    return (
      <div>
        <ProfileNav />
        <div style={{ padding: "24px" }}>
          <h1 style={{ marginTop: 0 }}>Statistici</h1>
          <p>Trebuie să fii logat ca să vezi statisticile tale.</p>
          <p>
            <Link to="/login">Mergi la Login</Link>
          </p>
        </div>
      </div>
    );
  }

  if (isAuthenticated && !isAuthVerified) {
    return (
      <div>
        <ProfileNav />
        <div style={{ padding: "24px" }}>
          <h1 style={{ marginTop: 0 }}>Statistici</h1>
          <p style={{ marginTop: "14px" }}>Se încarcă...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <ProfileNav />
      <div style={{ padding: "24px" }}>
        <h1 style={{ marginTop: 0 }}>Statistici</h1>
        <ProfileStats />

        <div style={{ ...ui.card, marginTop: "16px" }}>
          <div style={{ fontWeight: 700, marginBottom: "8px" }}>
            Raportările mele
          </div>
          {isLoadingReports ? (
            <div style={{ opacity: 0.85 }}>Se încarcă...</div>
          ) : null}
          {reportsError ? <div style={ui.errorText}>{reportsError}</div> : null}
          {!isLoadingReports && !reportsError ? (
            <div style={{ opacity: 0.9 }}>
              Total: <strong>{reportCounts.total}</strong> · Pending:{" "}
              <strong>{reportCounts.pending}</strong> · Resolved:{" "}
              <strong>{reportCounts.resolved}</strong>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
