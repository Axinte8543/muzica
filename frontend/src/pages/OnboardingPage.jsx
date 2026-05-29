import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { setupOnboarding } from "../api/onboarding.js";
import { apiClient } from "../api/apiClient.js";
import { ui } from "../ui/ui.js";

export default function OnboardingPage() {
  const navigate = useNavigate();

  function getGenreKey(genre) {
    return String(genre?.id ?? genre?.slug ?? genre?.name ?? "");
  }

  // State for selected genres and artists
  const [selectedGenres, setSelectedGenres] = useState(new Map());
  // Keep a map of selected artistId -> artist object so we don't lose details
  // when clearing the search results after selection.
  const [selectedArtists, setSelectedArtists] = useState(new Map());
  const [artistSearchQuery, setArtistSearchQuery] = useState("");
  const [filteredArtists, setFilteredArtists] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Fetch genres
  const filtersQuery = useQuery({
    queryKey: ["albumsFilters"],
    staleTime: 1000 * 60 * 60,
    gcTime: 1000 * 60 * 60 * 2,
    queryFn: async () => {
      const res = await apiClient.get(`/api/albums/filters/`);
      return res?.data || {};
    },
  });

  const genres = filtersQuery.data?.genres || [];

  // Fetch artists based on search query
  const artistsQuery = useQuery({
    queryKey: ["artists-search", artistSearchQuery],
    enabled: artistSearchQuery.length >= 2,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 10,
    queryFn: async () => {
      if (!artistSearchQuery || artistSearchQuery.length < 2) {
        return [];
      }
      try {
        const res = await apiClient.get(`/api/search/`, {
          params: { q: artistSearchQuery, limit: 10 },
        });
        return Array.isArray(res?.data?.artists) ? res.data.artists : [];
      } catch (err) {
        console.error("Failed to fetch artists", err);
        return [];
      }
    },
  });

  // Update filtered artists when search results change
  useEffect(() => {
    if (artistSearchQuery.length >= 2 && artistsQuery.data) {
      setFilteredArtists(artistsQuery.data);
    } else if (!artistSearchQuery) {
      setFilteredArtists([]);
    }
  }, [artistSearchQuery, artistsQuery.data]);

  // Toggle genre selection
  function toggleGenre(genre) {
    const genreKey = getGenreKey(genre);
    if (!genreKey) return;

    const newSelected = new Map(selectedGenres);
    if (newSelected.has(genreKey)) {
      newSelected.delete(genreKey);
    } else {
      newSelected.set(genreKey, genre);
    }
    setSelectedGenres(newSelected);
  }

  // Toggle artist selection
  function toggleArtist(artist) {
    const newSelected = new Map(selectedArtists);
    const artistId = artist?.id;
    if (!artistId) return;
    if (newSelected.has(artistId)) {
      newSelected.delete(artistId);
    } else {
      newSelected.set(artistId, artist);
    }
    setSelectedArtists(newSelected);
  }

  // Remove selected artist
  function removeArtist(artistId) {
    const newSelected = new Map(selectedArtists);
    newSelected.delete(artistId);
    setSelectedArtists(newSelected);
  }

  // Handle form submission
  async function handleSubmit(event) {
    event.preventDefault();

    if (selectedGenres.size === 0) {
      setError("Trebuie să selectezi cel puțin un gen.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const payload = {
        genre_ids: Array.from(selectedGenres.values())
          .map((genre) => {
            const resolved = Number(genre?.id);
            if (Number.isFinite(resolved) && resolved > 0) return resolved;
            const fallback = genres.find(
              (item) =>
                getGenreKey(item) === getGenreKey(genre) ||
                String(item?.name || "").toLowerCase() ===
                  String(genre?.name || "").toLowerCase(),
            );
            return Number(fallback?.id) || null;
          })
          .filter((value) => Number.isFinite(value) && value > 0),
        artist_ids: Array.from(selectedArtists.keys()).map((v) => Number(v)),
      };
      console.debug("Onboarding submit payload:", payload);
      const resp = await setupOnboarding(payload);
      console.debug("Onboarding response:", resp);

      // Navigate to home page after successful onboarding
      navigate("/");
    } catch (err) {
      console.error("Failed to complete onboarding:", err);
      const serverMsg = err?.response?.data || err?.message || "Unknown error";
      setError(
        typeof serverMsg === "string" ? serverMsg : JSON.stringify(serverMsg),
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  // Get selected artist details for display (we store full artist objects in the map)
  const selectedArtistDetails = Array.from(selectedArtists.values());

  return (
    <div style={{ padding: "24px", maxWidth: "800px", margin: "0 auto" }}>
      <div style={{ textAlign: "center", marginBottom: "32px" }}>
        <h1 style={{ marginTop: 0, marginBottom: "8px" }}>
          Bun venit la Licența Muzică!
        </h1>
        <p style={{ opacity: 0.8, marginBottom: 0 }}>
          Personalizează-ți experiența selectând genurile și artiștii tăi
          preferați
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Genres Section */}
        <div style={{ marginBottom: "32px" }}>
          <h2 style={{ fontSize: "18px", marginBottom: "12px" }}>
            Selectează genurile preferate (minim 1)
          </h2>
          {filtersQuery.isLoading ? (
            <p>Se încarcă genurile...</p>
          ) : (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
                gap: "8px",
              }}
            >
              {genres.map((g) => (
                <button
                  key={getGenreKey(g)}
                  type="button"
                  onClick={() => toggleGenre(g)}
                  style={{
                    padding: "10px 12px",
                    border: selectedGenres.has(getGenreKey(g))
                      ? "1px solid rgba(78, 182, 255, 0.85)"
                      : "1px solid rgba(255,255,255,0.06)",
                    background: selectedGenres.has(getGenreKey(g))
                      ? "rgba(78, 182, 255, 0.18)"
                      : "transparent",
                    color: selectedGenres.has(getGenreKey(g))
                      ? "#eaf7ff"
                      : "inherit",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontWeight: selectedGenres.has(getGenreKey(g)) ? 600 : 400,
                    transition: "all 0.2s ease",
                  }}
                >
                  {g.name}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Artists Section */}
        <div style={{ marginBottom: "32px" }}>
          <h2 style={{ fontSize: "18px", marginBottom: "12px" }}>
            Selectează artiști preferați (opțional)
          </h2>

          {/* Artist search input */}
          <input
            type="text"
            placeholder="Caută artisti..."
            value={artistSearchQuery}
            onChange={(e) => setArtistSearchQuery(e.target.value)}
            style={{
              width: "100%",
              marginBottom: "12px",
              ...ui.input,
            }}
          />

          {/* Search suggestions dropdown */}
          {filteredArtists.length > 0 && (
            <div
              style={{
                border: "1px solid #ccc",
                borderRadius: "6px",
                maxHeight: "300px",
                overflowY: "auto",
                marginBottom: "12px",
              }}
            >
              {filteredArtists.map((artist) => (
                <button
                  key={artist.id}
                  type="button"
                  onClick={() => {
                    toggleArtist(artist);
                    setArtistSearchQuery("");
                  }}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    border: "none",
                    borderBottom: "1px solid #eee",
                    background: "transparent",
                    textAlign: "left",
                    cursor: "pointer",
                    fontSize: "14px",
                  }}
                >
                  {artist.name}
                </button>
              ))}
            </div>
          )}

          {/* Selected artists display */}
          {selectedArtistDetails.length > 0 && (
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "8px",
                marginTop: "12px",
              }}
            >
              {selectedArtistDetails.map((artist) => (
                <div
                  key={artist.id}
                  style={{
                    padding: "8px 12px",
                    background: "rgba(78, 182, 255, 0.16)",
                    border: "1px solid rgba(78, 182, 255, 0.75)",
                    borderRadius: "20px",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "14px",
                    color: "#eaf7ff",
                  }}
                >
                  {artist.name}
                  <button
                    type="button"
                    onClick={() => removeArtist(artist.id)}
                    style={{
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      fontSize: "18px",
                      padding: 0,
                      lineHeight: 1,
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Summary and error */}
        {error ? (
          <p style={{ ...ui.errorText, marginBottom: "16px" }}>{error}</p>
        ) : null}

        <div
          style={{
            padding: "12px",
            background: "#f5f5f5",
            borderRadius: "6px",
            marginBottom: "16px",
            fontSize: "14px",
          }}
        >
          <p style={{ margin: 0 }}>
            Selectat: <strong>{selectedGenres.size}</strong> genuri,{" "}
            <strong>{selectedArtists.size}</strong> artiști
          </p>
        </div>

        <button
          type="submit"
          disabled={isSubmitting || selectedGenres.size === 0}
          style={{
            width: "100%",
            ...ui.button,
            opacity: isSubmitting || selectedGenres.size === 0 ? 0.6 : 1,
            cursor:
              isSubmitting || selectedGenres.size === 0
                ? "not-allowed"
                : "pointer",
          }}
        >
          {isSubmitting ? "Se finalizează..." : "Finalizează onboarding"}
        </button>
      </form>
    </div>
  );
}
