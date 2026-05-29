import { apiClient } from "./apiClient.js";

// Album Review Reactions

export async function getAlbumReviewReactions({
  baseUrl,
  accessToken,
  reviewId,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/reviews/${reviewId}/reactions`);
  return response.data;
}

export async function toggleAlbumReviewReaction({
  baseUrl,
  accessToken,
  reviewId,
  emoji,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/reviews/${reviewId}/react`, {
    emoji,
  });
  return response.data;
}

// Review Comment Reactions

export async function getReviewCommentReactions({
  baseUrl,
  accessToken,
  commentId,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(
    `/api/review-comments/${commentId}/reactions`,
  );
  return response.data;
}

export async function toggleReviewCommentReaction({
  baseUrl,
  accessToken,
  commentId,
  emoji,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(
    `/api/review-comments/${commentId}/react`,
    {
      emoji,
    },
  );
  return response.data;
}

// Song Comment Reactions

export async function getSongCommentReactions({
  baseUrl,
  accessToken,
  commentId,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(
    `/api/song-comments/${commentId}/reactions`,
  );
  return response.data;
}

export async function toggleSongCommentReaction({
  baseUrl,
  accessToken,
  commentId,
  emoji,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(
    `/api/song-comments/${commentId}/react`,
    {
      emoji,
    },
  );
  return response.data;
}
