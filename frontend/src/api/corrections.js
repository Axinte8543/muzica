import { apiClient } from "./apiClient.js";

export async function postCorrectionReport({
  baseUrl,
  accessToken,
  pageUrl,
  description,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/corrections`, {
    page_url: pageUrl || "",
    description,
  });

  return response.data;
}
