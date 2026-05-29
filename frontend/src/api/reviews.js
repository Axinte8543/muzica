import { apiClient } from "./apiClient.js";

export async function getAlbumReviews({ baseUrl, albumId }) {
  void baseUrl;
  const response = await apiClient.get(`/api/albums/${albumId}/reviews`);
  return response.data;
}

export async function createAlbumReview({
  baseUrl,
  albumId,
  title,
  content,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/albums/${albumId}/reviews`, {
    title,
    content,
  });

  return response.data;
}

export async function likeReview({ baseUrl, reviewId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/reviews/${reviewId}/like`, {});

  return response.data;
}

export async function unlikeReview({ baseUrl, reviewId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.delete(`/api/reviews/${reviewId}/like`);

  return response.data;
}

export async function updateReview({
  baseUrl,
  reviewId,
  title,
  content,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.put(`/api/reviews/${reviewId}/`, {
    title,
    content,
  });

  return response.data;
}

export async function getMyReviews({ baseUrl, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/profile/reviews`);

  return response.data;
}

export async function getReviewHistory({ baseUrl, reviewId }) {
  void baseUrl;
  const response = await apiClient.get(`/api/reviews/${reviewId}/history`);
  return response.data;
}

export async function getReviewDraft({ baseUrl, albumId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/albums/${albumId}/review-draft`);
  return response.data;
}

export async function saveReviewDraft({
  baseUrl,
  albumId,
  title,
  content,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.put(`/api/albums/${albumId}/review-draft`, {
    title: title ?? "",
    content: content ?? "",
  });
  return response.data;
}

export async function deleteReviewDraft({ baseUrl, albumId, accessToken }) {
  void baseUrl;
  void accessToken;
  await apiClient.delete(`/api/albums/${albumId}/review-draft`);
}
