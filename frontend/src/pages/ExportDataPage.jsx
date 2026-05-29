import { useState } from "react";
import { useAuth } from "../context/useAuth.js";
import { exportMyDataBlob } from "../api/exportData.js";
import { ui } from "../ui/ui.js";
import "../styles/ExportDataPage.css";

const EXPORT_RESOURCES = [
  {
    id: "listens",
    label: "Albumele Ascultate",
    description: "Toate albumele ascultate cu date",
    icon: "🎵",
  },
  {
    id: "ratings",
    label: "Ratinguri Albume",
    description: "Toate ratingurile tale pentru albume (1-5 stele)",
    icon: "⭐",
  },
  {
    id: "reviews",
    label: "Recenzii Albume",
    description: "Toate recenziile tale scrise cu conținut",
    icon: "💬",
  },
  {
    id: "lists",
    label: "Listele Mele",
    description: "Toate listele tale create și metadatele",
    icon: "📋",
  },
  {
    id: "activity",
    label: "Jurnal de Activitate",
    description: "Toate activitățile și interacțiunile tale",
    icon: "📊",
  },
];

export default function ExportDataPage() {
  const { isAuthenticated } = useAuth();
  const [selectedResource, setSelectedResource] = useState("listens");
  const [format, setFormat] = useState("csv");
  const [limit, setLimit] = useState("5000");
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState(null);

  if (!isAuthenticated) {
    return (
      <div className="page-container export-data-page">
        <div className="error-state">
          <p>{ui.mustBeLoggedIn}</p>
        </div>
      </div>
    );
  }

  async function handleExport() {
    if (!selectedResource) {
      setError("Selectați un tip de date pentru export");
      return;
    }

    setError(null);
    setIsExporting(true);

    try {
      const blob = await exportMyDataBlob({
        format,
        resource: selectedResource,
        limit: parseInt(limit, 10) || 5000,
      });

      // Determine file extension
      const ext = format === "csv" ? "csv" : "json";
      const filename = `${selectedResource}_${new Date().toISOString().split("T")[0]}.${ext}`;

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "A apărut o eroare la exportul datelor",
      );
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <div className="page-container export-data-page">
      <div className="page-header">
        <h1>📥 Exportă Date Personale</h1>
        <p className="subtitle">
          Descarcă datele tale muzicale, ratinguri, recenzii și activitate.
        </p>
      </div>

      <div className="export-container">
        <section className="section">
          <h2>Selectează Date pentru Export</h2>
          <div className="resources-grid">
            {EXPORT_RESOURCES.map((resource) => (
              <div
                key={resource.id}
                className={`resource-card ${selectedResource === resource.id ? "selected" : ""}`}
                onClick={() => setSelectedResource(resource.id)}
              >
                <div className="resource-icon">{resource.icon}</div>
                <div className="resource-content">
                  <h3>{resource.label}</h3>
                  <p>{resource.description}</p>
                </div>
                {selectedResource === resource.id && (
                  <div className="checkmark">✓</div>
                )}
              </div>
            ))}
          </div>
        </section>

        <section className="section">
          <h2>Setări Export</h2>
          <div className="settings-grid">
            <div className="setting-group">
              <label htmlFor="format-select">Format</label>
              <select
                id="format-select"
                value={format}
                onChange={(e) => setFormat(e.target.value)}
                disabled={isExporting}
              >
                <option value="csv">CSV (Foaie de calcul)</option>
                <option value="json">JSON (Date brute)</option>
              </select>
              <p className="setting-hint">
                {format === "csv"
                  ? "CSV este mai bun pentru Excel sau Google Sheets"
                  : "JSON este mai bun pentru backup sau analiză de date"}
              </p>
            </div>

            <div className="setting-group">
              <label htmlFor="limit-input">Limita Rânduri (max 10.000)</label>
              <input
                id="limit-input"
                type="number"
                min="1"
                max="10000"
                value={limit}
                onChange={(e) => setLimit(e.target.value)}
                disabled={isExporting}
              />
              <p className="setting-hint">
                Intrări cele mai recente mai întâi. Lasă gol pentru 5.000
                rânduri.
              </p>
            </div>
          </div>
        </section>

        {error && <div className="error-message">{error}</div>}

        <div className="action-buttons">
          <button
            className="btn-export"
            onClick={handleExport}
            disabled={isExporting || !selectedResource}
          >
            {isExporting ? "Se exportă..." : "📥 Descarcă Export"}
          </button>
        </div>
      </div>
    </div>
  );
}
