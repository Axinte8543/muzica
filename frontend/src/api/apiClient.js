import axios from "axios";

export const SESSION_EXPIRED_MESSAGE =
  "Sesiunea a expirat, te rugăm să te loghezi din nou.";

function normalizeBaseUrl(baseUrl) {
  if (!baseUrl) return "";
  return String(baseUrl).replace(/\/$/, "");
}

// Mutable runtime wiring (configured from AuthProvider)
let configuredBaseUrl = "";
let getAccessToken = () => null;
let getRefreshToken = () => null;
let getIsAuthVerified = () => false;
let onTokens = null; // ({ access, refresh }) => void
let onLogout = null; // ({ reason, message }) => void

/**
 * Configure the shared API client.
 * Call this from the auth layer (AuthProvider) so the client can:
 * - attach Authorization headers only when auth is verified
 * - refresh access token once on 401
 */
export function configureApiClient({
  baseUrl,
  getAccessToken: getAccess,
  getRefreshToken: getRefresh,
  getIsAuthVerified: getVerified,
  onTokens: onTokensUpdate,
  onLogout: onLogoutCb,
}) {
  configuredBaseUrl = normalizeBaseUrl(baseUrl);
  apiClient.defaults.baseURL = configuredBaseUrl;

  // New wiring means a new auth session; allow future auth-failure notifications.
  logoutNotified = false;

  if (typeof getAccess === "function") getAccessToken = getAccess;
  if (typeof getRefresh === "function") getRefreshToken = getRefresh;
  if (typeof getVerified === "function") getIsAuthVerified = getVerified;

  onTokens = typeof onTokensUpdate === "function" ? onTokensUpdate : null;
  onLogout = typeof onLogoutCb === "function" ? onLogoutCb : null;
}

/**
 * Optional request flag:
 * - requiresAuth: attach Authorization even if isAuthVerified is false.
 *   Useful for the initial /auth/me verification call.
 */
export const apiClient = axios.create({
  baseURL: configuredBaseUrl,
});

let refreshPromise = null;
let logoutNotified = false;

function notifySessionExpiredOnce() {
  if (logoutNotified) return;
  logoutNotified = true;
  onLogout?.({ reason: "session_expired", message: SESSION_EXPIRED_MESSAGE });
}

async function refreshAccessToken() {
  const refresh = getRefreshToken?.();
  if (!refresh) return null;

  if (refreshPromise) return refreshPromise;

  const baseURL = apiClient.defaults.baseURL || configuredBaseUrl;

  refreshPromise = axios
    .post(`${normalizeBaseUrl(baseURL)}/api/auth/refresh/`, { refresh })
    .then((res) => {
      const data = res?.data || {};
      const nextAccess = data?.access || null;
      if (!nextAccess) return null;

      logoutNotified = false;

      // Keep current refresh unless server returned a rotated one.
      const rotatedRefresh = data?.refresh || null;
      const nextTokens = {
        access: nextAccess,
        refresh: rotatedRefresh || refresh,
      };

      onTokens?.(nextTokens);
      return nextTokens;
    })
    .catch(() => null)
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

apiClient.interceptors.request.use(
  (config) => {
    const cfg = config || {};

    // Allow callers to explicitly opt-out.
    if (cfg.headers?.Authorization) return cfg;

    const access = getAccessToken?.();
    if (!access) return cfg;

    const verified = Boolean(getIsAuthVerified?.());
    const requiresAuth = Boolean(cfg.requiresAuth);

    // Key rule to prevent 401 spam on public endpoints:
    // attach token ONLY if auth was verified (or the request explicitly requires auth).
    if (!verified && !requiresAuth) return cfg;

    cfg.headers = {
      ...(cfg.headers || {}),
      Authorization: `Bearer ${access}`,
    };

    return cfg;
  },
  (error) => Promise.reject(error),
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status;
    const originalConfig = error?.config;

    if (!originalConfig || status !== 401) {
      return Promise.reject(error);
    }

    // Allow callers to explicitly opt-out of the refresh flow.
    if (originalConfig.skipAuthRefresh) {
      return Promise.reject(error);
    }

    // Never try to refresh on auth endpoints themselves.
    // (E.g., invalid credentials on login should not trigger token refresh.)
    const url = String(originalConfig.url || "");
    const isAuthEndpoint =
      url.includes("/api/auth/login/") ||
      url.includes("/api/auth/register/") ||
      url.includes("/api/auth/refresh/");
    if (isAuthEndpoint) {
      return Promise.reject(error);
    }

    // Avoid infinite loops.
    if (originalConfig._retry) {
      notifySessionExpiredOnce();
      return Promise.reject(error);
    }

    // If we have no refresh token, just logout.
    if (!getRefreshToken?.()) {
      notifySessionExpiredOnce();
      return Promise.reject(error);
    }

    originalConfig._retry = true;

    const nextTokens = await refreshAccessToken();
    if (!nextTokens?.access) {
      notifySessionExpiredOnce();
      return Promise.reject(error);
    }

    originalConfig.headers = {
      ...(originalConfig.headers || {}),
      Authorization: `Bearer ${nextTokens.access}`,
    };

    try {
      return await apiClient.request(originalConfig);
    } catch (err) {
      return Promise.reject(err);
    }
  },
);
