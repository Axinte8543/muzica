import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  addAlbumToList,
  addListCollaborator,
  cloneList,
  createList,
  deleteList,
  getMyLists,
  getPublicLists,
  removeListCollaborator,
  likePublicList,
  reorderListAlbums,
  removeAlbumFromList,
  unlikePublicList,
  updateListAlbumNote,
  updateListTags,
  updateList,
} from "../api/lists.js";
import { apiClient } from "../api/apiClient.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

export default function ListsPage() {
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken, logout } =
    useAuth();

  const [lists, setLists] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const [publicNew, setPublicNew] = useState([]);
  const [publicLiked, setPublicLiked] = useState([]);
  const [isLoadingPublic, setIsLoadingPublic] = useState(false);
  const [publicError, setPublicError] = useState(null);
  const [publicTagValue, setPublicTagValue] = useState("");
  const [publicTag, setPublicTag] = useState("");

  const [newListName, setNewListName] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const [selectedListId, setSelectedListId] = useState(null);
  const [renameValue, setRenameValue] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);

  const [descriptionValue, setDescriptionValue] = useState("");
  const [isSavingDescription, setIsSavingDescription] = useState(false);
  const [isReordering, setIsReordering] = useState(false);
  const [isCloning, setIsCloning] = useState(false);

  const [tagsValue, setTagsValue] = useState("");
  const [isSavingTags, setIsSavingTags] = useState(false);

  const [collabUsername, setCollabUsername] = useState("");
  const [collabRole, setCollabRole] = useState("editor");
  const [isAddingCollab, setIsAddingCollab] = useState(false);
  const [removingCollabUserId, setRemovingCollabUserId] = useState(null);

  const [noteEdits, setNoteEdits] = useState(() => ({}));
  const [savingNoteItemId, setSavingNoteItemId] = useState(null);
  const [draggingItemId, setDraggingItemId] = useState(null);

  const [albumInput, setAlbumInput] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [isDeletingList, setIsDeletingList] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);
  const [myListFilter, setMyListFilter] = useState("");
  const [likePendingIds, setLikePendingIds] = useState(() => new Set());

  const [lastRemoved, setLastRemoved] = useState(null);
  const [isUndoingRemove, setIsUndoingRemove] = useState(false);

  const visibleLists = useMemo(() => {
    const query = String(myListFilter || "")
      .trim()
      .toLowerCase();
    const arr = Array.isArray(lists) ? lists : [];
    if (!query) return arr;
    return arr.filter((item) =>
      String(item?.name || "")
        .toLowerCase()
        .includes(query),
    );
  }, [lists, myListFilter]);

  const myListsCount = useMemo(() => {
    return Array.isArray(lists) ? lists.length : 0;
  }, [lists]);

  const selectedList = useMemo(() => {
    if (!selectedListId) return null;
    return (Array.isArray(lists) ? lists : []).find(
      (l) => String(l.id) === String(selectedListId),
    );
  }, [lists, selectedListId]);

  useEffect(() => {
    setRenameValue(selectedList?.name ? String(selectedList.name) : "");
  }, [selectedList?.id, selectedList?.name]);

  useEffect(() => {
    setDescriptionValue(
      selectedList?.description ? String(selectedList.description) : "",
    );
  }, [selectedList?.id, selectedList?.description]);

  useEffect(() => {
    const tags = Array.isArray(selectedList?.tags) ? selectedList.tags : [];
    setTagsValue(tags.join(", "));
  }, [selectedList?.id, selectedList?.tags]);

  useEffect(() => {
    // reset local note edits when switching lists
    setNoteEdits({});
    setSavingNoteItemId(null);
    setDraggingItemId(null);
    setStatusMessage(null);
  }, [selectedList?.id]);

  useEffect(() => {
    let isCancelled = false;

    async function loadLists() {
      if (!isAuthVerified || !accessToken) {
        setLists([]);
        setSelectedListId(null);
        setIsLoading(false);
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const data = await getMyLists({ baseUrl, accessToken });
        if (isCancelled) return;
        const next = Array.isArray(data) ? data : [];
        setLists(next);

        setSelectedListId((prev) => {
          if (prev && next.some((l) => String(l?.id) === String(prev))) {
            return prev;
          }
          return next.length ? next[0].id : null;
        });
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled) {
          setLists([]);
          setError("Nu am putut încărca listele.");
        }
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    loadLists();

    return () => {
      isCancelled = true;
    };
  }, [accessToken, baseUrl, isAuthVerified, logout]);

  useEffect(() => {
    let isCancelled = false;

    async function loadPublic() {
      setIsLoadingPublic(true);
      setPublicError(null);

      try {
        const [newest, liked] = await Promise.all([
          getPublicLists({
            baseUrl,
            sort: "new",
            limit: 20,
            tag: publicTag || undefined,
            accessToken: isAuthVerified ? accessToken : undefined,
          }),
          getPublicLists({
            baseUrl,
            sort: "liked",
            limit: 20,
            tag: publicTag || undefined,
            accessToken: isAuthVerified ? accessToken : undefined,
          }),
        ]);

        if (isCancelled) return;
        setPublicNew(Array.isArray(newest) ? newest : []);
        setPublicLiked(Array.isArray(liked) ? liked : []);
      } catch (err) {
        if (err?.response?.status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled) {
          setPublicNew([]);
          setPublicLiked([]);
          setPublicError("Nu am putut încărca listele publice.");
        }
      } finally {
        if (!isCancelled) setIsLoadingPublic(false);
      }
    }

    loadPublic();

    return () => {
      isCancelled = true;
    };
  }, [baseUrl, isAuthVerified, accessToken, logout, publicTag]);

  const selectedRole = String(selectedList?.my_role || "").toLowerCase();
  const isOwner = selectedRole === "owner";
  const canEditList = selectedRole === "owner" || selectedRole === "editor";

  function normalizeAlbumSlug(raw) {
    const input = String(raw || "").trim();
    if (!input) return "";

    if (/^\d+$/.test(input)) return input;

    const withoutHash = input.split("#")[0].split("?")[0];
    const fromPath = withoutHash.match(/\/albums\/([^/]+)\/?$/i);
    if (fromPath?.[1]) return fromPath[1];

    return withoutHash.replace(/^\/+|\/+$/g, "");
  }

  async function resolveAlbumId(rawInput) {
    const normalized = normalizeAlbumSlug(rawInput);
    if (!normalized) return null;

    if (/^\d+$/.test(normalized)) {
      const id = Number(normalized);
      return Number.isFinite(id) && id > 0 ? id : null;
    }

    try {
      const response = await apiClient.get(`/api/albums/${normalized}/`);
      const resolvedId = Number(response?.data?.id);
      return Number.isFinite(resolvedId) && resolvedId > 0 ? resolvedId : null;
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return null;
      }
      return null;
    }
  }

  async function toggleLike(listItem) {
    if (!isAuthVerified || !accessToken) return;
    if (!listItem?.id) return;

    const listId = listItem.id;
    if (likePendingIds.has(String(listId))) return;
    const isLiked = Boolean(listItem?.is_liked);

    setLikePendingIds((prev) => {
      const next = new Set(prev);
      next.add(String(listId));
      return next;
    });

    const applyUpdate = (arrSetter) => {
      arrSetter((prev) => {
        const arr = Array.isArray(prev) ? prev : [];
        return arr.map((l) => {
          if (String(l.id) !== String(listId)) return l;
          const nextLiked = !isLiked;
          const nextCount = Math.max(
            0,
            Number(l.likes_count ?? 0) + (nextLiked ? 1 : -1),
          );
          return { ...l, is_liked: nextLiked, likes_count: nextCount };
        });
      });
    };

    // optimistic update
    applyUpdate(setPublicNew);
    applyUpdate(setPublicLiked);

    try {
      if (isLiked) {
        await unlikePublicList({ baseUrl, listId, accessToken });
      } else {
        await likePublicList({ baseUrl, listId, accessToken });
      }
      setStatusMessage(isLiked ? "Like eliminat." : "Like adaugat.");
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      // rollback
      applyUpdate(setPublicNew);
      applyUpdate(setPublicLiked);
      setError("Nu am putut actualiza like-ul.");
    } finally {
      setLikePendingIds((prev) => {
        const next = new Set(prev);
        next.delete(String(listId));
        return next;
      });
    }
  }

  async function handleCreateList(e) {
    e.preventDefault();
    if (!isAuthVerified || !accessToken) return;

    const name = newListName.trim();
    if (!name) return;

    setIsCreating(true);
    setError(null);
    setStatusMessage(null);

    try {
      const created = await createList({ baseUrl, name, accessToken });
      setLists((prev) => {
        const arr = Array.isArray(prev) ? prev : [];
        return [created, ...arr];
      });
      setSelectedListId(created?.id || null);
      setNewListName("");
      setStatusMessage("Lista a fost creata.");
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut crea lista.");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleAddAlbum(e) {
    e.preventDefault();
    if (!isAuthVerified || !accessToken) return;

    if (!selectedListId) return;

    const raw = String(albumInput).trim();
    if (!raw) return;

    setIsAdding(true);
    setError(null);
    setStatusMessage(null);

    try {
      const albumIdNum = await resolveAlbumId(raw);
      if (!albumIdNum) {
        setError("Album invalid. Introdu ID, slug sau link de album.");
        return;
      }

      const existsInList = Array.isArray(selectedList?.albums)
        ? selectedList.albums.some(
            (it) => Number(it?.album_id) === Number(albumIdNum),
          )
        : false;
      if (existsInList) {
        setStatusMessage("Albumul este deja in lista.");
        return;
      }

      const updated = await addAlbumToList({
        baseUrl,
        listId: selectedListId,
        albumId: albumIdNum,
        accessToken,
      });

      setLists((prev) => {
        const arr = Array.isArray(prev) ? prev : [];
        return arr.map((l) => (l.id === updated.id ? updated : l));
      });

      setAlbumInput("");
      setStatusMessage("Album adaugat in lista.");
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut adăuga albumul în listă.");
    } finally {
      setIsAdding(false);
    }
  }

  async function handleRemoveAlbum(item) {
    if (!isAuthVerified || !accessToken) return;
    if (!selectedList?.id) return;
    if (!item?.album_id) return;

    const ok = window.confirm(
      `Scoți albumul "${item.album_title}" din lista "${selectedList.name}"?`,
    );
    if (!ok) return;

    setError(null);
    setStatusMessage(null);

    try {
      const updated = await removeAlbumFromList({
        baseUrl,
        listId: selectedList.id,
        albumId: item.album_id,
        accessToken,
      });

      setLists((prev) => {
        const arr = Array.isArray(prev) ? prev : [];
        return arr.map((l) => (l.id === updated.id ? updated : l));
      });

      setLastRemoved({
        listId: selectedList.id,
        listName: selectedList.name,
        item,
      });
      setStatusMessage("Album scos din lista.");
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut scoate albumul din listă.");
    }
  }

  async function handleUndoRemove() {
    if (!isAuthVerified || !accessToken) return;
    if (!lastRemoved?.listId) return;
    if (!lastRemoved?.item?.album_id) return;

    setIsUndoingRemove(true);
    setError(null);
    setStatusMessage(null);

    try {
      const updated = await addAlbumToList({
        baseUrl,
        listId: lastRemoved.listId,
        albumId: lastRemoved.item.album_id,
        accessToken,
      });

      setLists((prev) => {
        const arr = Array.isArray(prev) ? prev : [];
        return arr.map((l) => (l.id === updated.id ? updated : l));
      });

      setLastRemoved(null);
      setStatusMessage("Undo reusit.");
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut face undo.");
    } finally {
      setIsUndoingRemove(false);
    }
  }

  async function handleRenameSelectedList(e) {
    e.preventDefault();
    if (!isAuthVerified || !accessToken) return;
    if (!selectedList?.id) return;
    if (!isOwner) return;

    const name = String(renameValue || "").trim();
    if (!name) return;

    setIsRenaming(true);
    setError(null);
    setStatusMessage(null);

    try {
      const updated = await updateList({
        baseUrl,
        listId: selectedList.id,
        name,
        accessToken,
      });

      setLists((prev) => {
        const arr = Array.isArray(prev) ? prev : [];
        return arr.map((l) => (l.id === updated.id ? updated : l));
      });
      setStatusMessage("Numele listei a fost actualizat.");
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut redenumi lista.");
    } finally {
      setIsRenaming(false);
    }
  }

  async function handleSaveDescription(e) {
    e.preventDefault();
    if (!isAuthVerified || !accessToken) return;
    if (!selectedList?.id) return;
    if (!isOwner) return;

    setIsSavingDescription(true);
    setError(null);
    setStatusMessage(null);

    try {
      const updated = await updateList({
        baseUrl,
        listId: selectedList.id,
        description: String(descriptionValue ?? ""),
        accessToken,
      });

      setLists((prev) => {
        const arr = Array.isArray(prev) ? prev : [];
        return arr.map((l) => (l.id === updated.id ? updated : l));
      });
      setStatusMessage("Descriere salvata.");
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut salva descrierea.");
    } finally {
      setIsSavingDescription(false);
    }
  }

  async function handleCloneSelectedList() {
    if (!isAuthVerified || !accessToken) return;
    if (!selectedList?.id) return;

    const ok = window.confirm(
      `Clonezi lista "${selectedList.name}" în contul tău?`,
    );
    if (!ok) return;

    setIsCloning(true);
    setError(null);

    try {
      const cloned = await cloneList({
        baseUrl,
        listId: selectedList.id,
        accessToken,
      });

      setLists((prev) => {
        const arr = Array.isArray(prev) ? prev : [];
        return [cloned, ...arr];
      });
      setSelectedListId(cloned?.id || null);
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut clona lista.");
    } finally {
      setIsCloning(false);
    }
  }

  async function handleMoveAlbum(itemId, delta) {
    if (!isAuthVerified || !accessToken) return;
    if (!selectedList?.id) return;
    if (!canEditList) return;
    if (!Array.isArray(selectedList?.albums)) return;
    if (isReordering) return;

    const items = selectedList.albums;
    const idx = items.findIndex((x) => String(x.id) === String(itemId));
    if (idx < 0) return;

    const nextIdx = idx + delta;
    if (nextIdx < 0 || nextIdx >= items.length) return;

    const nextItems = [...items];
    const tmp = nextItems[idx];
    nextItems[idx] = nextItems[nextIdx];
    nextItems[nextIdx] = tmp;

    // optimistic update
    setLists((prev) => {
      const arr = Array.isArray(prev) ? prev : [];
      return arr.map((l) => {
        if (String(l.id) !== String(selectedList.id)) return l;
        return { ...l, albums: nextItems };
      });
    });

    setIsReordering(true);
    setError(null);

    try {
      const updated = await reorderListAlbums({
        baseUrl,
        listId: selectedList.id,
        itemIds: nextItems.map((x) => x.id),
        accessToken,
      });
      setLists((prev) => {
        const arr = Array.isArray(prev) ? prev : [];
        return arr.map((l) => (l.id === updated.id ? updated : l));
      });
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut reordona lista.");
      // best-effort reload
      try {
        const data = await getMyLists({ baseUrl, accessToken });
        const next = Array.isArray(data) ? data : [];
        setLists(next);
      } catch (reloadErr) {
        if (reloadErr?.response?.status === 401) {
          logout();
          return;
        }
        console.error(reloadErr);
      }
    } finally {
      setIsReordering(false);
    }
  }

  async function handleDeleteSelectedList() {
    if (!isAuthVerified || !accessToken) return;
    if (!selectedList?.id) return;
    if (!isOwner) return;

    const ok = window.confirm(
      `Sigur vrei să ștergi lista "${selectedList.name}"?`,
    );
    if (!ok) return;

    setError(null);
    setStatusMessage(null);
    setIsDeletingList(true);

    try {
      await deleteList({ baseUrl, listId: selectedList.id, accessToken });

      setLists((prev) => {
        const arr = Array.isArray(prev) ? prev : [];
        const next = arr.filter((l) => l.id !== selectedList.id);
        setSelectedListId((prevId) => {
          if (String(prevId) !== String(selectedList.id)) return prevId;
          return next.length ? next[0].id : null;
        });
        return next;
      });
      setStatusMessage("Lista a fost stearsa.");
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut șterge lista.");
    } finally {
      setIsDeletingList(false);
    }
  }

  async function handleSaveTags(e) {
    e.preventDefault();
    if (!isAuthVerified || !accessToken) return;
    if (!selectedList?.id) return;
    if (!isOwner) return;

    const tags = String(tagsValue || "")
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    setIsSavingTags(true);
    setError(null);
    setStatusMessage(null);
    try {
      const updated = await updateListTags({
        baseUrl,
        listId: selectedList.id,
        tags,
        accessToken,
      });
      setLists((prev) => {
        const arr = Array.isArray(prev) ? prev : [];
        return arr.map((l) => (l.id === updated.id ? updated : l));
      });
      setStatusMessage("Tagurile au fost salvate.");
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut salva tagurile.");
    } finally {
      setIsSavingTags(false);
    }
  }

  async function handleAddCollaborator(e) {
    e.preventDefault();
    if (!isAuthVerified || !accessToken) return;
    if (!selectedList?.id) return;
    if (!isOwner) return;

    const username = String(collabUsername || "").trim();
    if (!username) return;

    setIsAddingCollab(true);
    setError(null);
    try {
      const updated = await addListCollaborator({
        baseUrl,
        listId: selectedList.id,
        username,
        role: collabRole,
        accessToken,
      });
      setLists((prev) => {
        const arr = Array.isArray(prev) ? prev : [];
        return arr.map((l) => (l.id === updated.id ? updated : l));
      });
      setCollabUsername("");
      setCollabRole("editor");
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut adăuga colaborator.");
    } finally {
      setIsAddingCollab(false);
    }
  }

  async function handleRemoveCollaborator(userId) {
    if (!isAuthVerified || !accessToken) return;
    if (!selectedList?.id) return;
    if (!isOwner) return;
    if (!userId) return;

    setRemovingCollabUserId(userId);
    setError(null);
    try {
      const updated = await removeListCollaborator({
        baseUrl,
        listId: selectedList.id,
        userId,
        accessToken,
      });
      setLists((prev) => {
        const arr = Array.isArray(prev) ? prev : [];
        return arr.map((l) => (l.id === updated.id ? updated : l));
      });
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut elimina colaboratorul.");
    } finally {
      setRemovingCollabUserId(null);
    }
  }

  async function saveNote(itemId) {
    if (!isAuthVerified || !accessToken) return;
    if (!canEditList) return;
    if (!itemId) return;

    const note = noteEdits[String(itemId)];
    setSavingNoteItemId(itemId);
    try {
      const updated = await updateListAlbumNote({
        baseUrl,
        itemId,
        note: note ?? "",
        accessToken,
      });

      setLists((prev) => {
        const arr = Array.isArray(prev) ? prev : [];
        return arr.map((l) => {
          if (String(l.id) !== String(selectedList?.id)) return l;
          const albums = Array.isArray(l.albums) ? l.albums : [];
          return {
            ...l,
            albums: albums.map((it) => (it.id === updated.id ? updated : it)),
          };
        });
      });
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut salva nota.");
    } finally {
      setSavingNoteItemId(null);
    }
  }

  async function reorderByDrag(fromId, toId) {
    if (!isAuthVerified || !accessToken) return;
    if (!selectedList?.id) return;
    if (!canEditList) return;
    if (isReordering) return;
    if (!fromId || !toId) return;

    const items = Array.isArray(selectedList?.albums)
      ? selectedList.albums
      : [];
    const fromIdx = items.findIndex((x) => String(x.id) === String(fromId));
    const toIdx = items.findIndex((x) => String(x.id) === String(toId));
    if (fromIdx < 0 || toIdx < 0 || fromIdx === toIdx) return;

    const nextItems = [...items];
    const [moved] = nextItems.splice(fromIdx, 1);
    nextItems.splice(toIdx, 0, moved);

    // optimistic update
    setLists((prev) => {
      const arr = Array.isArray(prev) ? prev : [];
      return arr.map((l) => {
        if (String(l.id) !== String(selectedList.id)) return l;
        return { ...l, albums: nextItems };
      });
    });

    setIsReordering(true);
    setError(null);
    try {
      const updated = await reorderListAlbums({
        baseUrl,
        listId: selectedList.id,
        itemIds: nextItems.map((x) => x.id),
        accessToken,
      });
      setLists((prev) => {
        const arr = Array.isArray(prev) ? prev : [];
        return arr.map((l) => (l.id === updated.id ? updated : l));
      });
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      setError("Nu am putut reordona lista.");
    } finally {
      setIsReordering(false);
    }
  }

  return (
    <div
      style={{
        ...ui.container,
        maxWidth: "1280px",
        margin: "0 auto",
      }}
    >
      <h1 style={{ marginTop: 0 }}>Liste</h1>

      {statusMessage ? (
        <div style={{ ...ui.card, marginTop: "12px", opacity: 0.95 }}>
          {statusMessage}
        </div>
      ) : null}

      {isAuthenticated && !isAuthVerified ? (
        <p style={{ marginTop: "14px" }}>Se încarcă...</p>
      ) : null}

      {isAuthenticated && selectedList ? (
        <div style={{ ...ui.card, marginTop: "12px" }}>
          <h3 style={{ marginTop: 0 }}>Lista selectată</h3>

          <p style={{ marginTop: "6px", opacity: 0.8 }}>
            Gestionează rapid detaliile listei tale, apoi adaugă albume în
            secțiunea de conținut de mai jos.
          </p>

          <div style={{ opacity: 0.85, marginBottom: "8px" }}>
            Rol: <strong>{selectedRole || "owner"}</strong>
          </div>

          <form onSubmit={handleRenameSelectedList}>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <input
                type="text"
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                placeholder="Numele listei"
                style={{ padding: "8px", minWidth: "260px" }}
                disabled={!isOwner}
              />
              <button type="submit" disabled={isRenaming || !isOwner}>
                {isRenaming ? "Se salvează..." : "Rename"}
              </button>
              <button
                type="button"
                disabled={isCloning || !selectedList?.id}
                onClick={handleCloneSelectedList}
              >
                {isCloning ? "Se clonează..." : "Clone"}
              </button>
              <button
                type="button"
                disabled={isDeletingList || !isOwner}
                onClick={handleDeleteSelectedList}
              >
                {isDeletingList ? "Se șterge..." : "Delete list"}
              </button>
            </div>
          </form>

          <form onSubmit={handleSaveDescription} style={{ marginTop: "10px" }}>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <textarea
                value={descriptionValue}
                onChange={(e) => setDescriptionValue(e.target.value)}
                placeholder="Descriere (opțional)"
                rows={3}
                style={{ minWidth: "360px", flex: 1, ...ui.input }}
                disabled={!isOwner}
              />
              <button type="submit" disabled={isSavingDescription}>
                {isSavingDescription ? "Se salvează..." : "Salvează descriere"}
              </button>
            </div>
          </form>

          <form onSubmit={handleSaveTags} style={{ marginTop: "10px" }}>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <input
                value={tagsValue}
                onChange={(e) => setTagsValue(e.target.value)}
                placeholder="Taguri (separate prin virgulă)"
                style={{ minWidth: "360px", flex: 1, ...ui.input }}
                disabled={!isOwner}
              />
              <button type="submit" disabled={isSavingTags || !isOwner}>
                {isSavingTags ? "Se salvează..." : "Salvează taguri"}
              </button>
            </div>
          </form>

          <div style={{ marginTop: "10px" }}>
            <details>
              <summary style={{ cursor: "pointer" }}>Colaboratori</summary>

              {!isOwner ? (
                <div style={{ marginTop: "8px", opacity: 0.85 }}>
                  Doar owner-ul poate invita/elimina colaboratori.
                </div>
              ) : (
                <>
                  <form
                    onSubmit={handleAddCollaborator}
                    style={{
                      display: "flex",
                      gap: "8px",
                      alignItems: "center",
                      flexWrap: "wrap",
                      marginTop: "8px",
                    }}
                  >
                    <input
                      value={collabUsername}
                      onChange={(e) => setCollabUsername(e.target.value)}
                      placeholder="Username"
                      style={{ width: "220px", ...ui.input }}
                    />
                    <select
                      value={collabRole}
                      onChange={(e) => setCollabRole(e.target.value)}
                      style={ui.input}
                    >
                      <option value="editor">editor</option>
                    </select>
                    <button
                      type="submit"
                      disabled={isAddingCollab}
                      style={ui.button}
                    >
                      {isAddingCollab ? "Se adaugă..." : "Invită"}
                    </button>
                  </form>

                  {Array.isArray(selectedList?.collaborators) &&
                  selectedList.collaborators.length ? (
                    <ul style={{ paddingLeft: "18px", marginTop: "10px" }}>
                      {selectedList.collaborators.map((c) => (
                        <li key={c.user_id} style={{ marginBottom: "6px" }}>
                          <span>
                            <strong>{c.username}</strong>
                            <span style={{ opacity: 0.85 }}>
                              {c.role ? ` — ${c.role}` : ""}
                            </span>
                          </span>
                          <button
                            type="button"
                            style={{ ...ui.buttonSmall, marginLeft: "10px" }}
                            disabled={
                              removingCollabUserId === c.user_id ||
                              isAddingCollab
                            }
                            onClick={() => handleRemoveCollaborator(c.user_id)}
                          >
                            {removingCollabUserId === c.user_id
                              ? "Se elimină..."
                              : "Remove"}
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div style={{ marginTop: "10px", opacity: 0.85 }}>
                      Nu există colaboratori.
                    </div>
                  )}
                </>
              )}
            </details>
          </div>
        </div>
      ) : null}

      <section style={{ ...ui.card, marginTop: "16px" }}>
        <h3 style={{ marginTop: 0, marginBottom: "10px" }}>
          Explorează liste publice
        </h3>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <input
            value={publicTagValue}
            onChange={(e) => setPublicTagValue(e.target.value)}
            placeholder="Filtru tag (opțional)"
            style={{ width: "260px", ...ui.input }}
          />
          <button
            type="button"
            style={ui.button}
            onClick={() => setPublicTag(String(publicTagValue || "").trim())}
          >
            Aplică
          </button>
          <button
            type="button"
            style={ui.button}
            onClick={() => {
              setPublicTagValue("");
              setPublicTag("");
            }}
          >
            Clear
          </button>
        </div>

        {isLoadingPublic ? (
          <p style={{ marginTop: "12px" }}>Se încarcă...</p>
        ) : null}
        {publicError ? (
          <p style={{ ...ui.errorText, marginTop: "12px" }}>{publicError}</p>
        ) : null}

        {!isLoadingPublic && !publicError ? (
          <div
            style={{
              display: "grid",
              gap: "14px",
              gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
              marginTop: "14px",
            }}
          >
            <div style={{ ...ui.card, padding: "12px" }}>
              <h4 style={{ margin: "0 0 8px" }}>Cele mai noi liste</h4>
              {Array.isArray(publicNew) && publicNew.length ? (
                <ul
                  style={{
                    listStyle: "none",
                    padding: 0,
                    margin: 0,
                    display: "grid",
                    gap: "8px",
                  }}
                >
                  {publicNew.map((l) => (
                    <li
                      key={`new-${l.id}`}
                      style={{ ...ui.card, padding: "10px 12px" }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: "10px",
                          alignItems: "center",
                        }}
                      >
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontWeight: 700 }}>
                            <Link to={`/lists/public/${l.id}`}>{l.name}</Link>
                          </div>
                          <div style={{ opacity: 0.85, marginTop: "2px" }}>
                            {l.user_username} · {l.albums_count ?? 0} albume ·
                            ❤️ {l.likes_count ?? 0}
                          </div>
                          {Array.isArray(l.tags) && l.tags.length ? (
                            <div
                              style={{
                                opacity: 0.78,
                                marginTop: "4px",
                                fontSize: "0.9em",
                              }}
                            >
                              Taguri: {l.tags.join(", ")}
                            </div>
                          ) : null}
                        </div>
                        {isAuthenticated ? (
                          <button
                            type="button"
                            style={ui.buttonSmall}
                            disabled={likePendingIds.has(String(l.id))}
                            onClick={() => toggleLike(l)}
                          >
                            {likePendingIds.has(String(l.id))
                              ? "..."
                              : l.is_liked
                                ? "Unlike"
                                : "Like"}
                          </button>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p style={{ margin: 0, opacity: 0.85 }}>
                  Nu există încă liste publice.
                </p>
              )}
            </div>

            <div style={{ ...ui.card, padding: "12px" }}>
              <h4 style={{ margin: "0 0 8px" }}>Cele mai liked liste</h4>
              {Array.isArray(publicLiked) && publicLiked.length ? (
                <ul
                  style={{
                    listStyle: "none",
                    padding: 0,
                    margin: 0,
                    display: "grid",
                    gap: "8px",
                  }}
                >
                  {publicLiked.map((l) => (
                    <li
                      key={`liked-${l.id}`}
                      style={{ ...ui.card, padding: "10px 12px" }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: "10px",
                          alignItems: "center",
                        }}
                      >
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontWeight: 700 }}>
                            <Link to={`/lists/public/${l.id}`}>{l.name}</Link>
                          </div>
                          <div style={{ opacity: 0.85, marginTop: "2px" }}>
                            {l.user_username} · {l.albums_count ?? 0} albume ·
                            ❤️ {l.likes_count ?? 0}
                          </div>
                        </div>
                        {isAuthenticated ? (
                          <button
                            type="button"
                            style={ui.buttonSmall}
                            disabled={likePendingIds.has(String(l.id))}
                            onClick={() => toggleLike(l)}
                          >
                            {likePendingIds.has(String(l.id))
                              ? "..."
                              : l.is_liked
                                ? "Unlike"
                                : "Like"}
                          </button>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p style={{ margin: 0, opacity: 0.85 }}>
                  Nu există încă liste publice.
                </p>
              )}
            </div>
          </div>
        ) : null}
      </section>

      {!isAuthenticated ? (
        <div style={{ marginTop: "18px", opacity: 0.9 }}>
          <p style={{ marginBottom: 0 }}>
            Loghează-te ca să creezi liste și să dai like.
          </p>
          <p style={{ marginTop: "8px" }}>
            <Link to="/login">Mergi la Login</Link>
          </p>
        </div>
      ) : null}

      {isAuthenticated ? (
        <>
          <form
            onSubmit={handleCreateList}
            style={{
              display: "flex",
              gap: "8px",
              alignItems: "center",
              flexWrap: "wrap",
              margin: "18px 0 16px",
            }}
          >
            <input
              value={newListName}
              onChange={(e) => setNewListName(e.target.value)}
              placeholder="Numele listei..."
              style={{
                width: "320px",
                ...ui.input,
              }}
            />
            <button type="submit" disabled={isCreating} style={ui.button}>
              {isCreating ? "Se creează..." : "Creează listă"}
            </button>
          </form>

          {isLoading ? <p>Se încarcă...</p> : null}
          {error ? <p style={ui.errorText}>{error}</p> : null}

          {!isLoading ? (
            <div
              style={{
                display: "flex",
                gap: "16px",
                alignItems: "flex-start",
                flexWrap: "wrap",
              }}
            >
              <div style={{ ...ui.card, minWidth: "260px", flex: "0 0 280px" }}>
                <h3 style={{ marginTop: 0 }}>Listele mele ({myListsCount})</h3>
                {Array.isArray(lists) && lists.length ? (
                  <>
                    <input
                      value={myListFilter}
                      onChange={(e) => setMyListFilter(e.target.value)}
                      placeholder="Cauta in listele tale"
                      style={{
                        ...ui.input,
                        width: "100%",
                        marginBottom: "10px",
                      }}
                    />
                    <ul
                      style={{ paddingLeft: "0", listStyle: "none", margin: 0 }}
                    >
                      {visibleLists.map((l) => {
                        const isActive =
                          String(selectedListId) === String(l.id);
                        return (
                          <li key={l.id} style={{ marginBottom: "8px" }}>
                            <button
                              type="button"
                              onClick={() => setSelectedListId(l.id)}
                              style={{
                                ...ui.buttonSmall,
                                width: "100%",
                                textAlign: "left",
                                background: isActive
                                  ? "rgba(245, 158, 11, 0.16)"
                                  : "var(--button-bg)",
                                borderColor: isActive
                                  ? "rgba(245, 158, 11, 0.34)"
                                  : "var(--border-color)",
                                fontWeight: isActive ? 700 : 500,
                              }}
                            >
                              {l.name} ({l.albums_count ?? 0})
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                    {!visibleLists.length ? (
                      <p style={{ opacity: 0.8, marginTop: "8px" }}>
                        Nicio listă nu corespunde filtrului.
                      </p>
                    ) : null}
                  </>
                ) : (
                  <p>Nu ai încă nicio listă. Creează una de mai sus.</p>
                )}
              </div>

              <div style={{ ...ui.card, flex: "1 1 540px", minWidth: "320px" }}>
                <h3 style={{ marginTop: 0 }}>Conținut</h3>

                {!selectedList ? <p>Selectează o listă.</p> : null}

                {selectedList ? (
                  <>
                    <div style={{ marginBottom: "12px" }}>
                      <strong>{selectedList.name}</strong>
                    </div>

                    {lastRemoved ? (
                      <div
                        style={{
                          ...ui.card,
                          background: ui.colors.mutedBg,
                          marginBottom: "12px",
                          display: "flex",
                          gap: "10px",
                          alignItems: "center",
                          justifyContent: "space-between",
                          flexWrap: "wrap",
                        }}
                      >
                        <div>
                          Ai scos{" "}
                          <strong>{lastRemoved.item?.album_title}</strong>
                          {lastRemoved.item?.artist_name ? (
                            <span style={{ opacity: 0.9 }}>
                              {" "}
                              — {lastRemoved.item.artist_name}
                            </span>
                          ) : null}
                          {lastRemoved.listName ? (
                            <span style={{ opacity: 0.9 }}>
                              {" "}
                              (din lista "{lastRemoved.listName}")
                            </span>
                          ) : null}
                        </div>
                        <button
                          type="button"
                          style={ui.buttonSmall}
                          disabled={isUndoingRemove}
                          onClick={handleUndoRemove}
                        >
                          {isUndoingRemove ? "Se face undo..." : "Undo"}
                        </button>
                      </div>
                    ) : null}

                    <form
                      onSubmit={handleAddAlbum}
                      style={{
                        display: "flex",
                        gap: "8px",
                        alignItems: "center",
                        flexWrap: "wrap",
                        marginBottom: "16px",
                      }}
                    >
                      <input
                        value={albumInput}
                        onChange={(e) => setAlbumInput(e.target.value)}
                        placeholder="ID, slug sau link album"
                        style={{
                          width: "280px",
                          ...ui.input,
                        }}
                        disabled={!canEditList}
                      />
                      <button
                        type="submit"
                        disabled={isAdding}
                        style={ui.button}
                      >
                        {isAdding ? "Se adaugă..." : "Adaugă album"}
                      </button>
                      <span style={{ opacity: 0.85, fontSize: "0.9em" }}>
                        Exemplu: 12, revolver sau /albums/revolver
                      </span>
                    </form>

                    {Array.isArray(selectedList.albums) &&
                    selectedList.albums.length ? (
                      <ul style={{ paddingLeft: "18px" }}>
                        {selectedList.albums.map((item, idx) => (
                          <li key={item.id} style={{ marginBottom: "10px" }}>
                            <div
                              draggable={canEditList}
                              onDragStart={() => setDraggingItemId(item.id)}
                              onDragEnd={() => setDraggingItemId(null)}
                              onDragOver={(e) => {
                                if (!canEditList) return;
                                e.preventDefault();
                              }}
                              onDrop={() => {
                                if (!draggingItemId) return;
                                const fromId = draggingItemId;
                                const toId = item.id;
                                setDraggingItemId(null);
                                reorderByDrag(fromId, toId);
                              }}
                              style={{
                                ...(draggingItemId === item.id
                                  ? { opacity: 0.6 }
                                  : null),
                              }}
                            >
                              <strong>
                                <Link to={`/albums/${item.album_slug}`}>
                                  {item.album_title}
                                </Link>
                              </strong>
                              <span style={{ opacity: 0.9 }}>
                                {" "}
                                —{" "}
                                <Link to={`/artists/${item.artist_slug}`}>
                                  {item.artist_name}
                                </Link>
                              </span>
                            </div>
                            <div style={{ opacity: 0.85, fontSize: "0.9em" }}>
                              Added: {item.added_at}
                            </div>

                            <div style={{ marginTop: "8px" }}>
                              <textarea
                                rows={2}
                                placeholder="Nota mea (privată)"
                                value={
                                  noteEdits[String(item.id)] ??
                                  item.my_note ??
                                  ""
                                }
                                onChange={(e) => {
                                  const val = e.target.value;
                                  setNoteEdits((prev) => ({
                                    ...prev,
                                    [String(item.id)]: val,
                                  }));
                                }}
                                onBlur={() => saveNote(item.id)}
                                disabled={!canEditList}
                                style={{
                                  width: "100%",
                                  ...ui.input,
                                }}
                              />
                              {savingNoteItemId === item.id ? (
                                <div
                                  style={{ opacity: 0.85, fontSize: "0.9em" }}
                                >
                                  Se salvează nota...
                                </div>
                              ) : null}
                            </div>

                            <div style={{ marginTop: "6px" }}>
                              <button
                                type="button"
                                style={ui.buttonSmall}
                                disabled={
                                  !canEditList || isReordering || idx === 0
                                }
                                onClick={() => handleMoveAlbum(item.id, -1)}
                              >
                                ↑
                              </button>{" "}
                              <button
                                type="button"
                                style={ui.buttonSmall}
                                disabled={
                                  !canEditList ||
                                  isReordering ||
                                  idx === selectedList.albums.length - 1
                                }
                                onClick={() => handleMoveAlbum(item.id, 1)}
                              >
                                ↓
                              </button>{" "}
                              <button
                                type="button"
                                style={ui.button}
                                onClick={() => handleRemoveAlbum(item)}
                                disabled={!canEditList}
                              >
                                Remove
                              </button>
                            </div>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>Lista este goală.</p>
                    )}
                  </>
                ) : null}
              </div>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
