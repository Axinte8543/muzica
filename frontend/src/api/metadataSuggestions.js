import { apiClient } from "./apiClient.js";

export async function getMetadataSuggestions({ status = "", kind = "" } = {}) {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (kind) params.append("kind", kind);

  const queryString = params.toString();
  const url = `/api/moderation/suggestions/metadata/${queryString ? "?" + queryString : ""}`;

  const response = await apiClient.get(url);
  return response.data;
}

export async function createMetadataSuggestion({
  targetType,
  targetId,
  kind,
  payload = {},
  note = "",
}) {
  const response = await apiClient.post(
    "/api/moderation/suggestions/metadata/",
    {
      target_type: targetType,
      target_id: targetId,
      kind,
      payload,
      note,
    },
  );

  return response.data;
}

export async function approveMetadataSuggestion(suggestionId) {
  const response = await apiClient.post(
    `/api/moderation/suggestions/metadata/${suggestionId}/decision/`,
    { decision: "approve" },
  );

  return response.data;
}

export async function rejectMetadataSuggestion(suggestionId, reason = "") {
  const response = await apiClient.post(
    `/api/moderation/suggestions/metadata/${suggestionId}/decision/`,
    { decision: "reject", reason },
  );

  return response.data;
}
