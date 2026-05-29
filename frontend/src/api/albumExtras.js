import { apiClient } from "./apiClient.js";

export async function getAlbumRecommendations({
  baseUrl,
  albumSlug,
  limit = 12,
}) {
  void baseUrl;
  const response = await apiClient.get(
    `/api/albums/${encodeURIComponent(albumSlug)}/recommendations/`,
    {
      params: { limit },
    },
  );

  return response.data;
}

export async function getAlbumPublicLists({
  baseUrl,
  albumSlug,
  limit = 10,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(
    `/api/albums/${encodeURIComponent(albumSlug)}/user-lists/`,
    {
      params: { limit },
    },
  );

  return response.data;
}

export async function getAlbumComments({ baseUrl, albumSlug, limit = 30 }) {
  void baseUrl;
  const response = await apiClient.get(
    `/api/albums/${encodeURIComponent(albumSlug)}/comments/`,
    {
      params: { limit },
    },
  );

  return response.data;
}
