import { apiClient } from "./apiClient.js";

export async function getMyLikedAlbums({ baseUrl, accessToken, page = 1 }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/profile/liked-albums`, {
    params: {
      page,
    },
  });

  return response.data;
}

export async function getAlbumLikeStatus({ baseUrl, accessToken, albumId }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/albums/${albumId}/like`);

  return response.data;
}

export async function likeAlbum({ baseUrl, accessToken, albumId }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/albums/${albumId}/like`, {});

  return response.data;
}

export async function unlikeAlbum({ baseUrl, accessToken, albumId }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.delete(`/api/albums/${albumId}/like`);

  return response.data;
}
