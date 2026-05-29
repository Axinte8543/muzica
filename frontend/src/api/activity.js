import { apiClient } from "./apiClient.js";

export async function getActivity({ baseUrl, accessToken, limit = 50 }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/activity`, {
    params: {
      limit,
    },
  });

  return response.data;
}

export async function getFriendsActivity({ baseUrl, accessToken, limit = 50 }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/activity/friends`, {
    params: {
      limit,
    },
  });

  return response.data;
}

export async function getFollowingActivity({
  baseUrl,
  accessToken,
  limit = 50,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/activity/following`, {
    params: {
      limit,
    },
  });

  return response.data;
}
