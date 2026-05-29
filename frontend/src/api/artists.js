import { apiClient } from "./apiClient.js";

export async function getSimilarArtists({ baseUrl, slug, limit }) {
  void baseUrl;
  const response = await apiClient.get(
    `/api/artists/${encodeURIComponent(slug)}/similar-artists/`,
    {
      params: limit ? { limit } : undefined,
    },
  );

  return response.data;
}
