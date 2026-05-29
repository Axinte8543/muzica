import { apiClient } from "./apiClient.js";

export async function getRecommendations({ baseUrl, accessToken, limit }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/recommendations/`, {
    params: limit ? { limit } : undefined,
  });

  return response.data;
}
