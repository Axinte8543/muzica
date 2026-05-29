import { apiClient } from "./apiClient.js";

export async function getHome({
  baseUrl,
  accessToken,
  recLimit = 8,
  friendsRecLimit = 8,
  activityLimit = 10,
  popularLimit = 10,
  weeklyPopularLimit = 10,
  weeklyListensLimit = 10,
  popularReviewsLimit = 10,
  anticipatedLimit = 10,
  genresLimit = 12,
  bestLimit = 5,
  newLimit = 10,
  recentLimit = 10,
  top2025Limit = 5,
}) {
  // baseUrl/accessToken kept only for backwards compatibility.
  void baseUrl;
  void accessToken;

  const response = await apiClient.get(`/api/home`, {
    params: {
      rec_limit: recLimit,
      friends_rec_limit: friendsRecLimit,
      activity_limit: activityLimit,
      popular_limit: popularLimit,
      weekly_popular_limit: weeklyPopularLimit,
      weekly_listens_limit: weeklyListensLimit,
      popular_reviews_limit: popularReviewsLimit,
      anticipated_limit: anticipatedLimit,
      genres_limit: genresLimit,
      best_limit: bestLimit,
      new_limit: newLimit,
      recent_limit: recentLimit,
      top_2025_limit: top2025Limit,
    },
  });

  return response.data;
}
