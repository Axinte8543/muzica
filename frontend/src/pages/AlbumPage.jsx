import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import RatingWidget from "../components/RatingWidget.jsx";
import ReviewForm from "../components/ReviewForm.jsx";
import ReviewList from "../components/ReviewList.jsx";
import {
  getAlbumComments,
  getAlbumPublicLists,
  getAlbumRecommendations,
} from "../api/albumExtras.js";
import { getAlbumReviews } from "../api/reviews.js";
import { getAlbumListenStatus, markAlbumListened } from "../api/listens.js";
import {
  addAlbumWantToListen,
  getAlbumWantToListenStatus,
  removeAlbumWantToListen,
} from "../api/watchlist.js";
import {
  getAlbumLikeStatus,
  likeAlbum,
  unlikeAlbum,
} from "../api/likedAlbums.js";
import {
  getMyFavoriteSongs,
  setMyFavoriteSongs,
} from "../api/favoriteSongs.js";
import {
  addAlbumToList,
  getMyLists,
  removeAlbumFromList,
} from "../api/lists.js";
import { rateSong } from "../api/ratings.js";
import {
  createMetadataSuggestion,
  createModerationReport,
  getMyModerationReports,
} from "../api/moderation.js";
import { apiClient } from "../api/apiClient.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return "";
  const totalSeconds = Number(seconds);
  if (Number.isNaN(totalSeconds)) return "";

  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

function slotsFromFavoriteSongsResponse(data) {
  const slots = [null, null, null, null];
  const fav = Array.isArray(data?.favorite_songs) ? data.favorite_songs : [];
  fav.forEach((item) => {
    const pos = Number(item?.position);
    if (!Number.isFinite(pos) || pos < 1 || pos > 4) return;
    const songId =
      item?.song_id === null || item?.song_id === undefined
        ? null
        : Number(item.song_id);
    slots[pos - 1] = Number.isFinite(songId) ? songId : null;
  });
  return slots;
}

function formatAverageRating(value) {
  if (value === null || value === undefined) return "";
  const num = Number(value);
  if (Number.isNaN(num)) return "";
  return num.toFixed(1);
}

function formatReportFeedback(meta) {
  if (!meta) return "";
  const reason = String(meta.reason || "").trim();
  const feedback = String(meta.feedback || "").trim();
  const bits = [];
  if (reason) bits.push(`Motiv: ${reason}`);
  if (feedback) bits.push(`Feedback: ${feedback}`);
  return bits.join(" · ");
}

function ReportState({ status, meta }) {
  if (!status) return null;

  const isResolved = String(status).toLowerCase() === "resolved";
  const feedback = formatReportFeedback(meta);

  return (
    <div
      style={{
        marginTop: "8px",
        padding: "10px 12px",
        borderRadius: "10px",
        border: `1px solid ${isResolved ? "rgba(34, 197, 94, 0.35)" : "rgba(245, 158, 11, 0.35)"}`,
        background: isResolved
          ? "rgba(34, 197, 94, 0.08)"
          : "rgba(245, 158, 11, 0.08)",
        fontSize: "0.92rem",
      }}
    >
      <div style={{ fontWeight: 700 }}>
        {isResolved ? "Rezolvat" : "În analiză"}
      </div>
      {isResolved && feedback ? (
        <div style={{ marginTop: "4px" }}>{feedback}</div>
      ) : null}
    </div>
  );
}

export default function AlbumPage({ slug }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { baseUrl, isAuthenticated, isAuthVerified, accessToken, logout } =
    useAuth();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState("overview");

  const effectiveBaseUrl = baseUrl;

  const [reportingCommentIds, setReportingCommentIds] = useState(
    () => new Set(),
  );
  const [reportStatusByKey, setReportStatusByKey] = useState(() => ({}));
  const [reportMetaByKey, setReportMetaByKey] = useState(() => ({}));
  const pickFavoriteSongSlot = useMemo(() => {
    const raw = String(searchParams.get("pickFavoriteSongSlot") || "").trim();
    if (!raw) return null;
    const num = Number.parseInt(raw, 10);
    if (!Number.isFinite(num) || num < 1 || num > 4) return null;
    return num;
  }, [searchParams]);
  const [isPickingFavoriteSong, setIsPickingFavoriteSong] = useState(false);
  const [pickSongError, setPickSongError] = useState(null);

  const [suggestKind, setSuggestKind] = useState(null);
  const [suggestCoverUrl, setSuggestCoverUrl] = useState("");
  const [suggestReleaseDate, setSuggestReleaseDate] = useState("");
  const [suggestDescription, setSuggestDescription] = useState("");
  const [suggestTracklistText, setSuggestTracklistText] = useState("");
  const [isSubmittingSuggestion, setIsSubmittingSuggestion] = useState(false);
  const [suggestionError, setSuggestionError] = useState(null);
  const [suggestionSuccess, setSuggestionSuccess] = useState(null);

  function toggleSuggest(nextKind) {
    setSuggestionError(null);
    setSuggestionSuccess(null);
    setSuggestKind((prev) => (prev === nextKind ? null : nextKind));
  }

  async function handlePickFavoriteSong(song) {
    if (!pickFavoriteSongSlot) return;
    if (!isAuthVerified || !accessToken) {
      setPickSongError("Trebuie să fii logat ca să setezi melodii favorite.");
      return;
    }
    const songId = Number(song?.id);
    if (!Number.isFinite(songId) || songId <= 0) {
      setPickSongError("Melodie invalidă.");
      return;
    }

    setIsPickingFavoriteSong(true);
    setPickSongError(null);
    try {
      const current = await getMyFavoriteSongs({ accessToken });
      const slots = slotsFromFavoriteSongsResponse(current);
      slots[pickFavoriteSongSlot - 1] = songId;
      await setMyFavoriteSongs({ accessToken, slots });
      navigate("/profile/stats");
    } catch (err) {
      console.error(err);
      setPickSongError("Nu am putut seta melodia ca favorită.");
    } finally {
      setIsPickingFavoriteSong(false);
    }
  }

  function parseTracklist(text) {
    const lines = String(text || "")
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter(Boolean);
    const tracks = [];
    for (let i = 0; i < lines.length; i += 1) {
      const raw = lines[i];
      const m = raw.match(/^\s*\d+\s*[.)-]\s*(.+)$/);
      const title = (m ? m[1] : raw).trim();
      if (!title) continue;
      tracks.push({
        title,
        track_number: i + 1,
        duration_seconds: null,
      });
    }
    return tracks;
  }

  async function submitSuggestion() {
    if (!isAuthVerified || !accessToken) return;
    if (!album?.id) return;
    if (!suggestKind) return;

    setIsSubmittingSuggestion(true);
    setSuggestionError(null);
    setSuggestionSuccess(null);

    try {
      let kind = suggestKind;
      let payload = {};

      if (kind === "cover_url") {
        payload = { cover_url: String(suggestCoverUrl || "").trim() };
      } else if (kind === "release_date") {
        payload = { release_date: String(suggestReleaseDate || "").trim() };
      } else if (kind === "description") {
        payload = { description: String(suggestDescription || "").trim() };
      } else if (kind === "tracklist") {
        payload = { tracks: parseTracklist(suggestTracklistText) };
      } else {
        kind = null;
      }

      if (!kind) return;

      await createMetadataSuggestion({
        baseUrl: effectiveBaseUrl,
        targetType: "album",
        targetId: album.id,
        kind,
        payload,
        note: "",
        accessToken,
      });

      setSuggestionSuccess("Sugestia a fost trimisă (pending).");
      setSuggestKind(null);
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
      const httpStatus = err?.response?.status;
      const data = err?.response?.data;
      let details = "";
      if (data) {
        try {
          details =
            typeof data === "string" ? data : JSON.stringify(data, null, 2);
        } catch {
          details = "";
        }
      }
      const msg =
        `Nu am putut trimite sugestia${httpStatus ? ` (HTTP ${httpStatus})` : ""}.` +
        (details ? `\n${details}` : "");
      setSuggestionError(msg.slice(0, 1200));
    } finally {
      setIsSubmittingSuggestion(false);
    }
  }

  async function reportAlbumComment(commentId) {
    if (!isAuthVerified || !accessToken) return;
    if (!commentId) return;
    if (reportingCommentIds.has(commentId)) return;

    setReportingCommentIds((prev) => new Set(prev).add(commentId));
    try {
      const created = await createModerationReport({
        baseUrl: effectiveBaseUrl,
        targetType: "review_comment",
        targetId: commentId,
        reason: "",
        accessToken,
      });
      const st = created?.status;
      if (st) {
        setReportStatusByKey((prev) => ({
          ...prev,
          [`review_comment:${commentId}`]: String(st),
        }));
        setReportMetaByKey((prev) => ({
          ...prev,
          [`review_comment:${commentId}`]: {
            status: String(st),
            reason: String(created?.resolution_reason || "").trim(),
            feedback: String(created?.resolution_feedback || "").trim(),
          },
        }));
      }
    } catch (err) {
      if (err?.response?.status === 401) {
        logout();
        return;
      }
      console.error(err);
    } finally {
      setReportingCommentIds((prev) => {
        const next = new Set(prev);
        next.delete(commentId);
        return next;
      });
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function loadMyReports() {
      if (!isAuthenticated || !accessToken) {
        setReportStatusByKey({});
        setReportMetaByKey({});
        return;
      }

      try {
        const data = await getMyModerationReports({
          baseUrl: effectiveBaseUrl,
          accessToken,
        });
        if (cancelled) return;

        const nextStatus = {};
        const nextMeta = {};
        for (const r of Array.isArray(data) ? data : []) {
          const t = String(r?.target_type || "");
          const id = Number(r?.target_id);
          const st = String(r?.status || "");
          if (!t || !Number.isFinite(id) || id <= 0 || !st) continue;
          nextStatus[`${t}:${id}`] = st;
          nextMeta[`${t}:${id}`] = {
            status: st,
            reason: String(r?.resolution_reason || "").trim(),
            feedback: String(r?.resolution_feedback || "").trim(),
          };
        }
        setReportStatusByKey(nextStatus);
        setReportMetaByKey(nextMeta);
      } catch (err) {
        console.error(err);
      }
    }

    loadMyReports();
    return () => {
      cancelled = true;
    };
  }, [accessToken, effectiveBaseUrl, isAuthenticated]);

  const [isSubmittingListen, setIsSubmittingListen] = useState(false);
  const [listenError, setListenError] = useState(null);

  const [isSubmittingWanted, setIsSubmittingWanted] = useState(false);
  const [wantError, setWantError] = useState(null);

  const [isSubmittingLiked, setIsSubmittingLiked] = useState(false);
  const [likeError, setLikeError] = useState(null);

  const [selectedListId, setSelectedListId] = useState("");
  const [isSubmittingAddToList, setIsSubmittingAddToList] = useState(false);
  const [addToListError, setAddToListError] = useState(null);
  const [addToListSuccess, setAddToListSuccess] = useState(null);
  const [isSubmittingRemoveFromListId, setIsSubmittingRemoveFromListId] =
    useState(null);
  const [removeFromListError, setRemoveFromListError] = useState(null);
  const [removeFromListSuccess, setRemoveFromListSuccess] = useState(null);

  const albumQueryKey = useMemo(() => {
    const authKey = isAuthVerified && accessToken ? accessToken : "anon";
    return ["album", effectiveBaseUrl, slug || "", authKey];
  }, [accessToken, effectiveBaseUrl, isAuthVerified, slug]);

  const albumQuery = useQuery({
    queryKey: albumQueryKey,
    enabled: Boolean(slug),
    queryFn: async () => {
      const response = await apiClient.get(`/api/albums/${slug}/`);
      return response.data;
    },
  });

  const album = albumQuery.data || null;
  const isLoading = albumQuery.isLoading;
  const error = albumQuery.isError ? "Albumul nu a putut fi încărcat." : null;

  const reviewsQueryKey = useMemo(() => {
    return ["albumReviews", effectiveBaseUrl, album?.id || null];
  }, [effectiveBaseUrl, album?.id]);

  const reviewsQuery = useQuery({
    queryKey: reviewsQueryKey,
    enabled: Boolean(album?.id),
    queryFn: async () => {
      const data = await getAlbumReviews({
        baseUrl: effectiveBaseUrl,
        albumId: album.id,
      });
      return Array.isArray(data) ? data : [];
    },
  });

  const reviews = useMemo(() => {
    return Array.isArray(reviewsQuery.data) ? reviewsQuery.data : [];
  }, [reviewsQuery.data]);
  const isLoadingReviews = reviewsQuery.isLoading;
  const reviewsError = reviewsQuery.isError
    ? "Nu am putut încărca review-urile."
    : null;

  useEffect(() => {
    if (!album?.id) return;
    setSuggestCoverUrl(String(album.cover_url || ""));
    setSuggestReleaseDate(String(album.release_date || ""));
    setSuggestDescription(String(album.description || ""));

    const tracks = Array.isArray(album.songs)
      ? [...album.songs]
          .sort((a, b) => (a.track_number ?? 9999) - (b.track_number ?? 9999))
          .map((s, idx) => {
            const n = s.track_number ?? idx + 1;
            const title = String(s.title || "").trim();
            if (!title) return null;
            return `${String(n).padStart(2, "0")}. ${title}`;
          })
          .filter(Boolean)
      : [];

    setSuggestTracklistText(tracks.join("\n"));
  }, [album]);

  const listenStatusQueryKey = useMemo(() => {
    return [
      "albumListenStatus",
      effectiveBaseUrl,
      album?.id || null,
      accessToken || "",
    ];
  }, [accessToken, effectiveBaseUrl, album?.id]);

  const listenStatusQuery = useQuery({
    queryKey: listenStatusQueryKey,
    enabled: Boolean(isAuthVerified && accessToken && album?.id),
    queryFn: async () => {
      const status = await getAlbumListenStatus({
        baseUrl: effectiveBaseUrl,
        albumId: album.id,
        accessToken,
      });
      return status || { listenedToday: false };
    },
  });

  const listenedToday = Boolean(listenStatusQuery.data?.listenedToday);
  const isLoadingListen = listenStatusQuery.isLoading;
  const listenStatusError = listenStatusQuery.isError
    ? "Nu am putut încărca statusul de ascultare."
    : null;

  const myListsQueryKey = useMemo(() => {
    return ["myLists", effectiveBaseUrl, accessToken || "", isAuthVerified];
  }, [accessToken, effectiveBaseUrl, isAuthVerified]);

  const myListsQuery = useQuery({
    queryKey: myListsQueryKey,
    enabled: Boolean(isAuthVerified && accessToken),
    queryFn: async () => {
      const data = await getMyLists({
        baseUrl: effectiveBaseUrl,
        accessToken,
      });
      return Array.isArray(data) ? data : [];
    },
  });

  const myLists = useMemo(() => {
    return Array.isArray(myListsQuery.data) ? myListsQuery.data : [];
  }, [myListsQuery.data]);
  const isLoadingMyLists = myListsQuery.isLoading;
  const myListsError = myListsQuery.isError
    ? "Nu am putut încărca listele tale."
    : null;

  useEffect(() => {
    if (!isAuthVerified || !accessToken) {
      setSelectedListId("");
      return;
    }
    if (!myLists.length) {
      setSelectedListId("");
      return;
    }

    setSelectedListId((prev) => {
      const prevStr = String(prev || "");
      if (prevStr && myLists.some((l) => String(l?.id) === prevStr)) {
        return prevStr;
      }
      const firstId = myLists[0]?.id;
      return firstId !== null && firstId !== undefined ? String(firstId) : "";
    });
  }, [accessToken, isAuthVerified, myLists]);

  async function handleAddAlbumToSelectedList() {
    if (!isAuthVerified || !accessToken) return;
    if (!album?.id) return;

    const listIdInt = Number(selectedListId);
    if (!Number.isFinite(listIdInt) || listIdInt <= 0) return;

    setIsSubmittingAddToList(true);
    setAddToListError(null);
    setAddToListSuccess(null);

    try {
      await addAlbumToList({
        baseUrl: effectiveBaseUrl,
        listId: listIdInt,
        albumId: album.id,
        accessToken,
      });

      const listName = myLists.find((l) => Number(l?.id) === listIdInt)?.name;
      setAddToListSuccess(
        listName ? `Adăugat în lista „${listName}”.` : "Adăugat în listă.",
      );

      queryClient.setQueryData(albumQueryKey, (prev) => {
        if (!prev) return prev;
        const existing = Array.isArray(prev.my_lists) ? prev.my_lists : [];
        if (existing.some((l) => Number(l?.id) === listIdInt)) return prev;

        const toAdd = {
          id: listIdInt,
          name: String(listName || "Lista mea"),
        };

        const existingCount = prev.in_lists_count;
        const nextCount =
          typeof existingCount === "number" ? existingCount + 1 : existingCount;

        return {
          ...prev,
          my_lists: [...existing, toAdd],
          in_lists_count: nextCount,
        };
      });
    } catch (err) {
      console.error(err);
      setAddToListError("Nu am putut adăuga albumul în listă.");
    } finally {
      setIsSubmittingAddToList(false);
    }
  }

  async function handleRemoveAlbumFromList(listId, listName) {
    if (!isAuthVerified || !accessToken) return;
    if (!album?.id) return;

    const listIdInt = Number(listId);
    if (!Number.isFinite(listIdInt) || listIdInt <= 0) return;

    setIsSubmittingRemoveFromListId(listIdInt);
    setRemoveFromListError(null);
    setRemoveFromListSuccess(null);

    try {
      await removeAlbumFromList({
        baseUrl: effectiveBaseUrl,
        listId: listIdInt,
        albumId: album.id,
        accessToken,
      });

      setRemoveFromListSuccess(
        listName ? `Scos din lista „${listName}”.` : "Scos din listă.",
      );

      queryClient.setQueryData(albumQueryKey, (prev) => {
        if (!prev) return prev;
        const existing = Array.isArray(prev.my_lists) ? prev.my_lists : [];
        const nextMyLists = existing.filter((l) => Number(l?.id) !== listIdInt);

        const existingCount = prev.in_lists_count;
        const nextCount =
          typeof existingCount === "number"
            ? Math.max(0, existingCount - 1)
            : existingCount;

        return {
          ...prev,
          my_lists: nextMyLists,
          in_lists_count: nextCount,
        };
      });
    } catch (err) {
      console.error(err);
      setRemoveFromListError("Nu am putut scoate albumul din listă.");
    } finally {
      setIsSubmittingRemoveFromListId(null);
    }
  }

  const likeStatusQueryKey = useMemo(() => {
    return [
      "albumLikeStatus",
      effectiveBaseUrl,
      album?.id || null,
      accessToken || "",
    ];
  }, [accessToken, effectiveBaseUrl, album?.id]);

  const likeStatusQuery = useQuery({
    queryKey: likeStatusQueryKey,
    enabled: Boolean(isAuthVerified && accessToken && album?.id),
    queryFn: async () => {
      const status = await getAlbumLikeStatus({
        baseUrl: effectiveBaseUrl,
        albumId: album.id,
        accessToken,
      });
      return status || { liked: false, likes_count: 0 };
    },
  });

  const isLiked = Boolean(likeStatusQuery.data?.liked);
  const likesCount = Number(likeStatusQuery.data?.likes_count ?? 0) || 0;
  const isLoadingLiked = likeStatusQuery.isLoading;
  const likeStatusError = likeStatusQuery.isError
    ? "Nu am putut încărca statusul de Like."
    : null;

  const wantedStatusQueryKey = useMemo(() => {
    return [
      "albumWantedStatus",
      effectiveBaseUrl,
      album?.id || null,
      accessToken || "",
    ];
  }, [accessToken, effectiveBaseUrl, album?.id]);

  const wantedStatusQuery = useQuery({
    queryKey: wantedStatusQueryKey,
    enabled: Boolean(isAuthVerified && accessToken && album?.id),
    queryFn: async () => {
      const status = await getAlbumWantToListenStatus({
        baseUrl: effectiveBaseUrl,
        albumId: album.id,
        accessToken,
      });
      return status || { wanted: false };
    },
  });

  const isWanted = Boolean(wantedStatusQuery.data?.wanted);
  const isLoadingWanted = wantedStatusQuery.isLoading;
  const wantStatusError = wantedStatusQuery.isError
    ? "Nu am putut încărca statusul Want To Listen."
    : null;

  async function handleMarkListened() {
    if (!isAuthVerified || !accessToken) return;
    if (!album?.id) return;

    setIsSubmittingListen(true);
    setListenError(null);

    try {
      const result = await markAlbumListened({
        baseUrl: effectiveBaseUrl,
        albumId: album.id,
        accessToken,
      });

      queryClient.setQueryData(listenStatusQueryKey, {
        listenedToday: Boolean(result?.listenedToday),
      });
      if (result?.listenedToday) {
        queryClient.setQueryData(wantedStatusQueryKey, { wanted: false });
      }
    } catch (err) {
      console.error(err);
      setListenError("Nu am putut salva ascultarea.");
    } finally {
      setIsSubmittingListen(false);
    }
  }

  async function handleToggleWantToListen() {
    if (!isAuthVerified || !accessToken) return;
    if (!album?.id) return;

    setIsSubmittingWanted(true);
    setWantError(null);

    try {
      if (isWanted) {
        const result = await removeAlbumWantToListen({
          baseUrl: effectiveBaseUrl,
          albumId: album.id,
          accessToken,
        });
        queryClient.setQueryData(wantedStatusQueryKey, {
          wanted: Boolean(result?.wanted),
        });
      } else {
        const result = await addAlbumWantToListen({
          baseUrl: effectiveBaseUrl,
          albumId: album.id,
          accessToken,
        });
        queryClient.setQueryData(wantedStatusQueryKey, {
          wanted: Boolean(result?.wanted),
        });
      }
    } catch (err) {
      console.error(err);
      setWantError("Nu am putut actualiza Want To Listen.");
    } finally {
      setIsSubmittingWanted(false);
    }
  }

  async function handleToggleLike() {
    if (!isAuthVerified || !accessToken) return;
    if (!album?.id) return;

    setIsSubmittingLiked(true);
    setLikeError(null);

    try {
      if (isLiked) {
        const result = await unlikeAlbum({
          baseUrl: effectiveBaseUrl,
          albumId: album.id,
          accessToken,
        });
        queryClient.setQueryData(likeStatusQueryKey, {
          liked: Boolean(result?.liked),
          likes_count: Number(result?.likes_count ?? 0) || 0,
        });
      } else {
        const result = await likeAlbum({
          baseUrl: effectiveBaseUrl,
          albumId: album.id,
          accessToken,
        });
        queryClient.setQueryData(likeStatusQueryKey, {
          liked: Boolean(result?.liked),
          likes_count: Number(result?.likes_count ?? 0) || 0,
        });
      }
    } catch (err) {
      console.error(err);
      setLikeError("Nu am putut actualiza Like.");
    } finally {
      setIsSubmittingLiked(false);
    }
  }

  function handleReviewCreated(created) {
    if (!created) return;
    queryClient.setQueryData(reviewsQueryKey, (prev) => {
      const prevArr = Array.isArray(prev) ? prev : [];
      return [created, ...prevArr];
    });
  }

  const handleChangeReviews = useMemo(() => {
    return (updater) => {
      if (typeof updater !== "function") return;
      queryClient.setQueryData(reviewsQueryKey, (prev) => {
        const prevArr = Array.isArray(prev) ? prev : [];
        const next = updater(prevArr);
        return Array.isArray(next) ? next : prevArr;
      });
    };
  }, [queryClient, reviewsQueryKey]);

  const topLikedReviews = useMemo(() => {
    if (!Array.isArray(reviews)) return [];
    return [...reviews]
      .sort((a, b) => {
        const likeDiff = (b.likes_count ?? 0) - (a.likes_count ?? 0);
        if (likeDiff !== 0) return likeDiff;
        return (
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
      })
      .slice(0, 5);
  }, [reviews]);

  const releaseYear = useMemo(() => {
    if (!album?.release_date) return null;
    const y = Number(String(album.release_date).slice(0, 4));
    return Number.isFinite(y) ? y : null;
  }, [album?.release_date]);

  const recommendationsQueryKey = useMemo(() => {
    return ["albumRecommendations", effectiveBaseUrl, slug || ""];
  }, [effectiveBaseUrl, slug]);

  const recommendationsQuery = useQuery({
    queryKey: recommendationsQueryKey,
    enabled: Boolean(slug),
    queryFn: async () => {
      const data = await getAlbumRecommendations({
        baseUrl: effectiveBaseUrl,
        albumSlug: slug,
        limit: 12,
      });
      return Array.isArray(data) ? data : [];
    },
  });

  const publicListsQueryKey = useMemo(() => {
    const authKey = isAuthVerified && accessToken ? accessToken : "anon";
    return ["albumPublicLists", effectiveBaseUrl, slug || "", authKey];
  }, [accessToken, effectiveBaseUrl, isAuthVerified, slug]);

  const publicListsQuery = useQuery({
    queryKey: publicListsQueryKey,
    enabled: Boolean(slug),
    queryFn: async () => {
      const data = await getAlbumPublicLists({
        baseUrl: effectiveBaseUrl,
        albumSlug: slug,
        limit: 10,
        accessToken: isAuthVerified ? accessToken : undefined,
      });
      return Array.isArray(data) ? data : [];
    },
  });

  const albumCommentsQueryKey = useMemo(() => {
    return ["albumComments", effectiveBaseUrl, slug || ""];
  }, [effectiveBaseUrl, slug]);

  const albumCommentsQuery = useQuery({
    queryKey: albumCommentsQueryKey,
    enabled: Boolean(slug && activeTab === "comments"),
    queryFn: async () => {
      const data = await getAlbumComments({
        baseUrl: effectiveBaseUrl,
        albumSlug: slug,
        limit: 50,
      });
      return Array.isArray(data) ? data : [];
    },
  });

  async function handleRateSong(songId, rating) {
    if (!isAuthVerified || !accessToken) return;
    if (!songId) return;
    if (!album?.id) return;

    const songIdInt = Number(songId);
    if (!Number.isFinite(songIdInt) || songIdInt <= 0) return;
    const ratingInt = Number(rating);
    if (!Number.isFinite(ratingInt) || ratingInt < 1 || ratingInt > 5) return;

    try {
      await rateSong({
        baseUrl: effectiveBaseUrl,
        songId: songIdInt,
        rating: ratingInt,
        accessToken,
      });

      queryClient.setQueryData(albumQueryKey, (prev) => {
        if (!prev) return prev;
        const songs = Array.isArray(prev.songs) ? prev.songs : [];
        const nextSongs = songs.map((s) => {
          if (Number(s?.id) !== songIdInt) return s;
          return {
            ...s,
            my_rating: ratingInt,
          };
        });
        return {
          ...prev,
          songs: nextSongs,
        };
      });
    } catch (err) {
      console.error(err);
    }
  }

  function TabButton({ tabKey, label }) {
    const isActive = activeTab === tabKey;
    return (
      <button
        type="button"
        onClick={() => setActiveTab(tabKey)}
        style={{
          ...ui.buttonSmall,
          background: isActive ? ui.colors.mutedBg : "transparent",
          fontWeight: isActive ? 700 : 400,
        }}
      >
        {label}
      </button>
    );
  }

  function CompactSongRating({ songId, value }) {
    const current = Number(value);
    return (
      <div style={{ display: "flex", gap: "4px", alignItems: "center" }}>
        {[1, 2, 3, 4, 5].map((v) => {
          const filled = Number.isFinite(current) && current >= v;
          return (
            <button
              key={v}
              type="button"
              onClick={() => handleRateSong(songId, v)}
              disabled={!isAuthenticated || !accessToken}
              aria-label={`Rate ${v} stars`}
              style={{
                border: `1px solid ${ui.colors.border}`,
                borderRadius: "6px",
                padding: "2px 6px",
                cursor:
                  !isAuthenticated || !accessToken ? "not-allowed" : "pointer",
                background: filled ? ui.colors.mutedBg : "transparent",
              }}
            >
              ⭐
            </button>
          );
        })}
      </div>
    );
  }

  if (isLoading) {
    const sk = (w, h) => ({
      width: w,
      height: h,
      background: ui.colors.mutedBg,
      border: `1px solid ${ui.colors.border}`,
      borderRadius: "8px",
    });

    return (
      <div style={{ padding: "24px" }}>
        <div style={{ display: "flex", gap: "16px", alignItems: "flex-start" }}>
          <div style={sk("180px", "180px")} />
          <div style={{ flex: 1, display: "grid", gap: "10px" }}>
            <div style={sk("60%", "32px")} />
            <div style={sk("40%", "18px")} />
            <div style={sk("30%", "18px")} />
            <div style={sk("50%", "18px")} />
          </div>
        </div>

        <div style={{ marginTop: "16px", display: "grid", gap: "10px" }}>
          <div style={sk("30%", "20px")} />
          <div style={sk("90%", "18px")} />
          <div style={sk("80%", "18px")} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "24px" }}>
        <p style={{ marginTop: 0, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Link to="/albums">← Înapoi la albume</Link>
          <span style={{ opacity: 0.6 }}>|</span>
          <Link to="/search">Caută</Link>
        </p>
        <p style={ui.errorText}>{error}</p>
      </div>
    );
  }

  if (!album) {
    return (
      <div style={{ padding: "24px" }}>
        <p style={{ marginTop: 0, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Link to="/albums">← Înapoi la albume</Link>
          <span style={{ opacity: 0.6 }}>|</span>
          <Link to="/search">Caută</Link>
        </p>
        <p>Album indisponibil.</p>
      </div>
    );
  }

  const songsSorted = Array.isArray(album.songs)
    ? [...album.songs].sort((a, b) => {
        const aNum = a.track_number ?? Number.POSITIVE_INFINITY;
        const bNum = b.track_number ?? Number.POSITIVE_INFINITY;
        return aNum - bNum;
      })
    : [];

  const commentsCount = Number(album.comments_count ?? 0) || 0;
  const recommendations = Array.isArray(recommendationsQuery.data)
    ? recommendationsQuery.data
    : [];
  const publicLists = Array.isArray(publicListsQuery.data)
    ? publicListsQuery.data
    : [];
  const albumComments = Array.isArray(albumCommentsQuery.data)
    ? albumCommentsQuery.data
    : [];

  return (
    <div style={{ padding: "24px" }}>
      <p style={{ marginTop: 0 }}>
        <Link to="/">← Înapoi la albume</Link>
      </p>

      <div style={{ display: "flex", gap: "16px", alignItems: "flex-start" }}>
        {album.cover_url ? (
          <img
            src={album.cover_url}
            alt={`Coperta albumului ${album.title}`}
            style={{ width: "180px", height: "180px", objectFit: "cover" }}
          />
        ) : null}

        <div>
          <h1 style={{ margin: 0 }}>{album.title}</h1>
          <p style={{ margin: "6px 0" }}>
            {album.artist_slug ? (
              <Link to={`/artists/${album.artist_slug}`}>
                {album.artist_name || album.artist}
              </Link>
            ) : (
              album.artist
            )}
          </p>
          <p style={{ margin: 0 }}>{album.release_date}</p>

          {album.genres?.length ? (
            <p style={{ margin: "12px 0 0" }}>
              Genuri: {album.genres.map((g) => g.name).join(", ")}
            </p>
          ) : null}

          {album.spotify_url ? (
            <p style={{ margin: "8px 0 0" }}>
              Spotify:{" "}
              <a href={album.spotify_url} target="_blank" rel="noreferrer">
                deschide
              </a>
            </p>
          ) : null}

          {album.year_rank ? (
            <p style={{ margin: "8px 0 0", opacity: 0.9 }}>
              {releaseYear ? `Loc în ${releaseYear}: ` : "Loc în an: "}#
              {album.year_rank}
              {album.year_rank_total ? ` / ${album.year_rank_total}` : ""}
            </p>
          ) : null}

          <div style={{ marginTop: "12px" }}>
            {album.average_rating !== null &&
            album.average_rating !== undefined ? (
              <div style={{ fontWeight: 700 }}>
                Average Rating ⭐ {formatAverageRating(album.average_rating)} /
                5
              </div>
            ) : (
              <div style={{ fontWeight: 700 }}>Average Rating ⭐ -</div>
            )}
            <div style={{ opacity: 0.9 }}>
              Votes: {album.ratings_count ?? 0}
            </div>
          </div>
        </div>
      </div>

      {album.description ? <div style={{ marginTop: "16px" }} /> : null}

      <div
        style={{
          marginTop: "16px",
          display: "flex",
          gap: "8px",
          flexWrap: "wrap",
        }}
      >
        <TabButton tabKey="overview" label="Overview" />
        <TabButton
          tabKey="reviews"
          label={`User reviews (${reviews.length})`}
        />
        <TabButton tabKey="lists" label="Lists" />
        <TabButton tabKey="comments" label={`Comments (${commentsCount})`} />
        <TabButton tabKey="discography" label="Discography" />
      </div>

      <div
        style={{
          marginTop: "16px",
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr) 380px",
          gap: "16px",
          alignItems: "start",
        }}
      >
        <div>
          {activeTab === "overview" ? (
            <div style={{ display: "grid", gap: "16px" }}>
              {album.description ? (
                <div style={ui.card}>
                  <div style={{ fontWeight: 700, marginBottom: "8px" }}>
                    Descriere
                  </div>
                  <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>
                    {album.description}
                  </p>
                </div>
              ) : null}

              <div style={ui.card}>
                <div style={{ fontWeight: 700, marginBottom: "8px" }}>
                  Sugerează corecție
                </div>

                {!isAuthenticated ? (
                  <div style={{ opacity: 0.9 }}>
                    <Link to="/login">Login</Link> ca să trimiți o sugestie.
                  </div>
                ) : (
                  <>
                    <div
                      style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}
                    >
                      <button
                        type="button"
                        onClick={() => toggleSuggest("cover_url")}
                        style={ui.buttonSmall}
                      >
                        Cover
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleSuggest("release_date")}
                        style={ui.buttonSmall}
                      >
                        Release date
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleSuggest("tracklist")}
                        style={ui.buttonSmall}
                      >
                        Tracklist
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleSuggest("description")}
                        style={ui.buttonSmall}
                      >
                        Descriere
                      </button>
                    </div>

                    {suggestKind === "cover_url" ? (
                      <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
                        <input
                          value={suggestCoverUrl}
                          onChange={(e) => setSuggestCoverUrl(e.target.value)}
                          placeholder="URL copertă (cover_url)"
                          style={{ ...ui.input, width: "100%" }}
                        />
                        <button
                          type="button"
                          onClick={submitSuggestion}
                          disabled={
                            isSubmittingSuggestion || !suggestCoverUrl.trim()
                          }
                          style={ui.button}
                        >
                          {isSubmittingSuggestion ? "Trimit..." : "Trimite"}
                        </button>
                      </div>
                    ) : null}

                    {suggestKind === "release_date" ? (
                      <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
                        <input
                          type="date"
                          value={suggestReleaseDate}
                          onChange={(e) =>
                            setSuggestReleaseDate(e.target.value)
                          }
                          style={{ ...ui.input, width: "fit-content" }}
                        />
                        <button
                          type="button"
                          onClick={submitSuggestion}
                          disabled={
                            isSubmittingSuggestion || !suggestReleaseDate.trim()
                          }
                          style={ui.button}
                        >
                          {isSubmittingSuggestion ? "Trimit..." : "Trimite"}
                        </button>
                      </div>
                    ) : null}

                    {suggestKind === "description" ? (
                      <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
                        <textarea
                          value={suggestDescription}
                          onChange={(e) =>
                            setSuggestDescription(e.target.value)
                          }
                          placeholder="Propune o descriere corectă..."
                          rows={4}
                          style={{ ...ui.input, width: "100%" }}
                        />
                        <button
                          type="button"
                          onClick={submitSuggestion}
                          disabled={
                            isSubmittingSuggestion || !suggestDescription.trim()
                          }
                          style={ui.button}
                        >
                          {isSubmittingSuggestion ? "Trimit..." : "Trimite"}
                        </button>
                      </div>
                    ) : null}

                    {suggestKind === "tracklist" ? (
                      <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
                        <textarea
                          value={suggestTracklistText}
                          onChange={(e) =>
                            setSuggestTracklistText(e.target.value)
                          }
                          placeholder="Tracklist (un track pe linie)"
                          rows={8}
                          style={{ ...ui.input, width: "100%" }}
                        />
                        <button
                          type="button"
                          onClick={submitSuggestion}
                          disabled={
                            isSubmittingSuggestion ||
                            !parseTracklist(suggestTracklistText).length
                          }
                          style={ui.button}
                        >
                          {isSubmittingSuggestion ? "Trimit..." : "Trimite"}
                        </button>
                      </div>
                    ) : null}
                  </>
                )}

                {suggestionError ? (
                  <div style={{ ...ui.errorText, marginTop: 8 }}>
                    {suggestionError}
                  </div>
                ) : null}
                {suggestionSuccess ? (
                  <div style={{ marginTop: 8, opacity: 0.9 }}>
                    {suggestionSuccess}
                  </div>
                ) : null}
              </div>

              <div style={ui.card}>
                <div style={{ fontWeight: 700, marginBottom: "8px" }}>
                  Rating
                </div>
                {album.id ? (
                  <RatingWidget kind="album" itemId={album.id} />
                ) : null}
              </div>

              <div style={ui.card}>
                <div style={{ fontWeight: 700, marginBottom: "8px" }}>
                  Ascultat
                </div>

                {!isAuthenticated ? (
                  <p
                    style={{ marginTop: 0, marginBottom: "8px", opacity: 0.9 }}
                  >
                    Loghează-te ca să marchezi un album ca ascultat.
                  </p>
                ) : null}

                {isAuthenticated ? (
                  <button
                    type="button"
                    onClick={handleMarkListened}
                    disabled={
                      !album?.id ||
                      listenedToday ||
                      isLoadingListen ||
                      isSubmittingListen
                    }
                    style={ui.button}
                  >
                    {listenedToday ? "Ai ascultat azi" : "Am ascultat"}
                  </button>
                ) : null}

                {isLoadingListen ? (
                  <div style={{ marginTop: "8px", opacity: 0.85 }}>
                    Se încarcă statusul...
                  </div>
                ) : null}

                {isSubmittingListen ? (
                  <div style={{ marginTop: "8px", opacity: 0.85 }}>
                    Se salvează...
                  </div>
                ) : null}

                {listenStatusError ? (
                  <p style={{ ...ui.errorText, marginTop: "8px" }}>
                    {listenStatusError}
                  </p>
                ) : null}

                {listenError ? (
                  <p style={{ ...ui.errorText, marginTop: "8px" }}>
                    {listenError}
                  </p>
                ) : null}
              </div>

              <div style={ui.card}>
                <div style={{ fontWeight: 700, marginBottom: "8px" }}>
                  Want To Listen
                </div>

                {!isAuthenticated ? (
                  <p
                    style={{ marginTop: 0, marginBottom: "8px", opacity: 0.9 }}
                  >
                    Loghează-te ca să adaugi albume în Want To Listen.
                  </p>
                ) : null}

                {isAuthenticated ? (
                  <button
                    type="button"
                    onClick={handleToggleWantToListen}
                    disabled={
                      !album?.id || isLoadingWanted || isSubmittingWanted
                    }
                    style={ui.button}
                  >
                    {isWanted
                      ? "Remove from Want To Listen"
                      : "Add to Want To Listen"}
                  </button>
                ) : null}

                {isLoadingWanted ? (
                  <div style={{ marginTop: "8px", opacity: 0.85 }}>
                    Se încarcă statusul...
                  </div>
                ) : null}

                {isSubmittingWanted ? (
                  <div style={{ marginTop: "8px", opacity: 0.85 }}>
                    Se salvează...
                  </div>
                ) : null}

                {wantStatusError ? (
                  <p style={{ ...ui.errorText, marginTop: "8px" }}>
                    {wantStatusError}
                  </p>
                ) : null}

                {wantError ? (
                  <p style={{ ...ui.errorText, marginTop: "8px" }}>
                    {wantError}
                  </p>
                ) : null}
              </div>

              <div style={ui.card}>
                <div style={{ fontWeight: 700, marginBottom: "8px" }}>Like</div>

                {!isAuthenticated ? (
                  <p
                    style={{ marginTop: 0, marginBottom: "8px", opacity: 0.9 }}
                  >
                    Loghează-te ca să dai Like la albume.
                  </p>
                ) : null}

                {isAuthenticated ? (
                  <button
                    type="button"
                    onClick={handleToggleLike}
                    disabled={!album?.id || isLoadingLiked || isSubmittingLiked}
                    style={ui.button}
                  >
                    {isLiked ? "Unlike" : "Like"}
                  </button>
                ) : null}

                {isAuthenticated && !isLoadingLiked ? (
                  <div style={{ marginTop: "8px", opacity: 0.9 }}>
                    Like-uri: {likesCount}
                  </div>
                ) : null}

                {isLoadingLiked ? (
                  <div style={{ marginTop: "8px", opacity: 0.85 }}>
                    Se încarcă statusul...
                  </div>
                ) : null}

                {isSubmittingLiked ? (
                  <div style={{ marginTop: "8px", opacity: 0.85 }}>
                    Se salvează...
                  </div>
                ) : null}

                {likeStatusError ? (
                  <p style={{ ...ui.errorText, marginTop: "8px" }}>
                    {likeStatusError}
                  </p>
                ) : null}

                {likeError ? (
                  <p style={{ ...ui.errorText, marginTop: "8px" }}>
                    {likeError}
                  </p>
                ) : null}
              </div>
            </div>
          ) : null}

          {activeTab === "reviews" ? (
            <div style={ui.card}>
              <div style={{ fontWeight: 700, marginBottom: "8px" }}>
                Reviews
              </div>
              <ReviewForm albumId={album.id} onCreated={handleReviewCreated} />

              {isLoadingReviews ? (
                <div
                  style={{ display: "grid", gap: "10px", marginTop: "12px" }}
                >
                  <div
                    style={{
                      height: "18px",
                      background: ui.colors.mutedBg,
                      border: `1px solid ${ui.colors.border}`,
                      borderRadius: "6px",
                    }}
                  />
                  <div
                    style={{
                      height: "18px",
                      background: ui.colors.mutedBg,
                      border: `1px solid ${ui.colors.border}`,
                      borderRadius: "6px",
                    }}
                  />
                  <div
                    style={{
                      height: "18px",
                      background: ui.colors.mutedBg,
                      border: `1px solid ${ui.colors.border}`,
                      borderRadius: "6px",
                    }}
                  />
                </div>
              ) : null}
              {reviewsError ? <p style={ui.errorText}>{reviewsError}</p> : null}

              {!isLoadingReviews && !reviewsError ? (
                <div>
                  <div style={{ marginTop: "12px" }}>
                    <div style={{ fontWeight: 700, marginBottom: "8px" }}>
                      Cele mai liked comentarii
                    </div>
                    <ReviewList
                      reviews={topLikedReviews}
                      onChangeReviews={handleChangeReviews}
                    />
                  </div>

                  <div style={{ marginTop: "16px" }}>
                    <div style={{ fontWeight: 700, marginBottom: "8px" }}>
                      Cele mai recente comentarii
                    </div>
                    <ReviewList
                      reviews={reviews}
                      onChangeReviews={handleChangeReviews}
                    />
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}

          {activeTab === "lists" ? (
            <div style={ui.card}>
              <div style={{ fontWeight: 700, marginBottom: "8px" }}>Liste</div>
              <p style={{ marginTop: 0, marginBottom: "8px", opacity: 0.9 }}>
                Albumul apare în {album.in_lists_count ?? 0} liste.
              </p>

              {isAuthenticated ? (
                <div>
                  <div style={{ fontWeight: 700 }}>Adaugă în listă</div>

                  {isLoadingMyLists ? (
                    <div style={{ marginTop: "8px", opacity: 0.85 }}>
                      Se încarcă listele...
                    </div>
                  ) : null}

                  {myListsError ? (
                    <p style={{ ...ui.errorText, marginTop: "8px" }}>
                      {myListsError}
                    </p>
                  ) : null}

                  {!isLoadingMyLists && !myListsError ? (
                    <div
                      style={{ marginTop: "8px", display: "flex", gap: "8px" }}
                    >
                      <select
                        value={selectedListId}
                        onChange={(e) => {
                          setSelectedListId(e.target.value);
                          setAddToListSuccess(null);
                          setAddToListError(null);
                        }}
                        disabled={!myLists.length || isSubmittingAddToList}
                        style={ui.input}
                      >
                        {myLists.length ? (
                          myLists.map((l) => (
                            <option key={l.id} value={String(l.id)}>
                              {l.name}
                            </option>
                          ))
                        ) : (
                          <option value="">Nu ai liste</option>
                        )}
                      </select>

                      <button
                        type="button"
                        onClick={handleAddAlbumToSelectedList}
                        disabled={
                          !album?.id ||
                          !myLists.length ||
                          !selectedListId ||
                          isSubmittingAddToList
                        }
                        style={ui.button}
                      >
                        {isSubmittingAddToList
                          ? "Se adaugă..."
                          : "Adaugă în listă"}
                      </button>
                    </div>
                  ) : null}

                  {addToListSuccess ? (
                    <div style={{ marginTop: "8px", opacity: 0.9 }}>
                      {addToListSuccess}
                    </div>
                  ) : null}

                  {addToListError ? (
                    <p style={{ ...ui.errorText, marginTop: "8px" }}>
                      {addToListError}
                    </p>
                  ) : null}
                </div>
              ) : (
                <p style={{ marginTop: 0, opacity: 0.9 }}>
                  Loghează-te ca să gestionezi liste.
                </p>
              )}

              {isAuthenticated && Array.isArray(album.my_lists) ? (
                <div style={{ marginTop: "12px" }}>
                  <div style={{ fontWeight: 700 }}>
                    Listele mele care îl conțin
                  </div>
                  {album.my_lists.length ? (
                    <ul style={{ paddingLeft: "18px", marginTop: "8px" }}>
                      {album.my_lists.map((l) => (
                        <li
                          key={l.id}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                            marginBottom: "8px",
                          }}
                        >
                          <span>{l.name}</span>
                          <button
                            type="button"
                            onClick={() =>
                              handleRemoveAlbumFromList(l.id, l.name)
                            }
                            disabled={
                              isSubmittingRemoveFromListId !== null ||
                              isSubmittingAddToList
                            }
                            style={ui.buttonSmall}
                          >
                            {Number(isSubmittingRemoveFromListId) ===
                            Number(l.id)
                              ? "Se scoate..."
                              : "Scoate"}
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p style={{ marginTop: "8px", opacity: 0.85 }}>
                      Nu este în nicio listă de-a ta.
                    </p>
                  )}

                  {removeFromListSuccess ? (
                    <div style={{ marginTop: "8px", opacity: 0.9 }}>
                      {removeFromListSuccess}
                    </div>
                  ) : null}

                  {removeFromListError ? (
                    <p style={{ ...ui.errorText, marginTop: "8px" }}>
                      {removeFromListError}
                    </p>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}

          {activeTab === "comments" ? (
            <div style={ui.card}>
              <div style={{ fontWeight: 700, marginBottom: "8px" }}>
                Comments
              </div>

              {albumCommentsQuery.isLoading ? (
                <div style={{ opacity: 0.85 }}>Se încarcă comentariile...</div>
              ) : null}
              {albumCommentsQuery.isError ? (
                <p style={ui.errorText}>Nu am putut încărca comentariile.</p>
              ) : null}

              {!albumCommentsQuery.isLoading && !albumCommentsQuery.isError ? (
                <div style={{ display: "grid", gap: "10px" }}>
                  {albumComments.length ? (
                    albumComments.map((c) => (
                      <div
                        key={c.id}
                        style={{
                          border: `1px solid ${ui.colors.border}`,
                          borderRadius: "8px",
                          padding: "10px",
                        }}
                      >
                        <div style={{ fontWeight: 700 }}>
                          {c.user_username || "User"}
                        </div>
                        <div style={{ opacity: 0.85, fontSize: "0.9em" }}>
                          {c.created_at
                            ? new Date(c.created_at).toLocaleString()
                            : ""}
                        </div>
                        <div
                          style={{ marginTop: "6px", whiteSpace: "pre-wrap" }}
                        >
                          {c.content}
                        </div>

                        {isAuthenticated ? (
                          <div style={{ marginTop: "8px" }}>
                            <button
                              type="button"
                              style={ui.buttonSmall}
                              disabled={
                                reportingCommentIds.has(c.id) ||
                                reportStatusByKey[`review_comment:${c.id}`] ===
                                  "pending"
                              }
                              onClick={() => reportAlbumComment(c.id)}
                            >
                              {reportingCommentIds.has(c.id)
                                ? "Reporting..."
                                : "Report"}
                            </button>
                            <ReportState
                              status={
                                reportStatusByKey[`review_comment:${c.id}`]
                              }
                              meta={reportMetaByKey[`review_comment:${c.id}`]}
                            />
                          </div>
                        ) : null}
                      </div>
                    ))
                  ) : (
                    <div style={{ opacity: 0.85 }}>Nu există comentarii.</div>
                  )}
                </div>
              ) : null}
            </div>
          ) : null}

          {activeTab === "discography" ? (
            <div style={ui.card}>
              <div style={{ fontWeight: 700, marginBottom: "8px" }}>
                Discography
              </div>
              {Array.isArray(album.other_albums_by_artist) &&
              album.other_albums_by_artist.length ? (
                <ul style={{ paddingLeft: "18px", marginTop: 0 }}>
                  {album.other_albums_by_artist.map((a) => (
                    <li key={a.id} style={{ marginBottom: "8px" }}>
                      {a.slug ? (
                        <Link to={`/albums/${a.slug}`}>{a.title}</Link>
                      ) : (
                        a.title
                      )}
                      {a.average_rating !== null &&
                      a.average_rating !== undefined ? (
                        <span>
                          {" "}
                          — ⭐ {formatAverageRating(a.average_rating)}
                          {a.ratings_count ? ` (${a.ratings_count})` : ""}
                        </span>
                      ) : null}
                      {a.release_date ? (
                        <span style={{ opacity: 0.85 }}>
                          {" "}
                          — {a.release_date}
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ opacity: 0.85 }}>
                  Nu există alte albume disponibile.
                </div>
              )}
            </div>
          ) : null}
        </div>

        <div style={{ display: "grid", gap: "16px" }}>
          <div style={ui.card}>
            <div style={{ fontWeight: 700, marginBottom: "8px" }}>
              Tracklist (Rate tracks)
            </div>
            {pickFavoriteSongSlot ? (
              <div style={{ marginBottom: "10px", opacity: 0.85 }}>
                Selectează piesa pentru slotul favorit #{pickFavoriteSongSlot}.
                {pickSongError ? (
                  <div
                    style={{ ...ui.errorText, marginTop: "6px" }}
                    role="alert"
                  >
                    {pickSongError}
                  </div>
                ) : null}
              </div>
            ) : null}
            {songsSorted.length ? (
              <div style={{ display: "grid", gap: "10px" }}>
                {songsSorted.map((song) => (
                  <div
                    key={song.id}
                    style={{
                      border: `1px solid ${ui.colors.border}`,
                      borderRadius: "8px",
                      padding: "10px",
                      display: "grid",
                      gap: "6px",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        gap: "8px",
                        alignItems: "baseline",
                      }}
                    >
                      <span style={{ opacity: 0.85 }}>
                        {song.track_number
                          ? String(song.track_number).padStart(2, "0")
                          : "–"}
                      </span>
                      <div style={{ flex: 1 }}>
                        <strong>
                          {song.slug ? (
                            <Link to={`/songs/${song.slug}`}>{song.title}</Link>
                          ) : (
                            song.title
                          )}
                        </strong>
                        {song.duration_seconds ? (
                          <span style={{ opacity: 0.85 }}>
                            {" "}
                            — {formatDuration(song.duration_seconds)}
                          </span>
                        ) : null}
                      </div>
                    </div>

                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: "10px",
                      }}
                    >
                      <div style={{ opacity: 0.9, fontSize: "0.9em" }}>
                        {song.average_rating !== null &&
                        song.average_rating !== undefined
                          ? `⭐ ${formatAverageRating(song.average_rating)}${song.ratings_count ? ` (${song.ratings_count})` : ""}`
                          : "⭐ -"}
                      </div>
                      <CompactSongRating
                        songId={song.id}
                        value={song.my_rating}
                      />
                    </div>

                    {pickFavoriteSongSlot ? (
                      <div>
                        <button
                          type="button"
                          style={ui.buttonSmall}
                          disabled={isPickingFavoriteSong}
                          onClick={() => handlePickFavoriteSong(song)}
                        >
                          Setează ca melodie favorită #{pickFavoriteSongSlot}
                        </button>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ margin: 0, opacity: 0.85 }}>Nu există piese.</p>
            )}

            {!isAuthenticated ? (
              <div style={{ marginTop: "8px", opacity: 0.85 }}>
                Loghează-te ca să ratezi piese.
              </div>
            ) : null}
          </div>

          <div style={ui.card}>
            <div style={{ fontWeight: 700, marginBottom: "8px" }}>
              You may also like
            </div>
            {recommendationsQuery.isLoading ? (
              <div style={{ opacity: 0.85 }}>Se încarcă recomandările...</div>
            ) : null}
            {recommendationsQuery.isError ? (
              <div style={ui.errorText}>Nu am putut încărca recomandările.</div>
            ) : null}
            {!recommendationsQuery.isLoading &&
            !recommendationsQuery.isError ? (
              recommendations.length ? (
                <div
                  style={{
                    display: "flex",
                    gap: "10px",
                    overflowX: "auto",
                    paddingBottom: "6px",
                  }}
                >
                  {recommendations.map((a) => (
                    <Link
                      key={a.id}
                      to={a.slug ? `/albums/${a.slug}` : "#"}
                      style={{
                        ...ui.card,
                        minWidth: "180px",
                        textDecoration: "none",
                        color: "inherit",
                      }}
                    >
                      {a.cover_url ? (
                        <img
                          src={a.cover_url}
                          alt={a.title}
                          style={{
                            width: "100%",
                            height: "120px",
                            objectFit: "cover",
                            borderRadius: "8px",
                          }}
                        />
                      ) : null}
                      <div style={{ marginTop: "8px", fontWeight: 700 }}>
                        {a.title}
                      </div>
                      <div style={{ opacity: 0.9, fontSize: "0.9em" }}>
                        {a.artist_name || ""}
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div style={{ opacity: 0.85 }}>
                  Nu avem recomandări pentru acest album.
                </div>
              )
            ) : null}
          </div>

          <div style={ui.card}>
            <div style={{ fontWeight: 700, marginBottom: "8px" }}>
              User lists
            </div>
            {publicListsQuery.isLoading ? (
              <div style={{ opacity: 0.85 }}>Se încarcă listele...</div>
            ) : null}
            {publicListsQuery.isError ? (
              <div style={ui.errorText}>Nu am putut încărca listele.</div>
            ) : null}
            {!publicListsQuery.isLoading && !publicListsQuery.isError ? (
              publicLists.length ? (
                <div style={{ display: "grid", gap: "8px" }}>
                  {publicLists.map((l) => (
                    <div
                      key={l.id}
                      style={{
                        border: `1px solid ${ui.colors.border}`,
                        borderRadius: "8px",
                        padding: "10px",
                      }}
                    >
                      <div style={{ fontWeight: 700 }}>
                        <Link to={`/lists/public/${l.id}`}>{l.name}</Link>
                      </div>
                      <div style={{ opacity: 0.9, fontSize: "0.9em" }}>
                        @{l.user_username} • ❤️ {l.likes_count} • Albume:{" "}
                        {l.albums_count}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ opacity: 0.85 }}>Nu apare în liste publice.</div>
              )
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
