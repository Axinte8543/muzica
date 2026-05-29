import { apiClient } from "./apiClient.js";

export async function getArtistFollowStatus({
  baseUrl,
  artistId,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/artists/${artistId}/follow`);

  return Boolean(response.data?.is_following);
}

export async function followArtist({ baseUrl, artistId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/artists/${artistId}/follow`, {});

  return Boolean(response.data?.is_following);
}

export async function unfollowArtist({ baseUrl, artistId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.delete(`/api/artists/${artistId}/follow`);

  return Boolean(response.data?.is_following);
}

export async function getFollowedArtists({ baseUrl, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/following/artists`);

  return response.data;
}
