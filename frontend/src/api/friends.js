import { apiClient } from "./apiClient.js";

export async function getFriendsList({ baseUrl, accessToken, page = 1 }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/friends/list`, {
    params: {
      page,
    },
  });

  return response.data;
}

export async function sendFriendRequest({
  baseUrl,
  accessToken,
  receiverUsername,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/friends/request`, {
    receiver_username: receiverUsername,
  });

  return response.data;
}

export async function acceptFriendRequest({ baseUrl, accessToken, requestId }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/friends/accept`, {
    request_id: requestId,
  });

  return response.data;
}

export async function rejectFriendRequest({ baseUrl, accessToken, requestId }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/friends/reject`, {
    request_id: requestId,
  });

  return response.data;
}
