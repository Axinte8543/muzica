import { apiClient } from "./apiClient.js";

export async function getReviewComments({ baseUrl, reviewId }) {
  void baseUrl;
  const response = await apiClient.get(`/api/reviews/${reviewId}/comments`);
  return response.data;
}

export async function createReviewComment({
  baseUrl,
  reviewId,
  content,
  parentId,
  accessToken,
}) {
  void baseUrl;
  void accessToken;

  const payload = { content };
  if (parentId) payload.parent_id = parentId;

  const response = await apiClient.post(
    `/api/reviews/${reviewId}/comments`,
    payload,
  );
  return response.data;
}
