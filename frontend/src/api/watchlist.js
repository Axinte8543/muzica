import { apiClient } from "./apiClient.js";

export async function getAlbumWantToListenStatus({
  baseUrl,
  albumId,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/albums/${albumId}/want-to-listen`);

  return {
    wanted: Boolean(response.data?.wanted),
  };
}

export async function addAlbumWantToListen({ baseUrl, albumId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(
    `/api/albums/${albumId}/want-to-listen`,
    {},
  );

  return {
    wanted: Boolean(response.data?.wanted),
    created: Boolean(response.data?.created),
  };
}

export async function removeAlbumWantToListen({
  baseUrl,
  albumId,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.delete(
    `/api/albums/${albumId}/want-to-listen`,
  );

  return {
    wanted: Boolean(response.data?.wanted),
  };
}

export async function getMyWantToListen({
  baseUrl,
  accessToken,
  page = 1,
  pageSize = 10,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/profile/want-to-listen`, {
    params: {
      page,
      page_size: pageSize,
    },
  });

  return response.data;
}
