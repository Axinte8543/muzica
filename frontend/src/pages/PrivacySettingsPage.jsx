import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

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

  const [formData, setFormData] = useState({
    public_lists: true,
    public_activity: true,
    public_compatibility: true,
  });

  const [unsavedChanges, setUnsavedChanges] = useState(false);
  const [expandedControl, setExpandedControl] = useState(null);

  const canLoad = useMemo(() => {
    return Boolean(isAuthVerified && accessToken);
  }, [isAuthVerified, accessToken]);

  // Load privacy settings
  useEffect(() => {
    let isCancelled = false;

    async function loadSettings() {
      if (!canLoad) {
        setSettings(null);
        setIsLoading(false);
        setError(null);
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

  // Redirect if not authenticated
  if (!isLoadingUser && !user) {
    navigate("/login");
    return null;
  }

  return (
    <div style={{ padding: "20px 16px", maxWidth: "800px", margin: "0 auto" }}>
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
