import { apiClient } from "./apiClient.js";

export async function getMyPrivacySettings({ baseUrl, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/profile/privacy`);
  return response.data;
}

export async function updateMyPrivacySettings({
  baseUrl,
  accessToken,
  publicLists,
  publicActivity,
  publicCompatibility,
}) {
  void baseUrl;
  void accessToken;

  const payload = {
    public_lists: Boolean(publicLists),
    public_activity: Boolean(publicActivity),
    public_compatibility: Boolean(publicCompatibility),
  };

  const response = await apiClient.put(`/api/profile/privacy`, payload);
  return response.data;
}
