import { apiClient } from "./apiClient.js";

export async function getAlbumListenStatus({ baseUrl, albumId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/albums/${albumId}/listen`);

  return {
    listenedToday: Boolean(response.data?.listened_today),
  };
}

export async function markAlbumListened({ baseUrl, albumId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/albums/${albumId}/listen`, {});

  return {
    listenedToday: Boolean(response.data?.listened_today),
    created: Boolean(response.data?.created),
  };
}

export async function getMyListens({ baseUrl, accessToken, limit = 100 }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/profile/listens`, {
    params: {
      limit,
    },
  });

  return response.data;
}

export async function getMyListensStats({ baseUrl, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/profile/listens/stats`);

  return response.data;
}
