/**
 * Onboarding API endpoints
 */

import { apiClient } from "./apiClient.js";

export const setupOnboarding = async ({ genre_ids, artist_ids }) => {
  const response = await apiClient.post(
    "/api/onboarding/setup/",
    {
      genre_ids: genre_ids || [],
      artist_ids: artist_ids || [],
    },
    { requiresAuth: true },
  );
  return response.data;
};

export const getOnboardingStatus = async () => {
  const response = await apiClient.get("/api/onboarding/setup/", {
    requiresAuth: true,
  });
  return response.data;
};
