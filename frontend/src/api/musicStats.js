import { apiClient } from "./apiClient.js";

export async function getMusicStats({ baseUrl, limit }) {
  void baseUrl;
  const response = await apiClient.get(`/api/stats`, {
    params: limit ? { limit } : undefined,
  });

  return response.data;
}
