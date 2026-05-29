import { apiClient } from "./apiClient.js";

export async function suggestArtist({
  baseUrl,
  accessToken,
  name,
  slug,
  bio,
  image_url,
  aliases,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/artists/suggest/`, {
    name,
    slug: slug || "",
    bio: bio || "",
    image_url: image_url || "",
    aliases: aliases || "",
  });

  return response.data;
}

export async function suggestAlbum({
  baseUrl,
  accessToken,
  title,
  slug,
  description,
  cover_url,
  release_date,
  artist_slug,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/albums/suggest/`, {
    title,
    slug: slug || "",
    description: description || "",
    cover_url: cover_url || "",
    release_date,
    artist_slug,
  });

  return response.data;
}

export async function suggestSong({
  baseUrl,
  accessToken,
  title,
  slug,
  track_number,
  duration_seconds,
  description,
  artist_slug,
  album_slug,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/songs/suggest/`, {
    title,
    slug: slug || "",
    track_number: track_number === "" ? null : track_number,
    duration_seconds: duration_seconds === "" ? 0 : duration_seconds,
    description: description || "",
    artist_slug,
    album_slug: album_slug || null,
  });

  return response.data;
}
