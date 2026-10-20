import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { confirmEmailChange } from "../api/auth.js";
import { ui } from "../ui/ui.js";

export default function ConfirmEmailChangePage() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState("loading");
  const [message, setMessage] = useState("Se confirmă schimbarea emailului...");

  useEffect(() => {
    let cancelled = false;

    async function confirmChange() {
      const token = String(searchParams.get("token") || "").trim();
      if (!token) {
        if (!cancelled) {
          setStatus("error");
          setMessage("Tokenul de confirmare lipsește.");
        }
        return;
      }

      try {
        await confirmEmailChange({ token });
        if (!cancelled) {
          setStatus("success");
          setMessage("Emailul a fost schimbat cu succes.");
        }
      } catch (err) {
        console.error(err);
        const serverDetail = err?.response?.data?.detail;
        if (!cancelled) {
          setStatus("error");
          setMessage(
            serverDetail ||
              "Schimbarea emailului a eșuat. Linkul poate fi expirat sau invalid.",
          );
        }
      }
    }

    confirmChange();

    return () => {
      cancelled = true;
    };
  }, [searchParams]);

  return (
    <div style={{ padding: "24px", maxWidth: "560px", margin: "0 auto" }}>
      <div style={ui.card}>
        <p
          style={{
            marginTop: 0,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            opacity: 0.72,
          }}
        >
          Securitate cont
        </p>
        <h1 style={{ marginTop: 0 }}>Schimbare email</h1>
        <p style={{ marginBottom: 0 }}>{message}</p>

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 20 }}>
          <Link to="/login" style={ui.button}>
            Mergi la login
          </Link>
          {status === "error" ? (
            <Link to="/profile/privacy" style={ui.button}>
              Înapoi la setări
            </Link>
          ) : null}
        </div>
      </div>
    </div>
  );
}
