import { apiClient } from "./apiClient.js";

export async function exportMyDataBlob({
  baseUrl,
  accessToken,
  format = "json",
  resource,
  limit,
}) {
  void baseUrl;
  void accessToken;

  const params = new URLSearchParams();
  if (format) params.set("format", String(format));
  if (resource) params.set("resource", String(resource));
  if (limit !== undefined && limit !== null && String(limit).trim() !== "") {
    params.set("limit", String(limit));
  }

  const suffix = params.toString() ? `?${params.toString()}` : "";

  const response = await apiClient.get(`/api/profile/export${suffix}`, {
    responseType: "blob",
  });

  return response.data;
}
