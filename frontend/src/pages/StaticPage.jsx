import { ui } from "../ui/ui.js";
import { Link } from "react-router-dom";

export default function StaticPage({ title, children, message }) {
  const isNotFound = title === "Not Found";
  const defaultMessage = isNotFound
    ? "Pagina pe care o cauți nu există."
    : "Pagina este în lucru. Revino în curând.";

  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>{title}</h1>
      <div style={{ maxWidth: "920px" }}>
        {children || (
          <>
            <p style={{ opacity: 0.85 }}>{message || defaultMessage}</p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Link to="/search" style={ui.button}>
                Caută
              </Link>
              <Link to="/albums" style={ui.button}>
                Vezi albumele
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
