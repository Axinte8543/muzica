import { apiClient } from "./apiClient.js";

function base64UrlToBuffer(value) {
  if (!value) return new ArrayBuffer(0);
  const base64 = String(value).replace(/-/g, "+").replace(/_/g, "/");
  const pad = base64.length % 4;
  const padded = pad ? `${base64}${"=".repeat(4 - pad)}` : base64;
  const raw = atob(padded);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) {
    bytes[i] = raw.charCodeAt(i);
  }
  return bytes.buffer;
}

function bufferToBase64Url(value) {
  const bytes = new Uint8Array(value || new ArrayBuffer(0));
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

export function normalizePublicKeyOptions(options) {
  const publicKey = options?.publicKey || {};
  return {
    ...options,
    publicKey: {
      ...publicKey,
      challenge: base64UrlToBuffer(publicKey.challenge),
      user: publicKey.user
        ? {
            ...publicKey.user,
            id: base64UrlToBuffer(publicKey.user.id),
          }
        : publicKey.user,
      allowCredentials: Array.isArray(publicKey.allowCredentials)
        ? publicKey.allowCredentials.map((credential) => ({
            ...credential,
            id: base64UrlToBuffer(credential.id),
          }))
        : publicKey.allowCredentials,
      excludeCredentials: Array.isArray(publicKey.excludeCredentials)
        ? publicKey.excludeCredentials.map((credential) => ({
            ...credential,
            id: base64UrlToBuffer(credential.id),
          }))
        : publicKey.excludeCredentials,
    },
  };
}

export function credentialToAttestation(credential) {
  const response = credential?.response || {};
  return {
    id: credential?.id || "",
    rawId: bufferToBase64Url(credential?.rawId || new ArrayBuffer(0)),
    type: credential?.type || "public-key",
    transports:
      typeof response.getTransports === "function"
        ? response.getTransports()
        : [],
    clientDataJSON: bufferToBase64Url(
      response.clientDataJSON || new ArrayBuffer(0),
    ),
    attestationObject: bufferToBase64Url(
      response.attestationObject || new ArrayBuffer(0),
    ),
  };
}

export function credentialToAssertion(credential) {
  const response = credential?.response || {};
  return {
    credentialId: bufferToBase64Url(credential?.rawId || new ArrayBuffer(0)),
    clientDataJSON: bufferToBase64Url(
      response.clientDataJSON || new ArrayBuffer(0),
    ),
    authenticatorData: bufferToBase64Url(
      response.authenticatorData || new ArrayBuffer(0),
    ),
    signature: bufferToBase64Url(response.signature || new ArrayBuffer(0)),
    userHandle: response.userHandle
      ? bufferToBase64Url(response.userHandle)
      : null,
  };
}

export async function getSecuritySessions({ baseUrl } = {}) {
  void baseUrl;
  const response = await apiClient.get(`/api/auth/sessions/`, {
    requiresAuth: true,
  });
  return response.data;
}

export async function revokeSecuritySession({ baseUrl, sessionId } = {}) {
  void baseUrl;
  const response = await apiClient.post(
    `/api/auth/sessions/${sessionId}/revoke/`,
    {},
    { requiresAuth: true },
  );
  return response.data;
}

export async function revokeAllSecuritySessions({ baseUrl } = {}) {
  void baseUrl;
  const response = await apiClient.post(
    `/api/auth/sessions/revoke-all/`,
    {},
    { requiresAuth: true },
  );
  return response.data;
}

export async function getWebAuthnRegisterOptions({ baseUrl } = {}) {
  void baseUrl;
  const response = await apiClient.post(
    `/api/auth/webauthn/register/options/`,
    {},
    { requiresAuth: true },
  );
  return response.data;
}

export async function completeWebAuthnRegistration({
  baseUrl,
  attestation,
} = {}) {
  void baseUrl;
  const response = await apiClient.post(
    `/api/auth/webauthn/register/complete/`,
    { attestation },
    { requiresAuth: true },
  );
  return response.data;
}

export async function getWebAuthnLoginOptions({ baseUrl, username } = {}) {
  void baseUrl;
  const response = await apiClient.post(`/api/auth/webauthn/login/options/`, {
    username,
  });
  return response.data;
}

export async function completeWebAuthnLogin({
  baseUrl,
  username,
  assertion,
} = {}) {
  void baseUrl;
  const response = await apiClient.post(`/api/auth/webauthn/login/complete/`, {
    username,
    assertion,
  });
  return response.data;
}
