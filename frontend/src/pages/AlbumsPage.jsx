import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/apiClient.js";
import {
  getMyFavoriteAlbums,
  setMyFavoriteAlbums,
} from "../api/favoriteAlbums.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";
import { prefetchAlbum } from "../query/prefetchAlbum.js";

function getYearFromDate(dateString) {
  if (!dateString) return "";
  const match = String(dateString).match(/^\d{4}/);
  return match ? match[0] : "";
}

function releaseTypeLabel(album) {
  const type = String(album?.release_type || "").toLowerCase();
  if (type === "single") return "Single";
  if (type === "ep") return "EP";
  if (type === "compilation") return "Compilație";
  return "Album";
}

export default function AlbumsPage() {
  const navigate = useNavigate();
  const { baseUrl, isAuthVerified, accessToken } = useAuth();
  const queryClient = useQueryClient();

  const [searchParams, setSearchParams] = useSearchParams();

  const pickFavoriteSlot = useMemo(() => {
    const raw = String(searchParams.get("pickFavoriteSlot") || "").trim();
    if (!raw) return null;
    const num = Number.parseInt(raw, 10);
    if (!Number.isFinite(num) || num < 1 || num > 4) return null;
    return num;
  }, [searchParams]);

  const pickFavoriteSongSlot = useMemo(() => {
    const raw = String(searchParams.get("pickFavoriteSongSlot") || "").trim();
    if (!raw) return null;
    const num = Number.parseInt(raw, 10);
    if (!Number.isFinite(num) || num < 1 || num > 4) return null;
    return num;
  }, [searchParams]);

  const [pickError, setPickError] = useState(null);
  const [isPickingFavorite, setIsPickingFavorite] = useState(false);

  function slotsFromFavoriteAlbumsResponse(data) {
    const slots = [null, null, null, null];
    const fav = Array.isArray(data?.favorite_albums)
      ? data.favorite_albums
      : [];
    fav.forEach((item) => {
      const pos = Number(item?.position);
      if (!Number.isFinite(pos) || pos < 1 || pos > 4) return;
      const albumId =
        item?.album_id === null || item?.album_id === undefined
          ? null
          : Number(item.album_id);
      slots[pos - 1] = Number.isFinite(albumId) ? albumId : null;
    });
    return slots;
  }

  async function handlePickFavorite(album) {
    if (!pickFavoriteSlot) return;
    if (!isAuthVerified || !accessToken) {
      setPickError("Trebuie să fii logat ca să setezi albume favorite.");
      return;
    }
    const albumId = Number(album?.id);
    if (!Number.isFinite(albumId) || albumId <= 0) {
      setPickError("Album invalid.");
      return;
    }

    setIsPickingFavorite(true);
    setPickError(null);
    try {
      const current = await getMyFavoriteAlbums({ accessToken });
      const slots = slotsFromFavoriteAlbumsResponse(current);
      slots[pickFavoriteSlot - 1] = albumId;
      await setMyFavoriteAlbums({ accessToken, slots });
      navigate("/profile/stats");
    } catch (err) {
      console.error(err);
      setPickError("Nu am putut seta albumul ca favorit.");
    } finally {
      setIsPickingFavorite(false);
    }
  }

  const yearFromUrl = useMemo(() => {
    const yearRaw = String(searchParams.get("year") || "").trim();
    if (!yearRaw) return "";
    const yearNum = Number.parseInt(yearRaw, 10);
    if (!Number.isFinite(yearNum) || yearNum < 1900 || yearNum > 2100)
      return "";
    return String(yearNum);
  }, [searchParams]);

  const monthFromUrl = useMemo(() => {
    const monthRaw = String(searchParams.get("month") || "").trim();
    if (!monthRaw) return "";
    const monthNum = Number.parseInt(monthRaw, 10);
    if (!Number.isFinite(monthNum) || monthNum < 1 || monthNum > 12) return "";
    return String(monthNum);
  }, [searchParams]);

  const genreFromUrl = useMemo(() => {
    const raw = String(searchParams.get("genre") || "").trim();
    if (!raw) return "";
    // Keep it permissive (slugs may contain dashes). Reject obvious junk.
    if (raw.length > 100) return "";
    return raw;
  }, [searchParams]);

  const sortFromUrl = useMemo(() => {
    const raw = String(searchParams.get("sort") || "").trim();
    return ["release_date", "rating", "ratings_count", "my_rating"].includes(
      raw,
    )
      ? raw
      : "release_date";
  }, [searchParams]);

  const releaseTypeFromUrl = useMemo(() => {
    const raw = String(searchParams.get("release_type") || "").trim();
    return ["albums", "singles", "all"].includes(raw) ? raw : "albums";
  }, [searchParams]);

  const [searchInput, setSearchInput] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");

  const [selectedGenre, setSelectedGenre] = useState(genreFromUrl);
  const [selectedYear, setSelectedYear] = useState(yearFromUrl);
  const [selectedMonth, setSelectedMonth] = useState(monthFromUrl);
  const [selectedDecade, setSelectedDecade] = useState("");
  const [selectedSort, setSelectedSort] = useState(sortFromUrl);
  const [selectedReleaseType, setSelectedReleaseType] =
    useState(releaseTypeFromUrl);

  const [genreOptions, setGenreOptions] = useState([]);
  const [yearOptions, setYearOptions] = useState([]);
  const [monthOptions, setMonthOptions] = useState([]);
  const [decadeOptions, setDecadeOptions] = useState([]);

  const [albums, setAlbums] = useState([]);
  const [page, setPage] = useState(1);
  const [pageInfo, setPageInfo] = useState({
    count: 0,
    next: null,
    previous: null,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const filtersQuery = useQuery({
    queryKey: ["albumsFilters"],
    staleTime: 1000 * 60 * 60, // 1h
    gcTime: 1000 * 60 * 60 * 2, // 2h
    queryFn: async () => {
      const res = await apiClient.get(`/api/albums/filters/`);
      return res?.data || {};
    },
  });

  useEffect(() => {
    const payload = filtersQuery.data || {};

    const genres = Array.isArray(payload?.genres) ? payload.genres : [];
    const years = Array.isArray(payload?.years) ? payload.years : [];
    const months = Array.isArray(payload?.months) ? payload.months : [];
    const decades = Array.isArray(payload?.decades) ? payload.decades : [];

    const t = setTimeout(() => {
      setGenreOptions(genres);
      setYearOptions(
        years
          .map((y) => Number(y))
          .filter((y) => Number.isFinite(y) && y > 0)
          .sort((a, b) => b - a),
      );
      setMonthOptions(
        months
          .map((m) => Number(m))
          .filter((m) => Number.isFinite(m) && m >= 1 && m <= 12)
          .sort((a, b) => a - b),
      );
      setDecadeOptions(
        decades
          .map((d) => Number(d))
          .filter((d) => Number.isFinite(d) && d > 0)
          .sort((a, b) => b - a),
      );
    }, 0);

    return () => clearTimeout(t);
  }, [filtersQuery.data]);

  useEffect(() => {
    setIsLoading(true);
    setPage(1);
    setSelectedGenre(genreFromUrl);
    setSelectedYear(yearFromUrl);
    setSelectedMonth(monthFromUrl);
    setSelectedSort(sortFromUrl);
    setSelectedReleaseType(releaseTypeFromUrl);
  }, [genreFromUrl, yearFromUrl, monthFromUrl, sortFromUrl, releaseTypeFromUrl]);

  useEffect(() => {
    let isCancelled = false;

    const params = {};
    if (appliedSearch) params.q = appliedSearch;
    if (selectedGenre) params.genre = selectedGenre;
    if (selectedYear) params.year = selectedYear;
    if (selectedMonth) params.month = selectedMonth;
    if (selectedDecade) params.decade = selectedDecade;
    if (selectedSort) params.sort = selectedSort;
    if (selectedReleaseType) params.release_type = selectedReleaseType;
    if (pickFavoriteSlot) params.pickMode = "album";
    if (pickFavoriteSongSlot) params.pickMode = "song";
    params.page = page;
    params.page_size = 20;

    apiClient
      .get(`/api/albums/`, { params })
      .then((response) => {
        if (isCancelled) return;

        const payload = response.data || {};
        const nextAlbums = Array.isArray(payload?.results)
          ? payload.results
          : [];

        setAlbums(nextAlbums);
        setPageInfo({
          count: Number(payload?.count) || 0,
          next: payload?.next || null,
          previous: payload?.previous || null,
        });

        setError(null);
      })
      .catch((err) => {
        if (isCancelled) return;
        console.error(err);
        setError("Nu am putut încărca lista de albume.");
        setAlbums([]);
        setPageInfo({ count: 0, next: null, previous: null });
      })
      .finally(() => {
        if (isCancelled) return;
        setIsLoading(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [
    appliedSearch,
    page,
    selectedDecade,
    selectedGenre,
    selectedMonth,
    selectedYear,
    selectedSort,
    selectedReleaseType,
    pickFavoriteSlot,
    pickFavoriteSongSlot,
    isAuthVerified,
    accessToken,
  ]);

  function handleSearchSubmit(e) {
    e.preventDefault();
    setIsLoading(true);
    setPage(1);
    setAppliedSearch(searchInput.trim());
  }

  function handleClearAll() {
    setIsLoading(true);
    setPage(1);
    setSearchInput("");
    setAppliedSearch("");
    setSelectedGenre("");
    setSelectedYear("");
    setSelectedMonth("");
    setSelectedDecade("");
    setSelectedSort("release_date");
    setSelectedReleaseType("albums");

    const nextParams = new URLSearchParams();
    if (pickFavoriteSlot) {
      nextParams.set("pickFavoriteSlot", String(pickFavoriteSlot));
    }
    if (pickFavoriteSongSlot) {
      nextParams.set("pickFavoriteSongSlot", String(pickFavoriteSongSlot));
    }
    setSearchParams(nextParams, { replace: true });
  }

  return (
    <div style={{ padding: "24px" }}>
      <h1>Albume</h1>

      {pickFavoriteSlot ? (
        <div style={{ ...ui.card, marginTop: "12px", maxWidth: "920px" }}>
          <div style={{ fontWeight: 700 }}>
            Selectează un album pentru slotul favorit #{pickFavoriteSlot}
          </div>
          <div style={{ marginTop: "8px", display: "flex", gap: "10px" }}>
            <Link to="/profile/stats" style={ui.buttonSmall}>
              Înapoi la profil
            </Link>
          </div>
          {pickError ? (
            <p style={{ ...ui.errorText, marginTop: "10px" }} role="alert">
              {pickError}
            </p>
          ) : null}
        </div>
      ) : null}

      {pickFavoriteSongSlot ? (
        <div style={{ ...ui.card, marginTop: "12px", maxWidth: "920px" }}>
          <div style={{ fontWeight: 700 }}>
            Selectează albumul din care alegi melodia pentru slotul favorit #
            {pickFavoriteSongSlot}
          </div>
          <div style={{ marginTop: "8px", opacity: 0.85 }}>
            După ce deschizi albumul, poți seta piesa direct din tracklist.
          </div>
          <div style={{ marginTop: "8px", display: "flex", gap: "10px" }}>
            <Link to="/profile/stats" style={ui.buttonSmall}>
              Înapoi la profil
            </Link>
          </div>
        </div>
      ) : null}

      <div style={{ display: "flex", gap: "18px", marginTop: "12px" }}>
        <aside
          style={{
            width: "260px",
            minWidth: "260px",
            border: "1px solid #e5e7eb",
            borderRadius: "10px",
            padding: "12px",
            height: "fit-content",
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: "10px" }}>Căutare</div>
          <form
            onSubmit={handleSearchSubmit}
            style={{ display: "grid", gap: "8px" }}
          >
            <input
              type="search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Caută album sau artist..."
              style={{
                padding: "8px 10px",
                border: "1px solid #e5e7eb",
                borderRadius: "6px",
              }}
            />
            <div style={{ display: "flex", gap: "8px" }}>
              <button type="submit" style={{ ...ui.button, flex: 1 }}>
                Caută
              </button>
              <button type="button" onClick={handleClearAll} style={ui.button}>
                Curăță
              </button>
            </div>
          </form>

          <div style={{ fontWeight: 700, margin: "16px 0 10px" }}>Filtre</div>

          <div style={{ display: "grid", gap: "10px" }}>
            <label style={{ display: "grid", gap: "6px" }}>
              <span style={{ fontSize: "14px", opacity: 0.85 }}>Tip</span>
              <select
                value={selectedReleaseType}
                onChange={(e) => {
                  setIsLoading(true);
                  setPage(1);
                  setSelectedReleaseType(e.target.value);
                }}
                style={{
                  padding: "8px 10px",
                  border: "1px solid #e5e7eb",
                  borderRadius: "6px",
                }}
              >
                <option value="albums">Albume</option>
                <option value="singles">Single-uri</option>
                <option value="all">Toate lansările</option>
              </select>
            </label>

            <label style={{ display: "grid", gap: "6px" }}>
              <span style={{ fontSize: "14px", opacity: 0.85 }}>Gen</span>
              <select
                value={selectedGenre}
                onChange={(e) => {
                  setIsLoading(true);
                  setPage(1);
                  setSelectedGenre(e.target.value);
                }}
                style={{
                  padding: "8px 10px",
                  border: "1px solid #e5e7eb",
                  borderRadius: "6px",
                }}
              >
                <option value="">Toate</option>
                {genreOptions.map((g) => (
                  <option key={g.slug} value={g.slug}>
                    {g.name}
                  </option>
                ))}
              </select>
            </label>

            <label style={{ display: "grid", gap: "6px" }}>
              <span style={{ fontSize: "14px", opacity: 0.85 }}>An</span>
              <select
                value={selectedYear}
                onChange={(e) => {
                  setIsLoading(true);
                  setPage(1);
                  setSelectedYear(e.target.value);
                }}
                style={{
                  padding: "8px 10px",
                  border: "1px solid #e5e7eb",
                  borderRadius: "6px",
                }}
              >
                <option value="">Toți</option>
                {yearOptions.map((y) => (
                  <option key={y} value={String(y)}>
                    {y}
                  </option>
                ))}
              </select>
            </label>

            <label style={{ display: "grid", gap: "6px" }}>
              <span style={{ fontSize: "14px", opacity: 0.85 }}>Lună</span>
              <select
                value={selectedMonth}
                onChange={(e) => {
                  setIsLoading(true);
                  setPage(1);
                  setSelectedMonth(e.target.value);
                }}
                style={{
                  padding: "8px 10px",
                  border: "1px solid #e5e7eb",
                  borderRadius: "6px",
                }}
              >
                <option value="">Toate</option>
                {monthOptions.map((m) => (
                  <option key={m} value={String(m)}>
                    {String(m).padStart(2, "0")}
                  </option>
                ))}
              </select>
            </label>

            <label style={{ display: "grid", gap: "6px" }}>
              <span style={{ fontSize: "14px", opacity: 0.85 }}>Deceniu</span>
              <select
                value={selectedDecade}
                onChange={(e) => {
                  setIsLoading(true);
                  setPage(1);
                  setSelectedDecade(e.target.value);
                }}
                style={{
                  padding: "8px 10px",
                  border: "1px solid #e5e7eb",
                  borderRadius: "6px",
                }}
              >
                <option value="">Toate</option>
                {decadeOptions.map((d) => (
                  <option key={d} value={String(d)}>
                    {d}s
                  </option>
                ))}
              </select>
            </label>
          </div>
        </aside>

        <main style={{ flex: 1 }}>
          <div style={{ marginBottom: "12px" }}>
            <label
              style={{ display: "flex", alignItems: "center", gap: "10px" }}
            >
              <span style={{ fontWeight: 700 }}>Ordonează după</span>
              <select
                value={selectedSort}
                onChange={(e) => {
                  setIsLoading(true);
                  setPage(1);
                  setSelectedSort(e.target.value);
                }}
                style={{
                  padding: "8px 10px",
                  border: "1px solid #e5e7eb",
                  borderRadius: "6px",
                }}
              >
                <option value="release_date">Data lansării</option>
                <option value="rating">Nota</option>
                <option value="ratings_count">Nr. ratinguri</option>
                <option value="my_rating">Nota mea</option>
              </select>
            </label>
          </div>

          {isLoading && <p>Se încarcă albumele...</p>}
          {error && <p style={ui.errorText}>{error}</p>}

          {!isLoading && !error && albums.length === 0 ? (
            <p>Nu am găsit albume.</p>
          ) : null}

          {!isLoading && !error && albums.length > 0 ? (
            <>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                  gap: "16px",
                }}
              >
                {albums.map((album) => {
                  const year = getYearFromDate(album.release_date);

                  const CardInner = (
                    <div
                      style={{
                        border: "1px solid #e5e7eb",
                        borderRadius: "10px",
                        padding: "12px",
                      }}
                    >
                      {album.cover_url ? (
                        <img
                          src={album.cover_url}
                          alt={`Coperta albumului ${album.title}`}
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
                            background: "#f3f4f6",
                          }}
                        />
                      )}

                      <div style={{ marginTop: "10px" }}>
                        <div style={{ fontWeight: 700 }}>{album.title}</div>
                        <div style={{ marginTop: "4px" }}>
                          {album.artist_name}
                        </div>
                        <div style={{ marginTop: "4px", opacity: 0.82 }}>
                          {releaseTypeLabel(album)}
                          {album.songs_count ? ` · ${album.songs_count} piese` : ""}
                        </div>
                        <div style={{ marginTop: "4px", opacity: 0.8 }}>
                          {year}
                        </div>

                        {pickFavoriteSlot ? (
                          <div style={{ marginTop: "10px" }}>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.preventDefault();
                                handlePickFavorite(album);
                              }}
                              disabled={isPickingFavorite}
                              style={ui.buttonSmall}
                            >
                              Setează ca favorit #{pickFavoriteSlot}
                            </button>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  );

                  return album.slug ? (
                    <Link
                      key={album.id}
                      to={
                        pickFavoriteSongSlot
                          ? `/albums/${album.slug}?pickFavoriteSongSlot=${pickFavoriteSongSlot}`
                          : `/albums/${album.slug}`
                      }
                      onMouseEnter={() =>
                        prefetchAlbum({
                          queryClient,
                          baseUrl,
                          slug: album.slug,
                          accessToken,
                          isAuthVerified,
                        })
                      }
                      style={{ color: "inherit", textDecoration: "none" }}
                    >
                      {CardInner}
                    </Link>
                  ) : (
                    <div key={album.id}>{CardInner}</div>
                  );
                })}
              </div>

              <div
                style={{
                  marginTop: "16px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "12px",
                }}
              >
                <button
                  type="button"
                  onClick={() => {
                    setIsLoading(true);
                    setPage((p) => Math.max(1, Number(p || 1) - 1));
                  }}
                  disabled={!pageInfo.previous || page <= 1}
                  style={ui.button}
                >
                  Prev
                </button>

                <div style={{ opacity: 0.85 }}>
                  Page {page}
                  {pageInfo.count ? (
                    <span> — {pageInfo.count} total</span>
                  ) : null}
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setIsLoading(true);
                    setPage((p) => Number(p || 1) + 1);
                  }}
                  disabled={!pageInfo.next}
                  style={ui.button}
                >
                  Next
                </button>
              </div>
            </>
          ) : null}
        </main>
      </div>
    </div>
  );
}
