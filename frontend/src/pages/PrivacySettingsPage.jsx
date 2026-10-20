import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  completeWebAuthnRegistration,
  credentialToAttestation,
  getSecuritySessions,
  getWebAuthnRegisterOptions,
  normalizePublicKeyOptions,
  revokeAllSecuritySessions,
  revokeSecuritySession,
} from "../api/security.js";
import { changePassword, requestEmailChange } from "../api/auth.js";
import {
  getMyPrivacySettings,
  updateMyPrivacySettings,
} from "../api/privacy.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

/**
 * Privacy control descriptions and details
 */
const PRIVACY_CONTROLS = {
  public_lists: {
    label: "Liste publice",
    description: "Permite utilizatorilor să-ți vadă listele și să le comenteze",
    details: [
      "Alții vor putea vedea listele tale pe profilul public",
      "Alții vor putea vedea și comenta albumele din listele tale",
      "Listele vor apărea în sugestiile de conținut",
    ],
  },
  public_activity: {
    label: "Activitate publică",
    description: "Permite publicării activității tale în feed și pe profil",
    details: [
      "Ratingurile și review-urile tale vor apărea în feed",
      "Activitatea va fi vizibilă pe profilul tău public",
      "Prietenii vor putea vedea ce ascultai și ce ai notat",
    ],
  },
  public_compatibility: {
    label: "Compatibilitate publică",
    description:
      "Permite calcularea scorului de compatibilitate cu alți utilizatori",
    details: [
      "Sistemul va calcula compatibilitatea gustului tău cu al altor utilizatori",
      "Vei apărea în lista utilizatorilor similari pe alte profiluri",
      "Te vor putea descoperi alți utilizatori cu gust muzical similar",
    ],
  },
};

export default function PrivacySettingsPage() {
  const { baseUrl, isAuthVerified, accessToken, logout, user, isLoadingUser } =
    useAuth();
  const navigate = useNavigate();

  const [settings, setSettings] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState(null);
  const [sessionsActionError, setSessionsActionError] = useState(null);
  const [sessionsActionSuccess, setSessionsActionSuccess] = useState(null);
  const [passkeyBusy, setPasskeyBusy] = useState(false);
  const [passkeyError, setPasskeyError] = useState(null);
  const [passkeySuccess, setPasskeySuccess] = useState(null);
  // Email change state
  const [newEmailValue, setNewEmailValue] = useState("");
  const [emailChangeLoading, setEmailChangeLoading] = useState(false);
  const [emailChangeMessage, setEmailChangeMessage] = useState(null);
  const [emailChangeError, setEmailChangeError] = useState(null);
  // Password change state
  const [currentPasswordValue, setCurrentPasswordValue] = useState("");
  const [newPasswordValue, setNewPasswordValue] = useState("");
  const [passwordChangeLoading, setPasswordChangeLoading] = useState(false);
  const [passwordChangeMessage, setPasswordChangeMessage] = useState(null);
  const [passwordChangeError, setPasswordChangeError] = useState(null);

  const [formData, setFormData] = useState({
    public_lists: true,
    public_activity: true,
    public_compatibility: true,
  });

  const [unsavedChanges, setUnsavedChanges] = useState(false);
  const [expandedControl, setExpandedControl] = useState(null);

  function RelativeTime({ value }) {
    const [text, setText] = useState(() => (value ? String(value) : "-"));
    const [title, setTitle] = useState("");

    useEffect(() => {
      let mounted = true;

      function update() {
        if (!mounted) return;
        if (!value) {
          setText("-");
          setTitle("");
          return;
        }
        try {
          const d = new Date(value);
          if (Number.isNaN(d.getTime())) {
            setText(String(value));
            setTitle("");
            return;
          }
          const diffMs = Date.now() - d.getTime();
          const seconds = Math.round(diffMs / 1000);
          const rtf = new Intl.RelativeTimeFormat("ro", { numeric: "auto" });
          if (seconds < 60) setText(rtf.format(-seconds, "second"));
          else {
            const minutes = Math.round(seconds / 60);
            if (minutes < 60) setText(rtf.format(-minutes, "minute"));
            else {
              const hours = Math.round(minutes / 60);
              if (hours < 24) setText(rtf.format(-hours, "hour"));
              else {
                const days = Math.round(hours / 24);
                if (days <= 7) setText(rtf.format(-days, "day"));
                else {
                  try {
                    setText(
                      new Intl.DateTimeFormat("ro-RO", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      }).format(d),
                    );
                  } catch {
                    setText(d.toLocaleString());
                  }
                }
              }
            }
          }
          try {
            setTitle(
              new Intl.DateTimeFormat("ro-RO", {
                dateStyle: "medium",
                timeStyle: "short",
              }).format(d),
            );
          } catch {
            setTitle(d.toLocaleString());
          }
        } catch {
          setText(String(value));
          setTitle("");
        }
      }

      update();
      const id = setInterval(update, 60 * 1000);
      return () => {
        clearInterval(id);
        mounted = false;
      };
    }, [value]);

    return (
      <time dateTime={value || ""} title={title}>
        {text}
      </time>
    );
  }

  const canLoad = useMemo(() => {
    return Boolean(isAuthVerified && accessToken);
  }, [isAuthVerified, accessToken]);

  useEffect(() => {
    let isCancelled = false;

    async function loadSessions() {
      if (!canLoad) {
        setSessions([]);
        setSessionsLoading(false);
        setSessionsError(null);
        return;
      }

      setSessionsLoading(true);
      setSessionsError(null);

      try {
        const data = await getSecuritySessions({ baseUrl });
        if (!isCancelled) {
          setSessions(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        const status = err?.response?.status;
        if (status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled) {
          setSessionsError("Nu am putut încărca sesiunile active.");
        }
      } finally {
        if (!isCancelled) setSessionsLoading(false);
      }
    }

    void loadSessions();

    return () => {
      isCancelled = true;
    };
  }, [baseUrl, canLoad, logout]);

  // Load privacy settings
  useEffect(() => {
    let isCancelled = false;

    async function loadSettings() {
      if (!canLoad) {
        setSettings(null);
        return;
      }
      setIsLoading(true);
      setError(null);

      try {
        const data = await getMyPrivacySettings({ baseUrl, accessToken });
        if (!isCancelled) {
          setSettings(data && typeof data === "object" ? data : null);
          setFormData({
            public_lists: Boolean(data?.public_lists ?? true),
            public_activity: Boolean(data?.public_activity ?? true),
            public_compatibility: Boolean(data?.public_compatibility ?? true),
          });
          setUnsavedChanges(false);
        }
      } catch (err) {
        const status = err?.response?.status;
        if (status === 401) {
          logout();
          return;
        }
        console.error(err);
        if (!isCancelled)
          setError("Nu am putut încărca setările de confidențialitate.");
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    void loadSettings();

    return () => {
      isCancelled = true;
    };
  }, [canLoad, baseUrl, accessToken, logout]);

  // Handle checkbox changes
  function handleToggle(key) {
    setFormData((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
    setUnsavedChanges(true);
    setSaveSuccess(null);
  }

  // Save settings
  async function handleSave() {
    if (!canLoad || isSaving || !unsavedChanges) return;

    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(null);

    try {
      const data = await updateMyPrivacySettings({
        baseUrl,
        accessToken,
        publicLists: formData.public_lists,
        publicActivity: formData.public_activity,
        publicCompatibility: formData.public_compatibility,
      });

      setSettings(data && typeof data === "object" ? data : null);
      setUnsavedChanges(false);
      setSaveSuccess("Setările au fost salvate cu succes.");

      // Clear success message after 3 seconds
      setTimeout(() => setSaveSuccess(null), 3000);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        logout();
        return;
      }
      console.error(err);
      setSaveError("Nu am putut salva setările. Încearcă din nou.");
    } finally {
      setIsSaving(false);
    }
  }

  // Reset to saved settings
  function handleReset() {
    if (!settings) return;
    setFormData({
      public_lists: Boolean(settings?.public_lists ?? true),
      public_activity: Boolean(settings?.public_activity ?? true),
      public_compatibility: Boolean(settings?.public_compatibility ?? true),
    });
    setUnsavedChanges(false);
    setSaveError(null);
    setSaveSuccess(null);
  }

  async function handleRevokeSession(sessionId) {
    setSessionsActionError(null);
    setSessionsActionSuccess(null);

    try {
      await revokeSecuritySession({ baseUrl, sessionId });
      setSessions((prev) => prev.filter((session) => session.id !== sessionId));
      setSessionsActionSuccess("Sesiunea a fost revocată.");
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        logout();
        return;
      }
      console.error(err);
      setSessionsActionError("Nu am putut revoca sesiunea.");
    }
  }

  async function handleRevokeAllSessions() {
    setSessionsActionError(null);
    setSessionsActionSuccess(null);

    try {
      await revokeAllSecuritySessions({ baseUrl });
      setSessions([]);
      setSessionsActionSuccess("Toate sesiunile au fost revocate.");
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        logout();
        return;
      }
      console.error(err);
      setSessionsActionError("Nu am putut revoca toate sesiunile.");
    }
  }

  async function handleRequestEmailChange() {
    if (!newEmailValue || !currentPasswordValue) {
      setEmailChangeError("Completează noul email și parola curentă.");
      return;
    }
    setEmailChangeLoading(true);
    setEmailChangeError(null);
    setEmailChangeMessage(null);
    try {
      await requestEmailChange({
        baseUrl,
        newEmail: newEmailValue,
        password: currentPasswordValue,
      });
      setEmailChangeMessage(
        "A fost trimis un email către adresa nouă; urmează instrucțiunile pentru confirmare.",
      );
      setNewEmailValue("");
      setCurrentPasswordValue("");
    } catch (err) {
      console.error(err);
      const msg =
        err?.response?.data?.detail || "Eroare la cererea schimbării de email.";
      setEmailChangeError(msg);
    } finally {
      setEmailChangeLoading(false);
    }
  }

  async function handleChangePassword() {
    if (!currentPasswordValue || !newPasswordValue) {
      setPasswordChangeError("Completează parola curentă și noua parolă.");
      return;
    }
    setPasswordChangeLoading(true);
    setPasswordChangeError(null);
    setPasswordChangeMessage(null);
    try {
      await changePassword({
        baseUrl,
        currentPassword: currentPasswordValue,
        newPassword: newPasswordValue,
      });
      setPasswordChangeMessage("Parola a fost schimbată cu succes.");
      setCurrentPasswordValue("");
      setNewPasswordValue("");
    } catch (err) {
      console.error(err);
      const msg =
        err?.response?.data?.detail || "Eroare la schimbarea parolei.";
      setPasswordChangeError(msg);
    } finally {
      setPasswordChangeLoading(false);
    }
  }

  async function handleRegisterPasskey() {
    if (!window.PublicKeyCredential) {
      setPasskeyError("Browserul tău nu suportă WebAuthn.");
      return;
    }

    setPasskeyBusy(true);
    setPasskeyError(null);
    setPasskeySuccess(null);

    try {
      const options = await getWebAuthnRegisterOptions({ baseUrl });
      const credential = await navigator.credentials.create(
        normalizePublicKeyOptions(options),
      );
      if (!credential) {
        setPasskeyError("Înregistrarea passkey a fost anulată.");
        return;
      }

      await completeWebAuthnRegistration({
        baseUrl,
        attestation: credentialToAttestation(credential),
      });

      setPasskeySuccess("Passkey înregistrat cu succes.");
    } catch (err) {
      console.error("WebAuthn registration error", err);
      const serverDetail =
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        err?.message;
      setPasskeyError(
        serverDetail
          ? `Nu am putut înregistra passkey-ul: ${serverDetail}`
          : "Nu am putut înregistra passkey-ul.",
      );
      const status = err?.response?.status;
      if (status === 401) {
        logout();
        return;
      }
    } finally {
      setPasskeyBusy(false);
    }
  }

  // Redirect if not authenticated
  if (!isLoadingUser && !user) {
    navigate("/login");
    return null;
  }

  return (
    <div className="privacy-settings-page">
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ margin: "0 0 8px 0", fontSize: "28px" }}>
          Setări de Confidențialitate
        </h1>
        <p style={{ margin: 0, opacity: 0.8 }}>
          Controlează ce informații sunt publice și cum pot alți utilizatori să
          te descopere.
        </p>
      </div>

      {/* Loading state */}
      {isLoading ? (
        <div style={{ ...ui.card, textAlign: "center", padding: "40px" }}>
          <p>Se încarcă setările...</p>
        </div>
      ) : null}

      {/* Error state */}
      {error ? (
        <div
          style={{
            ...ui.card,
            borderLeft: `4px solid ${ui.colors.danger}`,
            padding: "16px",
          }}
          role="alert"
        >
          <p style={{ margin: 0, color: ui.colors.danger }}>
            <strong>Eroare:</strong> {error}
          </p>
        </div>
      ) : null}

      {/* Main content */}
      {!isLoading && !error ? (
        <div>
          {/* Privacy Controls */}
          <div style={{ ...ui.card, marginBottom: "20px" }}>
            <h2 style={{ margin: "0 0 16px 0", fontSize: "18px" }}>
              Controluri de Confidențialitate
            </h2>

            <div style={{ display: "grid", gap: "12px" }}>
              {Object.entries(PRIVACY_CONTROLS).map(([key, config]) => (
                <div
                  key={key}
                  style={{
                    padding: "12px",
                    border: `1px solid ${ui.colors.border}`,
                    borderRadius: "8px",
                    backgroundColor:
                      expandedControl === key
                        ? `rgba(59, 130, 246, 0.05)`
                        : "transparent",
                  }}
                >
                  {/* Control header with toggle */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "12px",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={formData[key]}
                      onChange={() => handleToggle(key)}
                      disabled={isSaving}
                      style={{
                        marginTop: "3px",
                        cursor: "pointer",
                        flexShrink: 0,
                      }}
                    />

                    <div
                      style={{
                        flex: 1,
                        cursor: "pointer",
                        userSelect: "none",
                      }}
                      onClick={() =>
                        setExpandedControl(expandedControl === key ? null : key)
                      }
                    >
                      <div
                        style={{
                          fontWeight: 600,
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                        }}
                      >
                        {config.label}
                        <span style={{ opacity: 0.6 }}>
                          {expandedControl === key ? "▼" : "▶"}
                        </span>
                      </div>
                      <p
                        style={{
                          margin: "4px 0 0 0",
                          opacity: 0.8,
                          fontSize: "14px",
                        }}
                      >
                        {config.description}
                      </p>
                    </div>

                    {/* Status indicator */}
                    <div
                      style={{
                        padding: "4px 10px",
                        borderRadius: "4px",
                        fontSize: "12px",
                        fontWeight: 600,
                        whiteSpace: "nowrap",
                        flexShrink: 0,
                        backgroundColor: formData[key]
                          ? "rgba(34, 197, 94, 0.15)"
                          : "rgba(107, 114, 128, 0.15)",
                        color: formData[key]
                          ? "rgb(22, 163, 74)"
                          : "rgb(75, 85, 99)",
                      }}
                    >
                      {formData[key] ? "PUBLIC" : "PRIVAT"}
                    </div>
                  </div>

                  {/* Expanded details */}
                  {expandedControl === key ? (
                    <div
                      style={{
                        marginTop: "12px",
                        paddingTop: "12px",
                        borderTop: `1px solid ${ui.colors.border}`,
                      }}
                    >
                      <p
                        style={{
                          margin: "0 0 8px 0",
                          fontSize: "13px",
                          opacity: 0.8,
                        }}
                      >
                        <strong>Ce se va întâmpla dacă este activat:</strong>
                      </p>
                      <ul
                        style={{
                          margin: "0",
                          paddingLeft: "20px",
                          fontSize: "13px",
                        }}
                      >
                        {config.details.map((detail, idx) => (
                          <li key={idx} style={{ marginBottom: "4px" }}>
                            {detail}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </div>

          <div style={{ ...ui.card, marginBottom: "20px" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "12px",
                marginBottom: "12px",
              }}
            >
              <div>
                <h2 style={{ margin: 0, fontSize: "18px" }}>Sesiuni active</h2>
                <p
                  style={{
                    margin: "6px 0 0 0",
                    opacity: 0.8,
                    fontSize: "14px",
                  }}
                >
                  Vezi unde ești conectat și revocă instant tokenurile active.
                </p>
              </div>
              <button
                type="button"
                onClick={handleRevokeAllSessions}
                disabled={!sessions.length}
                style={{ ...ui.buttonSmall }}
              >
                Revocă toate
              </button>
            </div>

            {sessionsLoading ? (
              <p style={{ margin: 0 }}>Se încarcă...</p>
            ) : null}
            {sessionsError ? (
              <p style={{ ...ui.errorText, margin: 0 }}>{sessionsError}</p>
            ) : null}
            {sessionsActionError ? (
              <p style={{ ...ui.errorText, margin: "8px 0 0 0" }}>
                {sessionsActionError}
              </p>
            ) : null}
            {sessionsActionSuccess ? (
              <p style={{ margin: "8px 0 0 0", color: "rgb(22, 163, 74)" }}>
                {sessionsActionSuccess}
              </p>
            ) : null}

            {!sessionsLoading && !sessionsError ? (
              <div style={{ display: "grid", gap: "10px", marginTop: "12px" }}>
                {sessions.length ? (
                  sessions.map((session) => (
                    <div
                      key={session.id}
                      style={{
                        padding: "12px",
                        border: `1px solid ${ui.colors.border}`,
                        borderRadius: "12px",
                        display: "grid",
                        gap: "8px",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: "12px",
                        }}
                      >
                        <strong>
                          {session.is_current
                            ? "Sesiunea curentă"
                            : "Sesiune activă"}
                        </strong>
                        <button
                          type="button"
                          onClick={() => handleRevokeSession(session.id)}
                          style={{ ...ui.buttonSmall }}
                        >
                          Revocă
                        </button>
                      </div>
                      <div style={{ fontSize: "14px", opacity: 0.85 }}>
                        <div>IP: {session.ip || "necunoscut"}</div>
                        <div>UA: {session.user_agent || "necunoscut"}</div>
                        <div>
                          Ultima activitate:{" "}
                          <RelativeTime
                            value={session.last_active || session.created_at}
                          />
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <p style={{ margin: 0, opacity: 0.8 }}>
                    Nu există alte sesiuni active.
                  </p>
                )}
              </div>
            ) : null}
          </div>

          <div style={{ ...ui.card, marginBottom: "20px" }}>
            <h2 style={{ margin: "0 0 8px 0", fontSize: "18px" }}>
              Passkeys / WebAuthn
            </h2>
            <p style={{ margin: 0, opacity: 0.8, fontSize: "14px" }}>
              Adaugă o cheie hardware sau un passkey din browser pentru login
              mai sigur.
            </p>
            {passkeyError ? (
              <p style={{ ...ui.errorText, marginTop: "12px" }}>
                {passkeyError}
              </p>
            ) : null}
            {passkeySuccess ? (
              <p style={{ marginTop: "12px", color: "rgb(22, 163, 74)" }}>
                {passkeySuccess}
              </p>
            ) : null}
            <button
              type="button"
              onClick={handleRegisterPasskey}
              disabled={passkeyBusy}
              style={{ ...ui.button, marginTop: "12px" }}
            >
              {passkeyBusy ? "Se înregistrează..." : "Adaugă passkey"}
            </button>
          </div>

          <div style={{ ...ui.card, marginBottom: "20px" }}>
            <h2 style={{ margin: "0 0 8px 0", fontSize: "18px" }}>
              Schimbare email
            </h2>
            <p style={{ margin: 0, opacity: 0.8, fontSize: "14px" }}>
              Poți cere schimbarea adresei de email; va trebui să confirmi de la
              adresa nouă.
            </p>
            {emailChangeError ? (
              <p style={{ ...ui.errorText, marginTop: "12px" }}>
                {emailChangeError}
              </p>
            ) : null}
            {emailChangeMessage ? (
              <p style={{ marginTop: "12px", color: "rgb(22, 163, 74)" }}>
                {emailChangeMessage}
              </p>
            ) : null}
            <div style={{ marginTop: 12 }}>
              <input
                type="email"
                placeholder="Nou email"
                value={newEmailValue}
                onChange={(e) => setNewEmailValue(e.target.value)}
                style={{ width: "100%", marginTop: 6, ...ui.input }}
              />
              <input
                type="password"
                placeholder="Parola curentă"
                value={currentPasswordValue}
                onChange={(e) => setCurrentPasswordValue(e.target.value)}
                style={{ width: "100%", marginTop: 8, ...ui.input }}
              />
              <div style={{ marginTop: 8 }}>
                <button
                  type="button"
                  onClick={handleRequestEmailChange}
                  disabled={emailChangeLoading}
                  style={{ ...ui.button }}
                >
                  {emailChangeLoading
                    ? "Se trimite..."
                    : "Trimite cerere schimbare email"}
                </button>
              </div>
            </div>
          </div>

          <div style={{ ...ui.card, marginBottom: "20px" }}>
            <h2 style={{ margin: "0 0 8px 0", fontSize: "18px" }}>
              Schimbare parolă
            </h2>
            <p style={{ margin: 0, opacity: 0.8, fontSize: "14px" }}>
              Schimbă parola curentă a contului.
            </p>
            {passwordChangeError ? (
              <p style={{ ...ui.errorText, marginTop: "12px" }}>
                {passwordChangeError}
              </p>
            ) : null}
            {passwordChangeMessage ? (
              <p style={{ marginTop: "12px", color: "rgb(22, 163, 74)" }}>
                {passwordChangeMessage}
              </p>
            ) : null}
            <div style={{ marginTop: 12 }}>
              <input
                type="password"
                placeholder="Parola curentă"
                value={currentPasswordValue}
                onChange={(e) => setCurrentPasswordValue(e.target.value)}
                style={{ width: "100%", marginTop: 6, ...ui.input }}
              />
              <input
                type="password"
                placeholder="Noua parolă"
                value={newPasswordValue}
                onChange={(e) => setNewPasswordValue(e.target.value)}
                style={{ width: "100%", marginTop: 8, ...ui.input }}
              />
              <div style={{ marginTop: 8 }}>
                <button
                  type="button"
                  onClick={handleChangePassword}
                  disabled={passwordChangeLoading}
                  style={{ ...ui.button }}
                >
                  {passwordChangeLoading ? "Se schimbă..." : "Schimbă parola"}
                </button>
              </div>
            </div>
          </div>

          {/* Save section */}
          {saveError ? (
            <div
              style={{
                ...ui.card,
                borderLeft: `4px solid ${ui.colors.danger}`,
                marginBottom: "16px",
                padding: "12px",
              }}
              role="alert"
            >
              <p
                style={{ margin: 0, color: ui.colors.danger, fontSize: "14px" }}
              >
                {saveError}
              </p>
            </div>
          ) : null}

          {saveSuccess ? (
            <div
              style={{
                ...ui.card,
                borderLeft: `4px solid rgb(34, 197, 94)`,
                marginBottom: "16px",
                padding: "12px",
              }}
              role="alert"
            >
              <p
                style={{
                  margin: 0,
                  color: "rgb(22, 163, 74)",
                  fontSize: "14px",
                }}
              >
                ✓ {saveSuccess}
              </p>
            </div>
          ) : null}

          {/* Action buttons */}
          <div style={{ display: "flex", gap: "8px", marginTop: "16px" }}>
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving || !unsavedChanges || isLoading}
              style={{
                ...ui.button,
                opacity: unsavedChanges && !isSaving ? 1 : 0.6,
                cursor: unsavedChanges && !isSaving ? "pointer" : "not-allowed",
              }}
            >
              {isSaving ? "Se salvează..." : "Salvează schimbări"}
            </button>

            <button
              type="button"
              onClick={handleReset}
              disabled={!unsavedChanges || isSaving || isLoading}
              style={{
                ...ui.buttonSmall,
                opacity: unsavedChanges && !isSaving ? 1 : 0.6,
                cursor: unsavedChanges && !isSaving ? "pointer" : "not-allowed",
              }}
            >
              Anulează
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
