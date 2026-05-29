import { useState } from "react";
import { Link } from "react-router-dom";

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

  async function handleSuggestArtist(e) {
    e.preventDefault();
    setStatus({ loading: true, error: "", success: "" });
    try {
      await suggestArtist({ baseUrl, accessToken, ...artistForm });
      setStatus({
        loading: false,
        error: "",
        success: "Artist suggestion submitted.",
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
        success: "Album suggestion submitted.",
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
        success: "Song suggestion submitted.",
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
        Propunerile sunt salvate ca neaprobate și vor apărea după aprobare.
      </div>

      {status.error ? (
        <div style={{ ...ui.errorText, marginBottom: "12px" }}>
          {status.error}
        </div>
      ) : null}
      {status.success ? (
        <div style={{ marginBottom: "12px" }}>{status.success}</div>
      ) : null}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr",
          gap: "12px",
          maxWidth: "720px",
        }}
      >
        <form onSubmit={handleSuggestArtist} style={ui.card}>
          <h3 style={{ marginTop: 0 }}>Artist</h3>
          <div style={{ display: "grid", gap: "8px" }}>
            <input
              style={ui.input}
              placeholder="Name*"
              value={artistForm.name}
              onChange={(e) =>
                setArtistForm((p) => ({ ...p, name: e.target.value }))
              }
              required
            />
            <input
              style={ui.input}
              placeholder="Slug (optional)"
              value={artistForm.slug}
              onChange={(e) =>
                setArtistForm((p) => ({ ...p, slug: e.target.value }))
              }
            />
            <input
              style={ui.input}
              placeholder="Image URL (optional)"
              value={artistForm.image_url}
              onChange={(e) =>
                setArtistForm((p) => ({ ...p, image_url: e.target.value }))
              }
            />
            <input
              style={ui.input}
              placeholder="Aliases (comma-separated, optional)"
              value={artistForm.aliases}
              onChange={(e) =>
                setArtistForm((p) => ({ ...p, aliases: e.target.value }))
              }
            />
            <textarea
              style={{ ...ui.input, minHeight: "90px" }}
              placeholder="Bio (optional)"
              value={artistForm.bio}
              onChange={(e) =>
                setArtistForm((p) => ({ ...p, bio: e.target.value }))
              }
            />
            <button type="submit" style={ui.button} disabled={status.loading}>
              {status.loading ? "Submitting..." : "Submit artist"}
            </button>
          </div>
        </form>

        <form onSubmit={handleSuggestAlbum} style={ui.card}>
          <h3 style={{ marginTop: 0 }}>Album</h3>
          <div style={{ display: "grid", gap: "8px" }}>
            <input
              style={ui.input}
              placeholder="Title*"
              value={albumForm.title}
              onChange={(e) =>
                setAlbumForm((p) => ({ ...p, title: e.target.value }))
              }
              required
            />
            <input
              style={ui.input}
              placeholder="Artist slug (approved artist)*"
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
              placeholder="Cover URL (optional)"
              value={albumForm.cover_url}
              onChange={(e) =>
                setAlbumForm((p) => ({ ...p, cover_url: e.target.value }))
              }
            />
            <input
              style={ui.input}
              placeholder="Slug (optional)"
              value={albumForm.slug}
              onChange={(e) =>
                setAlbumForm((p) => ({ ...p, slug: e.target.value }))
              }
            />
            <textarea
              style={{ ...ui.input, minHeight: "90px" }}
              placeholder="Description (optional)"
              value={albumForm.description}
              onChange={(e) =>
                setAlbumForm((p) => ({ ...p, description: e.target.value }))
              }
            />
            <button type="submit" style={ui.button} disabled={status.loading}>
              {status.loading ? "Submitting..." : "Submit album"}
            </button>
          </div>
        </form>

        <form onSubmit={handleSuggestSong} style={ui.card}>
          <h3 style={{ marginTop: 0 }}>Song</h3>
          <div style={{ display: "grid", gap: "8px" }}>
            <input
              style={ui.input}
              placeholder="Title*"
              value={songForm.title}
              onChange={(e) =>
                setSongForm((p) => ({ ...p, title: e.target.value }))
              }
              required
            />
            <input
              style={ui.input}
              placeholder="Artist slug (approved artist)*"
              value={songForm.artist_slug}
              onChange={(e) =>
                setSongForm((p) => ({ ...p, artist_slug: e.target.value }))
              }
              required
            />
            <input
              style={ui.input}
              placeholder="Album slug (optional, approved album)"
              value={songForm.album_slug}
              onChange={(e) =>
                setSongForm((p) => ({ ...p, album_slug: e.target.value }))
              }
            />
            <input
              style={ui.input}
              type="number"
              min={1}
              placeholder="Track number (optional)"
              value={songForm.track_number}
              onChange={(e) =>
                setSongForm((p) => ({ ...p, track_number: e.target.value }))
              }
            />
            <input
              style={ui.input}
              type="number"
              min={0}
              placeholder="Duration seconds (optional)"
              value={songForm.duration_seconds}
              onChange={(e) =>
                setSongForm((p) => ({ ...p, duration_seconds: e.target.value }))
              }
            />
            <input
              style={ui.input}
              placeholder="Slug (optional)"
              value={songForm.slug}
              onChange={(e) =>
                setSongForm((p) => ({ ...p, slug: e.target.value }))
              }
            />
            <textarea
              style={{ ...ui.input, minHeight: "90px" }}
              placeholder="Description (optional)"
              value={songForm.description}
              onChange={(e) =>
                setSongForm((p) => ({ ...p, description: e.target.value }))
              }
            />
            <button type="submit" style={ui.button} disabled={status.loading}>
              {status.loading ? "Submitting..." : "Submit song"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
