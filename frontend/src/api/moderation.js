import { apiClient } from "./apiClient.js";

export async function createModerationReport({
  baseUrl,
  targetType,
  targetId,
  reasonCode,
  reason,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/moderation/reports/`, {
    target_type: targetType,
    target_id: targetId,
    reason_code: reasonCode || undefined,
    reason: reason ?? "",
  });
  return response.data;
}

export async function getMyModerationReports({
  baseUrl,
  status,
  targetType,
  targetId,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const params = {};
  if (status) params.status = status;
  if (targetType) params.target_type = targetType;
  if (targetId) params.target_id = targetId;

  const response = await apiClient.get(`/api/moderation/reports/`, {
    params: Object.keys(params).length ? params : undefined,
  });
  return response.data;
}

export async function createMetadataSuggestion({
  baseUrl,
  targetType,
  targetId,
  kind,
  payload,
  note,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(
    `/api/moderation/suggestions/metadata/`,
    {
      target_type: targetType,
      target_id: targetId,
      kind,
      payload: payload || {},
      note: note ?? "",
    },
  );
  return response.data;
}

export async function getMyMetadataSuggestions({
  baseUrl,
  status,
  kind,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const params = {};
  if (status) params.status = status;
  if (kind) params.kind = kind;

  const response = await apiClient.get(
    `/api/moderation/suggestions/metadata/`,
    {
      params: Object.keys(params).length ? params : undefined,
    },
  );
  return response.data;
}
