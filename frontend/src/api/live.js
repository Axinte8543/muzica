function normalizeBaseUrl(baseUrl) {
  if (!baseUrl) return "";
  return String(baseUrl).replace(/\/$/, "");
}

function createLiveFeedUrl({
  baseUrl,
  accessToken,
  kind,
  scope,
  limit,
  interval,
}) {
  const normalizedBaseUrl = normalizeBaseUrl(baseUrl);
  const endpoint = `${normalizedBaseUrl}/api/live/stream/`;
  const url = new URL(endpoint, window.location.origin);

  url.searchParams.set("token", accessToken);
  url.searchParams.set("kind", kind);

  if (scope) url.searchParams.set("scope", scope);
  if (typeof limit === "number") url.searchParams.set("limit", String(limit));
  if (typeof interval === "number") {
    url.searchParams.set("interval", String(interval));
  }

  return url.toString();
}

export function buildLiveFeedUrl({
  baseUrl,
  accessToken,
  kind,
  scope,
  limit,
  interval,
}) {
  return createLiveFeedUrl({
    baseUrl,
    accessToken,
    kind,
    scope,
    limit,
    interval,
  });
}

export function subscribeLiveFeed({
  baseUrl,
  accessToken,
  kind,
  scope,
  limit,
  interval,
  onSnapshot,
  onError,
}) {
  const source = new EventSource(
    createLiveFeedUrl({
      baseUrl,
      accessToken,
      kind,
      scope,
      limit,
      interval,
    }),
  );

  source.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data || "{}");
      if (data?.kind !== kind) return;
      onSnapshot?.(data?.payload || [], data);
    } catch (error) {
      console.error(error);
    }
  };

  source.onerror = (error) => {
    onError?.(error);
  };

  return () => source.close();
}
