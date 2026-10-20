import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { apiClient } from "../api/apiClient.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";
import { suggestAlbum, suggestArtist, suggestSong } from "../api/suggest.js";

function getErrorMessage(err) {
  const data = err?.response?.data;
  if (typeof data === "string") return data;
  if (data && typeof data === "object") {
    const firstKey = Object.keys(data)[0];
    if (firstKey) {
      const v = data[firstKey];
      if (Array.isArray(v) && v.length) return String(v[0]);
      return String(v);
    }
  }
  return err?.message || "Something went wrong";
}

export default function SuggestPage() {
  const { baseUrl, accessToken, isAuthenticated, isAuthVerified, logout } =
    useAuth();

  const [artistForm, setArtistForm] = useState({
    name: "",
    slug: "",
    bio: "",
    image_url: "",
    aliases: "",
  });
  const [albumForm, setAlbumForm] = useState({
    title: "",
    artist_slug: "",
    release_date: "",
    cover_url: "",
    description: "",
    slug: "",
  });
  const [songForm, setSongForm] = useState({
    title: "",
    artist_slug: "",
    album_slug: "",
    track_number: "",
    duration_seconds: "",
    description: "",
    slug: "",
  });

  const [status, setStatus] = useState({
    loading: false,
    error: "",
    success: "",
  });
  const [activeTab, setActiveTab] = useState("artist");
  const [artistOptions, setArtistOptions] = useState([]);
  const [albumOptions, setAlbumOptions] = useState([]);

  const artistQuery =
    activeTab === "album"
      ? albumForm.artist_slug
      : activeTab === "song"
        ? songForm.artist_slug
        : "";
  const albumQuery = activeTab === "song" ? songForm.album_slug : "";

  useEffect(() => {
    const query = String(artistQuery || "").trim();
    if (query.length < 2) {
      setArtistOptions([]);
      return undefined;
    }

    let cancelled = false;
    const t = setTimeout(async () => {
      try {
        const res = await apiClient.get("/api/search/", {
          params: { q: query },
        });
        if (cancelled) return;
        setArtistOptions(Array.isArray(res.data?.artists) ? res.data.artists : []);
      } catch (err) {
        if (!cancelled) setArtistOptions([]);
      }
    }, 250);

    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [artistQuery]);

  useEffect(() => {
    const query = String(albumQuery || "").trim();
    if (query.length < 2) {
      setAlbumOptions([]);
      return undefined;
    }

    let cancelled = false;
    const t = setTimeout(async () => {
      try {
        const res = await apiClient.get("/api/search/", {
          params: { q: query },
        });
        if (cancelled) return;
        setAlbumOptions(Array.isArray(res.data?.albums) ? res.data.albums : []);
      } catch (err) {
        if (!cancelled) setAlbumOptions([]);
      }
    }, 250);

    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [albumQuery]);

  const previewItems = useMemo(() => {
    if (activeTab === "artist") {
      return [
        ["Nume", artistForm.name],
        ["Slug", artistForm.slug || "generat automat"],
        ["Imagine", artistForm.image_url || "fără imagine"],
        ["Aliasuri", artistForm.aliases || "fără aliasuri"],
        ["Bio", artistForm.bio || "fără bio"],
      ];
    }
    if (activeTab === "album") {
      return [
        ["Titlu", albumForm.title],
        ["Artist", albumForm.artist_slug],
        ["Data lansării", albumForm.release_date],
        ["Cover", albumForm.cover_url || "fără cover"],
        ["Slug", albumForm.slug || "generat automat"],
        ["Descriere", albumForm.description || "fără descriere"],
      ];
    }
    return [
      ["Titlu", songForm.title],
      ["Artist", songForm.artist_slug],
      ["Release", songForm.album_slug || "single / fără album"],
      ["Nr. piesă", songForm.track_number || "necompletat"],
      ["Durată", songForm.duration_seconds ? `${songForm.duration_seconds}s` : "necompletat"],
      ["Slug", songForm.slug || "generat automat"],
      ["Descriere", songForm.description || "fără descriere"],
    ];
  }, [activeTab, albumForm, artistForm, songForm]);

  const tabButton = (key, label) => (
    <button
      type="button"
      role="tab"
      aria-selected={activeTab === key}
      onClick={() => {
        setActiveTab(key);
        setStatus((prev) => ({ ...prev, error: "", success: "" }));
      }}
      style={{
        ...ui.buttonSmall,
        background:
          activeTab === key ? "rgba(245, 158, 11, 0.18)" : "var(--button-bg)",
      }}
    >
      {label}
    </button>
  );

  async function handleSuggestArtist(e) {
    e.preventDefault();
    setStatus({ loading: true, error: "", success: "" });
    try {
      await suggestArtist({ baseUrl, accessToken, ...artistForm });
      setStatus({
        loading: false,
        error: "",
        success: `Propunerea pentru artistul "${artistForm.name}" a fost trimisă la aprobare.`,
      });
      setArtistForm({
        name: "",
        slug: "",
        bio: "",
        image_url: "",
        aliases: "",
      });
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      setStatus({ loading: false, error: getErrorMessage(err), success: "" });
    }
  }

  async function handleSuggestAlbum(e) {
    e.preventDefault();
    setStatus({ loading: true, error: "", success: "" });
    try {
      await suggestAlbum({ baseUrl, accessToken, ...albumForm });
      setStatus({
        loading: false,
        error: "",
        success: `Propunerea pentru albumul "${albumForm.title}" a fost trimisă la aprobare.`,
      });
      setAlbumForm({
        title: "",
        artist_slug: "",
        release_date: "",
        cover_url: "",
        description: "",
        slug: "",
      });
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      setStatus({ loading: false, error: getErrorMessage(err), success: "" });
    }
  }

  async function handleSuggestSong(e) {
    e.preventDefault();
    setStatus({ loading: true, error: "", success: "" });
    try {
      const payload = {
        ...songForm,
        track_number:
          songForm.track_number === "" ? "" : Number(songForm.track_number),
        duration_seconds:
          songForm.duration_seconds === ""
            ? ""
            : Number(songForm.duration_seconds),
      };
      await suggestSong({ baseUrl, accessToken, ...payload });
      setStatus({
        loading: false,
        error: "",
        success: `Propunerea pentru piesa "${songForm.title}" a fost trimisă la aprobare.`,
      });
      setSongForm({
        title: "",
        artist_slug: "",
        album_slug: "",
        track_number: "",
        duration_seconds: "",
        description: "",
        slug: "",
      });
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      setStatus({ loading: false, error: getErrorMessage(err), success: "" });
    }
  }

  if (!isAuthenticated) {
    return (
      <div style={ui.container}>
        <h2>Propune conținut</h2>
        <p>Trebuie să fii logat ca să propui conținut.</p>
        <p>
          <Link
            to="/login"
            style={{
              ...ui.button,
              textDecoration: "none",
              color: "inherit",
              display: "inline-block",
            }}
          >
            Mergi la Login
          </Link>
        </p>
      </div>
    );
  }

  if (isAuthenticated && !isAuthVerified) {
    return (
      <div style={ui.container}>
        <h2>Propune conținut</h2>
        <p style={{ marginTop: "14px" }}>Se încarcă...</p>
      </div>
    );
  }

  return (
    <div style={ui.container}>
      <h2>Propune conținut</h2>
      <div style={{ opacity: 0.85, marginBottom: "12px" }}>
        Propunerile sunt salvate ca neaprobate și apar în Django Admin pentru aprobare.
      </div>

      {status.error ? (
        <div style={{ ...ui.errorText, marginBottom: "12px" }}>
          {status.error}
        </div>
      ) : null}
      {status.success ? (
        <div
          style={{
            ...ui.card,
            marginBottom: "12px",
            borderColor: "rgba(34, 197, 94, 0.45)",
          }}
        >
          {status.success}
        </div>
      ) : null}

      <div
        role="tablist"
        aria-label="Tip propunere"
        style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "14px" }}
      >
        {tabButton("artist", "Artist")}
        {tabButton("album", "Album")}
        {tabButton("song", "Melodie")}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "14px",
          alignItems: "start",
        }}
      >
        {activeTab === "artist" ? (
        <form onSubmit={handleSuggestArtist} style={ui.card}>
          <h3 style={{ marginTop: 0 }}>Artist</h3>
          <div style={{ display: "grid", gap: "8px" }}>
            <input
              style={ui.input}
              placeholder="Nume*"
              value={artistForm.name}
              onChange={(e) =>
                setArtistForm((p) => ({ ...p, name: e.target.value }))
              }
              required
            />
            <input
              style={ui.input}
              placeholder="Slug (opțional)"
              value={artistForm.slug}
              onChange={(e) =>
                setArtistForm((p) => ({ ...p, slug: e.target.value }))
              }
            />
            <input
              style={ui.input}
              placeholder="URL imagine (opțional)"
              value={artistForm.image_url}
              onChange={(e) =>
                setArtistForm((p) => ({ ...p, image_url: e.target.value }))
              }
            />
            <input
              style={ui.input}
              placeholder="Aliasuri (separate prin virgulă, opțional)"
              value={artistForm.aliases}
              onChange={(e) =>
                setArtistForm((p) => ({ ...p, aliases: e.target.value }))
              }
            />
            <textarea
              style={{ ...ui.input, minHeight: "90px" }}
              placeholder="Bio (opțional)"
              value={artistForm.bio}
              onChange={(e) =>
                setArtistForm((p) => ({ ...p, bio: e.target.value }))
              }
            />
            <button type="submit" style={ui.button} disabled={status.loading}>
              {status.loading ? "Se trimite..." : "Trimite artist"}
            </button>
          </div>
        </form>
        ) : null}

        {activeTab === "album" ? (
        <form onSubmit={handleSuggestAlbum} style={ui.card}>
          <h3 style={{ marginTop: 0 }}>Album</h3>
          <div style={{ display: "grid", gap: "8px" }}>
            <input
              style={ui.input}
              placeholder="Titlu*"
              value={albumForm.title}
              onChange={(e) =>
                setAlbumForm((p) => ({ ...p, title: e.target.value }))
              }
              required
            />
            <input
              style={ui.input}
              list="artist-suggestions"
              placeholder="Artist aprobat: nume sau slug*"
              value={albumForm.artist_slug}
              onChange={(e) =>
                setAlbumForm((p) => ({ ...p, artist_slug: e.target.value }))
              }
              required
            />
            <input
              style={ui.input}
              type="date"
              value={albumForm.release_date}
              onChange={(e) =>
                setAlbumForm((p) => ({ ...p, release_date: e.target.value }))
              }
              required
            />
            <input
              style={ui.input}
              placeholder="URL cover (opțional)"
              value={albumForm.cover_url}
              onChange={(e) =>
                setAlbumForm((p) => ({ ...p, cover_url: e.target.value }))
              }
            />
            <input
              style={ui.input}
              placeholder="Slug (opțional)"
              value={albumForm.slug}
              onChange={(e) =>
                setAlbumForm((p) => ({ ...p, slug: e.target.value }))
              }
            />
            <textarea
              style={{ ...ui.input, minHeight: "90px" }}
              placeholder="Descriere (opțional)"
              value={albumForm.description}
              onChange={(e) =>
                setAlbumForm((p) => ({ ...p, description: e.target.value }))
              }
            />
            <button type="submit" style={ui.button} disabled={status.loading}>
              {status.loading ? "Se trimite..." : "Trimite album"}
            </button>
          </div>
        </form>
        ) : null}

        {activeTab === "song" ? (
        <form onSubmit={handleSuggestSong} style={ui.card}>
          <h3 style={{ marginTop: 0 }}>Melodie</h3>
          <div style={{ display: "grid", gap: "8px" }}>
            <input
              style={ui.input}
              placeholder="Titlu*"
              value={songForm.title}
              onChange={(e) =>
                setSongForm((p) => ({ ...p, title: e.target.value }))
              }
              required
            />
            <input
              style={ui.input}
              list="artist-suggestions"
              placeholder="Artist aprobat: nume sau slug*"
              value={songForm.artist_slug}
              onChange={(e) =>
                setSongForm((p) => ({ ...p, artist_slug: e.target.value }))
              }
              required
            />
            <input
              style={ui.input}
              list="album-suggestions"
              placeholder="Album/release aprobat: titlu sau slug (opțional)"
              value={songForm.album_slug}
              onChange={(e) =>
                setSongForm((p) => ({ ...p, album_slug: e.target.value }))
              }
            />
            <input
              style={ui.input}
              type="number"
              min={1}
              placeholder="Număr piesă (opțional)"
              value={songForm.track_number}
              onChange={(e) =>
                setSongForm((p) => ({ ...p, track_number: e.target.value }))
              }
            />
            <input
              style={ui.input}
              type="number"
              min={0}
              placeholder="Durată în secunde (opțional)"
              value={songForm.duration_seconds}
              onChange={(e) =>
                setSongForm((p) => ({ ...p, duration_seconds: e.target.value }))
              }
            />
            <input
              style={ui.input}
              placeholder="Slug (opțional)"
              value={songForm.slug}
              onChange={(e) =>
                setSongForm((p) => ({ ...p, slug: e.target.value }))
              }
            />
            <textarea
              style={{ ...ui.input, minHeight: "90px" }}
              placeholder="Descriere (opțional)"
              value={songForm.description}
              onChange={(e) =>
                setSongForm((p) => ({ ...p, description: e.target.value }))
              }
            />
            <button type="submit" style={ui.button} disabled={status.loading}>
              {status.loading ? "Se trimite..." : "Trimite melodie"}
            </button>
          </div>
        </form>
        ) : null}

        <aside style={{ ...ui.card, position: "sticky", top: "14px" }}>
          <h3 style={{ marginTop: 0 }}>Preview</h3>
          <div style={{ display: "grid", gap: "8px" }}>
            {previewItems.map(([label, value]) => (
              <div
                key={label}
                style={{
                  borderBottom: "1px solid var(--border-color)",
                  paddingBottom: "8px",
                }}
              >
                <div style={{ opacity: 0.72, fontSize: "0.88em" }}>{label}</div>
                <div style={{ fontWeight: 700, overflowWrap: "anywhere" }}>
                  {value || "necompletat"}
                </div>
              </div>
            ))}
          </div>
        </aside>
      </div>

      <datalist id="artist-suggestions">
        {artistOptions.map((item) => (
          <option key={item.id || item.slug || item.name} value={item.slug || item.name}>
            {item.name}
          </option>
        ))}
      </datalist>
      <datalist id="album-suggestions">
        {albumOptions.map((item) => (
          <option key={item.id || item.slug || item.title} value={item.slug || item.title}>
            {item.title} {item.artist_name ? `- ${item.artist_name}` : ""}
          </option>
        ))}
      </datalist>
    </div>
  );
}
