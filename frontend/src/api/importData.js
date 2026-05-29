import { apiClient } from "./apiClient.js";

export async function importMyDataCsv({ resource, file }) {
  const res = String(resource || "").trim();
  if (!res) throw new Error("resource is required");
  if (!file) throw new Error("file is required");

  const form = new FormData();
  form.append("file", file);

  const response = await apiClient.post(
    `/api/profile/import/?resource=${encodeURIComponent(res)}&format=csv`,
    form,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    },
  );

  return response.data;
}
