import { apiClient } from "./apiClient.js";

export const AUTH_STORAGE_KEYS = {
  accessToken: "accessToken",
  refreshToken: "refreshToken",
};

function base64UrlDecode(value) {
  if (!value) return "";
  const base64 = String(value).replace(/-/g, "+").replace(/_/g, "/");
  const pad = base64.length % 4;
  const padded = pad ? base64 + "=".repeat(4 - pad) : base64;

  try {
    return atob(padded);
  } catch {
    return "";
  }
}

function decodeJwtPayload(token) {
  const raw = String(token || "");
  const parts = raw.split(".");
  if (parts.length < 2) return null;

  const json = base64UrlDecode(parts[1]);
  if (!json) return null;

  try {
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function isJwtExpired(token, skewSeconds = 30) {
  const payload = decodeJwtPayload(token);
  const exp = payload?.exp;
  if (!exp) return false;
  const expSeconds = Number(exp);
  if (!Number.isFinite(expSeconds)) return false;
  const nowSeconds = Math.floor(Date.now() / 1000);
  return nowSeconds >= expSeconds - skewSeconds;
}

export async function registerUser({ baseUrl, username, email, password }) {
  // baseUrl kept for backwards compatibility; apiClient is configured in AuthProvider.
  void baseUrl;
  const response = await apiClient.post(`/api/auth/register/`, {
    username,
    email,
    password,
  });
  return response.data;
}

export async function resendVerification({ baseUrl, email }) {
  void baseUrl;
  const response = await apiClient.post(`/api/auth/verify-email/resend/`, {
    email,
  });
  return response.data;
}

export async function verifyEmail({ baseUrl, token }) {
  void baseUrl;
  const response = await apiClient.post(`/api/auth/verify-email/`, {
    token,
  });
  return response.data;
}

export async function loginUser({ baseUrl, username, password }) {
  void baseUrl;
  const response = await apiClient.post(`/api/auth/login/`, {
    username,
    password,
  });
  return response.data;
}

export async function refreshToken({ baseUrl, refresh }) {
  void baseUrl;
  const response = await apiClient.post(`/api/auth/refresh/`, { refresh });
  return response.data;
}

export async function getCurrentUser({ baseUrl } = {}) {
  void baseUrl;
  // This is the one call that must attach Authorization even before isAuthVerified
  const response = await apiClient.get(`/api/auth/me/`, { requiresAuth: true });
  return response.data;
}

export async function requestEmailChange({ baseUrl, newEmail, password } = {}) {
  void baseUrl;
  const response = await apiClient.post(
    `/api/auth/email-change/request/`,
    { new_email: newEmail, password },
    { requiresAuth: true },
  );
  return response.data;
}

export async function confirmEmailChange({ baseUrl, token } = {}) {
  void baseUrl;
  const response = await apiClient.post(`/api/auth/email-change/confirm/`, {
    token,
  });
  return response.data;
}

export async function requestPasswordReset({ baseUrl, email } = {}) {
  void baseUrl;
  const response = await apiClient.post(`/api/auth/password-reset/`, {
    email,
  });
  return response.data;
}

export async function confirmPasswordReset({ baseUrl, token, password } = {}) {
  void baseUrl;
  const response = await apiClient.post(`/api/auth/password-reset/confirm/`, {
    token,
    password,
  });
  return response.data;
}

export async function changePassword({
  baseUrl,
  currentPassword,
  newPassword,
  totpCode,
} = {}) {
  void baseUrl;
  const response = await apiClient.post(
    `/api/auth/password/change/`,
    {
      current_password: currentPassword,
      new_password: newPassword,
      totp_code: totpCode,
    },
    { requiresAuth: true },
  );
  return response.data;
}

export function persistTokens({ access, refresh }) {
  if (access) {
    localStorage.setItem(AUTH_STORAGE_KEYS.accessToken, access);
  }
  if (refresh) {
    localStorage.setItem(AUTH_STORAGE_KEYS.refreshToken, refresh);
  }
}

export function getStoredTokens() {
  const access = localStorage.getItem(AUTH_STORAGE_KEYS.accessToken);
  const refresh = localStorage.getItem(AUTH_STORAGE_KEYS.refreshToken);

  const normalizedAccess =
    access && access !== "null" && access !== "undefined" ? access : null;
  const normalizedRefresh =
    refresh && refresh !== "null" && refresh !== "undefined" ? refresh : null;

  if (normalizedAccess && isJwtExpired(normalizedAccess)) {
    localStorage.removeItem(AUTH_STORAGE_KEYS.accessToken);
    return {
      access: null,
      refresh: normalizedRefresh,
    };
  }

  return {
    access: normalizedAccess,
    refresh: normalizedRefresh,
  };
}

export function clearStoredTokens() {
  localStorage.removeItem(AUTH_STORAGE_KEYS.accessToken);
  localStorage.removeItem(AUTH_STORAGE_KEYS.refreshToken);
}
