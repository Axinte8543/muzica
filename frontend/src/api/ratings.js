import { apiClient } from "./apiClient.js";

export async function getMyAlbumRating({ baseUrl, albumId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/albums/${albumId}/rate`);

  // Backend returns either {rating: null} or { ... , rating: <int> }
  return response.data?.rating ?? null;
}

export async function rateAlbum({ baseUrl, albumId, rating, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/albums/${albumId}/rate`, {
    rating,
  });

  return response.data;
}

export async function getMySongRating({ baseUrl, songId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/songs/${songId}/rate`);

  return response.data?.rating ?? null;
}

export async function rateSong({ baseUrl, songId, rating, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/songs/${songId}/rate`, {
    rating,
  });

  return response.data;
}

export async function getMyRatings({
  baseUrl,
  accessToken,
  albumPage = 1,
  songPage = 1,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/profile/ratings`, {
    params: {
      album_page: albumPage,
      song_page: songPage,
    },
  });

  return response.data;
}
