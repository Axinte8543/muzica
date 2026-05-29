import { useCallback, useEffect, useMemo, useState } from "react";

import {
  clearStoredTokens,
  getCurrentUser,
  getStoredTokens,
  persistTokens,
} from "../api/auth.js";
import {
  configureApiClient,
  SESSION_EXPIRED_MESSAGE,
} from "../api/apiClient.js";
import { AuthContext } from "./AuthContext.js";
import { useNotice } from "./useNotice.js";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export function AuthProvider({ children }) {
  const baseUrl = useMemo(() => {
    return import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL;
  }, []);

  const { notify, dismiss } = useNotice();

  const [{ access, refresh }, setTokens] = useState(() => getStoredTokens());
  const [user, setUser] = useState(null);
  const [isLoadingUser, setIsLoadingUser] = useState(false);

  const hasToken = Boolean(access);
  const isAuthenticated = Boolean(access);
  const isAuthVerified = Boolean(access && user);

  const login = useCallback(
    ({ access: nextAccess, refresh: nextRefresh }) => {
      persistTokens({ access: nextAccess, refresh: nextRefresh });
      setTokens({ access: nextAccess || null, refresh: nextRefresh || null });

      // Successful login clears any previous session-expired notice.
      dismiss({ scope: "auth" });
    },
    [dismiss],
  );

  const logout = useCallback(
    (options) => {
      const reason = options?.reason || null;
      const message = options?.message || null;

      clearStoredTokens();
      setTokens({ access: null, refresh: null });
      setUser(null);

      if (reason === "session_expired") {
        const nextMessage = message || SESSION_EXPIRED_MESSAGE;
        notify({ type: "error", message: nextMessage, scope: "auth" });
        return;
      }

      // Manual/other logout clears auth-related notices.
      dismiss({ scope: "auth" });
    },
    [dismiss, notify],
  );

  useEffect(() => {
    configureApiClient({
      baseUrl,
      getAccessToken: () => access,
      getRefreshToken: () => refresh,
      getIsAuthVerified: () => Boolean(access && user),
      onTokens: ({ access: nextAccess, refresh: nextRefresh }) => {
        persistTokens({ access: nextAccess, refresh: nextRefresh });
        setTokens({
          access: nextAccess || null,
          refresh: nextRefresh || null,
        });
      },
      onLogout: logout,
    });
  }, [baseUrl, access, refresh, user, logout]);

  useEffect(() => {
    let isCancelled = false;

    async function loadMe() {
      if (!access && !refresh) {
        if (!isCancelled) setUser(null);
        return;
      }

      if (!isCancelled) setIsLoadingUser(true);

      try {
        const me = await getCurrentUser();
        if (!isCancelled) setUser(me);
      } catch (err) {
        const status = err?.response?.status;
        if (status && status !== 401) {
          console.error(err);
        }
        if (isCancelled) return;
        if (status === 401) {
          logout({
            reason: "session_expired",
            message: SESSION_EXPIRED_MESSAGE,
          });
          return;
        }
        logout();
      } finally {
        if (!isCancelled) setIsLoadingUser(false);
      }
    }

    loadMe();

    return () => {
      isCancelled = true;
    };
  }, [access, refresh, logout]);

  const value = useMemo(() => {
    return {
      baseUrl,
      accessToken: access,
      refreshToken: refresh,
      hasToken,
      isAuthenticated,
      isAuthVerified,
      user,
      isLoadingUser,
      login,
      logout,
    };
  }, [
    baseUrl,
    access,
    refresh,
    hasToken,
    isAuthenticated,
    isAuthVerified,
    user,
    isLoadingUser,
    login,
    logout,
  ]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
