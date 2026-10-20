import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { confirmPasswordReset } from "../api/auth.js";
import { ui } from "../ui/ui.js";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = String(searchParams.get("token") || "").trim();

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(token ? null : "Tokenul de resetare lipsește.");

  async function handleSubmit(event) {
    event.preventDefault();
    setMessage(null);
    setError(null);

    if (!token) {
      setError("Tokenul de resetare lipsește.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Parolele nu coincid.");
      return;
    }

    setIsSubmitting(true);
    try {
      await confirmPasswordReset({ token, password });
      setPassword("");
      setConfirmPassword("");
      setMessage("Parola a fost resetată. Acum te poți autentifica.");
    } catch (err) {
      console.error(err);
      setError(
        err?.response?.data?.detail ||
          "Resetarea parolei a eșuat. Linkul poate fi expirat sau invalid.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

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
        <h1 style={{ marginTop: 0 }}>Resetare parolă</h1>

        <form onSubmit={handleSubmit} style={{ display: "grid", gap: 12 }}>
          <label>
            <div style={{ fontWeight: 600 }}>Parolă nouă</div>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              autoComplete="new-password"
              disabled={!token || Boolean(message)}
              style={{ width: "100%", marginTop: 6, ...ui.input }}
            />
          </label>

          <label>
            <div style={{ fontWeight: 600 }}>Confirmă parola</div>
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
              autoComplete="new-password"
              disabled={!token || Boolean(message)}
              style={{ width: "100%", marginTop: 6, ...ui.input }}
            />
          </label>

          {error ? <p style={{ ...ui.errorText, margin: 0 }}>{error}</p> : null}
          {message ? (
            <p style={{ margin: 0, color: "rgb(22, 163, 74)" }}>{message}</p>
          ) : null}

          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {!message ? (
              <button
                type="submit"
                disabled={isSubmitting || !token}
                style={ui.button}
              >
                {isSubmitting ? "Se salvează..." : "Salvează parola"}
              </button>
            ) : null}
            <Link to="/login" style={ui.button}>
              Mergi la login
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
