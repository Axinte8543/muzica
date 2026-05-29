import { apiClient } from "./apiClient.js";

export async function getSongLikeStatus({ baseUrl, accessToken, songId }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/songs/${songId}/like`);

  return response.data;
}

export async function likeSong({ baseUrl, accessToken, songId }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/songs/${songId}/like`, {});

  return response.data;
}

export async function unlikeSong({ baseUrl, accessToken, songId }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.delete(`/api/songs/${songId}/like`);

  return response.data;
}
