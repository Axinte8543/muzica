import { apiClient } from "./apiClient.js";

export async function getMyFavoriteSongs({ baseUrl, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/profile/favorite-songs`);

  return response.data;
}

export async function setMyFavoriteSongs({ baseUrl, accessToken, slots }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.put(`/api/profile/favorite-songs`, {
    slots,
  });

  return response.data;
}
