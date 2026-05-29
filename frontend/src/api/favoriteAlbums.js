import { apiClient } from "./apiClient.js";

export async function getMyFavoriteAlbums({ baseUrl, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/profile/favorite-albums`);

  return response.data;
}

export async function setMyFavoriteAlbums({ baseUrl, accessToken, slots }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.put(`/api/profile/favorite-albums`, {
    slots,
  });

  return response.data;
}
