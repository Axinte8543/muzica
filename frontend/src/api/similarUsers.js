import { apiClient } from "./apiClient.js";

export async function getSimilarUsers({ baseUrl, accessToken, limit }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/users/similar`, {
    params: limit ? { limit } : undefined,
  });

  return response.data;
}
