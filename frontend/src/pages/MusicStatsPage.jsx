import { useEffect, useMemo, useState } from "react";

import { getMusicStats } from "../api/musicStats.js";
import MusicStats from "../components/MusicStats.jsx";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

export default function MusicStatsPage() {
  const { baseUrl } = useAuth();

  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const limit = 10;

  const safeBaseUrl = useMemo(() => {
    return baseUrl || "http://127.0.0.1:8000";
  }, [baseUrl]);

  useEffect(() => {
    let isCancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);

      try {
        const data = await getMusicStats({ baseUrl: safeBaseUrl, limit });
        if (!isCancelled) setStats(data || null);
      } catch (err) {
        console.error(err);
        if (!isCancelled) setError("Nu am putut încărca statisticile.");
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    load();

    return () => {
      isCancelled = true;
    };
  }, [safeBaseUrl]);

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Statistici muzicale</h1>

      {isLoading ? <p>Se încarcă...</p> : null}
      {error ? (
        <p style={ui.errorText} role="alert">
          {error}
        </p>
      ) : null}

      {!isLoading && !error && !stats ? (
        <p style={{ marginTop: "10px", opacity: 0.9 }}>Nu există date încă.</p>
      ) : null}

      {!isLoading && !error && stats ? <MusicStats stats={stats} /> : null}
    </div>
  );
}
