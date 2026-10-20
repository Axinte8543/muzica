import { apiClient } from "./apiClient.js";

export async function getNotifications({ baseUrl, accessToken, limit = 20 }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/notifications/`, {
    params: {
      limit,
    },
  });

  return response.data;
}

export async function getNotificationPreferences({ baseUrl, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/notifications/preferences/`);
  return response.data;
}

export async function updateNotificationPreferences({
  baseUrl,
  accessToken,
  preferences,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.patch(
    `/api/notifications/preferences/`,
    preferences,
  );
  return response.data;
}

export async function getNotificationsDigest({ baseUrl, accessToken, window }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/notifications/digest/`, {
    params: window ? { window } : undefined,
  });
  return response.data;
}
