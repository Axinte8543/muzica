import { apiClient } from "./apiClient.js";

export async function getMyProfileStats({ baseUrl, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/profile/stats`);

  return response.data;
}

export async function getMyTopStats({
  baseUrl,
  accessToken,
  period = "month",
  year,
  month,
  limit = 10,
}) {
  void baseUrl;
  void accessToken;

  const params = new URLSearchParams();
  if (period) params.set("period", String(period));
  if (year !== undefined && year !== null && String(year).trim() !== "") {
    params.set("year", String(year));
  }
  if (month !== undefined && month !== null && String(month).trim() !== "") {
    params.set("month", String(month));
  }
  if (limit !== undefined && limit !== null) {
    params.set("limit", String(limit));
  }

  const suffix = params.toString() ? `?${params.toString()}` : "";

  const response = await apiClient.get(`/api/profile/top${suffix}`);

  return response.data;
}
