import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { verifyEmail } from "../api/auth.js";
import { ui } from "../ui/ui.js";

export default function VerifyEmailPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [status, setStatus] = useState("loading");
  const [message, setMessage] = useState("Se verifică emailul...");

  useEffect(() => {
    let cancelled = false;

    async function runVerification() {
      const token = String(searchParams.get("token") || "").trim();
      if (!token) {
        if (!cancelled) {
          setStatus("error");
          setMessage("Tokenul de verificare lipsește.");
        }
        return;
      }

      try {
        await verifyEmail({ token });
        if (!cancelled) {
          setStatus("success");
          setMessage("Email verificat cu succes. Acum te poți autentifica.");
        }
      } catch (err) {
        console.error(err);
        const serverDetail = err?.response?.data?.detail;
        if (!cancelled) {
          setStatus("error");
          setMessage(
            serverDetail ||
              "Verificarea emailului a eșuat. Linkul poate fi expirat sau invalid.",
          );
        }
      }
    }

    runVerification();

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
          Verificare cont
        </p>
        <h1 style={{ marginTop: 0 }}>Email verification</h1>
        <p style={{ marginBottom: 0 }}>{message}</p>

        <div
          style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 20 }}
        >
          <Link to="/login" style={ui.button}>
            Mergi la login
          </Link>
          {status === "error" ? (
            <button
              type="button"
              onClick={() => navigate("/register")}
              style={ui.button}
            >
              Creează alt cont
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
