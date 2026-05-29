import { apiClient } from "./apiClient.js";

export async function getChatMessages({ baseUrl, accessToken, limit = 50 }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/chat/messages`, {
    params: {
      limit,
    },
  });

  return response.data;
}

export async function postChatMessage({ baseUrl, accessToken, content }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/chat/messages`, { content });

  return response.data;
}

export async function getConversations({ baseUrl, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/chat/conversations`);
  return response.data;
}

export async function getMessagesWithUser({ baseUrl, accessToken, userId }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/chat/messages/${userId}`);
  return response.data;
}

export async function sendMessageToUser({
  baseUrl,
  accessToken,
  userId,
  content,
  replyToId,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/chat/messages/${userId}`, {
    recipient_id: userId,
    content,
    reply_to_id: replyToId ?? null,
  });
  return response.data;
}

export async function getTypingStatus({ baseUrl, accessToken, userId }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/chat/typing/${userId}`);
  return response.data;
}

export async function setTypingStatus({
  baseUrl,
  accessToken,
  userId,
  isTyping,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/chat/typing/${userId}`, {
    is_typing: Boolean(isTyping),
  });
  return response.data;
}
