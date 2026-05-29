import { apiClient } from "./apiClient.js";

export async function getMyLists({ baseUrl, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/lists`);

  return response.data;
}

export async function createList({ baseUrl, name, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/lists`, { name });

  return response.data;
}

export async function getList({ baseUrl, listId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/lists/${listId}`);

  return response.data;
}

export async function renameList({ baseUrl, listId, name, accessToken }) {
  return updateList({ baseUrl, listId, name, accessToken });
}

export async function updateList({
  baseUrl,
  listId,
  name,
  description,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const payload = {};
  if (name !== undefined) payload.name = name;
  if (description !== undefined) payload.description = description;

  const response = await apiClient.put(`/api/lists/${listId}`, payload);

  return response.data;
}

export async function reorderListAlbums({
  baseUrl,
  listId,
  itemIds,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.put(`/api/lists/${listId}/albums/reorder`, {
    item_ids: itemIds,
  });
  return response.data;
}

export async function cloneList({ baseUrl, listId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/lists/${listId}/clone`, {});
  return response.data;
}

export async function deleteList({ baseUrl, listId, accessToken }) {
  void baseUrl;
  void accessToken;
  await apiClient.delete(`/api/lists/${listId}`);
}

export async function addAlbumToList({
  baseUrl,
  listId,
  albumId,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/lists/${listId}/albums`, {
    album_id: albumId,
  });

  return response.data;
}

export async function removeAlbumFromList({
  baseUrl,
  listId,
  albumId,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.delete(`/api/lists/${listId}/albums`, {
    data: { album_id: albumId },
  });

  return response.data;
}

export async function getPublicLists({
  baseUrl,
  sort = "new",
  limit = 20,
  tag,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/lists/public`, {
    params: {
      sort,
      limit,
      ...(tag ? { tag } : {}),
    },
  });

  return response.data;
}

export async function getPublicListDetail({ baseUrl, listId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/lists/public/${listId}`);
  return response.data;
}

export async function getListCollaborators({ baseUrl, listId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.get(`/api/lists/${listId}/collaborators`);
  return response.data;
}

export async function addListCollaborator({
  baseUrl,
  listId,
  username,
  role = "editor",
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/lists/${listId}/collaborators`, {
    username,
    role,
  });
  return response.data;
}

export async function removeListCollaborator({
  baseUrl,
  listId,
  userId,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.delete(
    `/api/lists/${listId}/collaborators`,
    {
      data: { user_id: userId },
    },
  );
  return response.data;
}

export async function updateListTags({ baseUrl, listId, tags, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.put(`/api/lists/${listId}/tags`, {
    tags: Array.isArray(tags) ? tags : [],
  });
  return response.data;
}

export async function updateListAlbumNote({
  baseUrl,
  itemId,
  note,
  accessToken,
}) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.put(`/api/list-albums/${itemId}/note`, {
    note: note ?? "",
  });
  return response.data;
}

export async function likePublicList({ baseUrl, listId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.post(`/api/lists/${listId}/like`, {});
  return response.data;
}

export async function unlikePublicList({ baseUrl, listId, accessToken }) {
  void baseUrl;
  void accessToken;
  const response = await apiClient.delete(`/api/lists/${listId}/like`);
  return response.data;
}
