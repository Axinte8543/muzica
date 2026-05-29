import { apiClient } from "./apiClient.js";

export async function getMyStreak() {
  const response = await apiClient.get("/api/profile/streak/");
  return response.data;
}

export async function getWeeklyChallenges() {
  const response = await apiClient.get("/api/profile/challenges/weekly/");
  return response.data;
}

export async function getGamificationStats() {
  const response = await apiClient.get("/api/profile/gamification/");
  return response.data;
}

export async function getMyBadges() {
  const response = await apiClient.get("/api/profile/badges/");
  return response.data;
}

export async function getBadges() {
  const response = await apiClient.get("/api/badges/");
  return response.data;
}

export async function getBadgesByCategory(category) {
  const response = await apiClient.get("/api/badges/by-category/", {
    params: { category },
  });
  return response.data;
}

export async function getMyAchievements() {
  const response = await apiClient.get("/api/profile/achievements/");
  return response.data;
}

export async function getUnlockedAchievements() {
  const response = await apiClient.get("/api/profile/achievements/unlocked/");
  return response.data;
}

export async function getAchievementsInProgress() {
  const response = await apiClient.get(
    "/api/profile/achievements/in-progress/",
  );
  return response.data;
}

export async function getAllAchievements() {
  const response = await apiClient.get("/api/achievements/");
  return response.data;
}

export async function getAchievementsByType(type) {
  const response = await apiClient.get("/api/achievements/by-type/", {
    params: { type },
  });
  return response.data;
}

export async function getMyXP() {
  const response = await apiClient.get("/api/profile/xp/");
  return response.data;
}
