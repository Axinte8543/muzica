import { apiClient } from "./apiClient.js";

export async function getCompatibility({ baseUrl, accessToken, userId }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(
    `/api/users/${encodeURIComponent(String(userId))}/compatibility`,
  );

  return response.data;
}
