import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { getSimilarArtists } from "../api/artists.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

function SimilarArtistCard({ artist }) {
  const name = artist?.name || "Artist";
  const slug = artist?.slug;
  const imageUrl = artist?.image_url;
  const matchValue = Number(artist?.match);
  const hasMatch = Number.isFinite(matchValue);

  const card = (
    <div style={{ ...ui.card, height: "100%" }}>
      {imageUrl ? (
        <img
          src={imageUrl}
          alt={`Imaginea pentru ${name}`}
          style={{
            width: "100%",
            aspectRatio: "1 / 1",
            objectFit: "cover",
            borderRadius: "8px",
            display: "block",
          }}
        />
      ) : (
        <div
          style={{
            width: "100%",
            aspectRatio: "1 / 1",
            borderRadius: "8px",
            background: ui.colors.mutedBg,
          }}
        />
      )}

      <div style={{ marginTop: "10px" }}>
        <div style={{ fontWeight: 800 }}>{name}</div>
        {hasMatch ? (
          <div style={{ marginTop: "6px", opacity: 0.9 }}>
            Potrivire estimată: {Math.round(matchValue * 100)}%
          </div>
        ) : null}
      </div>
    </div>
  );

  return slug ? (
    <Link
      key={slug}
      to={`/artists/${slug}`}
      style={{ color: "inherit", textDecoration: "none", display: "block" }}
    >
      {card}
    </Link>
  ) : (
    <div key={name}>{card}</div>
  );
}

export default function SimilarArtistsPage() {
  const { baseUrl, isAuthenticated, isAuthVerified } = useAuth();
  const [searchParams] = useSearchParams();
  const [artistSlug, setArtistSlug] = useState(() =>
    String(searchParams.get("artist") || "").trim(),
  );
  const [items, setItems] = useState([]);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const canLoad = useMemo(
    () => Boolean(isAuthVerified && artistSlug),
    [isAuthVerified, artistSlug],
  );

  useEffect(() => {
    const nextArtist = String(searchParams.get("artist") || "").trim();
    const t = setTimeout(() => setArtistSlug(nextArtist), 0);
    return () => clearTimeout(t);
  }, [searchParams]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!canLoad) {
        setItems([]);
        setError(null);
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const data = await getSimilarArtists({
          baseUrl,
          slug: artistSlug,
          limit: 12,
        });

        if (!cancelled) {
          setItems(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setError("Similar artists nu au putut fi incarcati.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    const t = setTimeout(() => {
      load();
    }, 0);

    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [artistSlug, baseUrl, canLoad]);

  if (!isAuthenticated) {
    return (
      <div style={ui.container}>
        <h1 style={{ marginTop: 0 }}>Similar artists</h1>
        <p>Trebuie să fii logat ca să vezi această secțiune.</p>
        <p>
          <Link to="/login">Mergi la Login</Link>
        </p>
      </div>
    );
  }

  if (!isAuthVerified) {
    return (
      <div style={ui.container}>
        <h1 style={{ marginTop: 0 }}>Similar artists</h1>
        <p style={{ marginTop: "14px" }}>Se încarcă...</p>
      </div>
    );
  }

  return (
    <div style={ui.container}>
      <div
        style={{
          ...ui.card,
          padding: "24px",
          background:
            "linear-gradient(135deg, rgba(245, 158, 11, 0.18), rgba(15, 23, 42, 0.04))",
        }}
      >
        <p
          style={{
            margin: 0,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            fontSize: "0.8rem",
            opacity: 0.75,
          }}
        >
          Descoperire contextuală
        </p>
        <h1 style={{ margin: "10px 0 12px" }}>Similar artists</h1>
        <p style={{ margin: 0, maxWidth: "72ch" }}>
          Vezi artiștii considerați similari pentru un artist ales. Lista este
          alimentată de endpointul existent din backend și poate fi deschisă
          direct din pagina artistului.
        </p>
      </div>

      <section style={{ ...ui.card, marginTop: "18px", padding: "20px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "12px",
            flexWrap: "wrap",
          }}
        >
          <h2 style={{ margin: 0 }}>Rezultate</h2>
          <Link to="/recommendations" style={{ color: "inherit" }}>
            Recomandări muzicale
          </Link>
        </div>

        {artistSlug ? (
          <p style={{ marginTop: "10px", opacity: 0.85 }}>
            Artist selectat: <strong>{artistSlug}</strong>
          </p>
        ) : null}

        {!artistSlug ? (
          <p style={{ marginTop: "12px" }}>
            Deschide această pagină cu un parametru de forma ?artist=slug-ul-
            artistului.
          </p>
        ) : isLoading ? (
          <p style={{ marginTop: "12px" }}>Se încarcă...</p>
        ) : error ? (
          <p style={{ ...ui.errorText, marginTop: "12px" }} role="alert">
            {error}
          </p>
        ) : items.length ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
              gap: "16px",
              marginTop: "14px",
            }}
          >
            {items.map((artist) => (
              <SimilarArtistCard
                key={artist.id || artist.slug || artist.name}
                artist={artist}
              />
            ))}
          </div>
        ) : (
          <p style={{ marginTop: "12px", opacity: 0.85 }}>—</p>
        )}
      </section>
    </div>
  );
}
