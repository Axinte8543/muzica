/**
 * Weekly Recap API endpoints
 */

import { apiClient } from "./apiClient.js";

export const getWeeklyRecap = async () => {
  const response = await apiClient.get("/api/recap/weekly/");
  return response.data;
};
