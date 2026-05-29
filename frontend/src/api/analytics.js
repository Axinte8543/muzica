import { apiClient } from "./apiClient.js";

export async function trackAnalyticsEvent({
  baseUrl,
  accessToken,
  eventName,
  targetType = "",
  targetId = null,
  properties = {},
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/analytics/events/`, {
    event_name: eventName,
    target_type: targetType,
    target_id: targetId,
    properties,
  });
  return response.data;
}

export async function getAnalyticsKpis({ baseUrl, accessToken, days = 30 }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/analytics/kpis/`, {
    params: {
      days,
    },
  });
  return response.data;
}
