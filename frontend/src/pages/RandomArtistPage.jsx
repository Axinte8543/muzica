import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiClient } from "../api/apiClient.js";
import { ui } from "../ui/ui.js";

export default function RandomArtistPage() {
  const navigate = useNavigate();

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isCancelled = false;

    async function load() {
      if (!isCancelled) {
        setIsLoading(true);
        setError(null);
      }

      try {
        const res = await apiClient.get(`/api/artists/random/`);
        if (isCancelled) return;

        const slug = res?.data?.slug;
        if (typeof slug === "string" && slug.trim()) {
          navigate(`/artists/${slug}`, { replace: true });
          return;
        }

        setError("Nu am găsit niciun artist.");
      } catch (err) {
        if (isCancelled) return;
        console.error(err);
        setError("Nu am putut alege un artist random.");
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    load();

    return () => {
      isCancelled = true;
    };
  }, [navigate]);

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Random Artist</h1>

      {isLoading ? <p>Se alege un artist...</p> : null}
      {error ? <p style={ui.errorText}>{error}</p> : null}

      {!isLoading && !error ? <p>Redirecționare...</p> : null}
    </div>
  );
}
