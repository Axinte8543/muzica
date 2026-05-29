import { apiClient } from "../api/apiClient.js";

export function albumQueryKey({ baseUrl, slug, accessToken, isAuthVerified }) {
  const effectiveBaseUrl = baseUrl || "";
  const safeSlug = String(slug || "").trim();
  const authKey = isAuthVerified && accessToken ? accessToken : "anon";
  return ["album", effectiveBaseUrl, safeSlug, authKey];
}

export async function fetchAlbumBySlug(slug) {
  const safeSlug = String(slug || "").trim();
  if (!safeSlug) return null;
  const response = await apiClient.get(`/api/albums/${safeSlug}/`);
  return response.data;
}

export function prefetchAlbum({
  queryClient,
  baseUrl,
  slug,
  accessToken,
  isAuthVerified,
}) {
  if (!queryClient) return;
  const safeSlug = String(slug || "").trim();
  if (!safeSlug) return;

  const key = albumQueryKey({
    baseUrl,
    slug: safeSlug,
    accessToken,
    isAuthVerified,
  });

  return queryClient.prefetchQuery({
    queryKey: key,
    queryFn: () => fetchAlbumBySlug(safeSlug),
    staleTime: 60_000,
  });
}
