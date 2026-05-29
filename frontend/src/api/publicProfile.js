import { apiClient } from "./apiClient.js";

export async function getPublicUserProfile({
  baseUrl,
  username,
  reviewsLimit = 5,
  ratingsLimit = 5,
  activityLimit = 10,
}) {
  void baseUrl;
  const safeUsername = encodeURIComponent(String(username || "").trim());

  const response = await apiClient.get(`/api/users/public/${safeUsername}`, {
    params: {
      reviews_limit: reviewsLimit,
      ratings_limit: ratingsLimit,
      activity_limit: activityLimit,
    },
  });

  return response.data;
}
