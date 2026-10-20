import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { loginUser } from "../api/auth.js";
import {
  completeWebAuthnLogin,
  credentialToAssertion,
  getWebAuthnLoginOptions,
  normalizePublicKeyOptions,
} from "../api/security.js";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

export default function LoginPage() {
  const navigate = useNavigate();
  const auth = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPasskeySubmitting, setIsPasskeySubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();

    setIsSubmitting(true);
    setError(null);

    try {
      const data = await loginUser({
        username: username.trim(),
        password,
      });

      // SimpleJWT returns: { access, refresh }
      if (data && (data.access || data.refresh)) {
        auth.login({ access: data.access, refresh: data.refresh });
      }

      navigate("/");
    } catch (err) {
      console.error(err);
      const serverDetail = err?.response?.data?.detail;
      if (serverDetail) {
        setError(serverDetail);
      } else {
        setError("Login eșuat. Verifică username/parola și încearcă din nou.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handlePasskeyLogin() {
    if (!username.trim()) {
      setError("Completează username-ul înainte de login cu passkey.");
      return;
    }
    if (!window.PublicKeyCredential) {
      setError("Browserul tău nu suportă WebAuthn.");
      return;
    }

    setIsPasskeySubmitting(true);
    setError(null);

    try {
      const options = await getWebAuthnLoginOptions({
        username: username.trim(),
      });
      const credential = await navigator.credentials.get(
        normalizePublicKeyOptions(options),
      );
      if (!credential) {
        setError("Login-ul cu passkey a fost anulat.");
        return;
      }

      const data = await completeWebAuthnLogin({
        username: username.trim(),
        assertion: credentialToAssertion(credential),
      });

      if (data && (data.access || data.refresh)) {
        auth.login({ access: data.access, refresh: data.refresh });
      }

      navigate("/");
    } catch (err) {
      console.error(err);
      const serverDetail = err?.response?.data?.detail;
      if (serverDetail) {
        setError(serverDetail);
      } else {
        setError("Login-ul cu passkey a eșuat. Încearcă din nou.");
      }
    } finally {
      setIsPasskeySubmitting(false);
    }
  }

  return (
    <div style={{ padding: "24px", maxWidth: "420px", margin: "0 auto" }}>
      <h1>Login</h1>

      <form onSubmit={handleSubmit} style={{ marginTop: "16px" }}>
        <label style={{ display: "block", marginTop: "12px" }}>
          <div style={{ fontWeight: 600 }}>username</div>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoComplete="username"
            style={{ width: "100%", marginTop: "6px", ...ui.input }}
          />
        </label>

        <label style={{ display: "block", marginTop: "12px" }}>
          <div style={{ fontWeight: 600 }}>password</div>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            style={{ width: "100%", marginTop: "6px", ...ui.input }}
          />
        </label>

        {error ? (
          <p style={{ ...ui.errorText, marginTop: "12px" }}>{error}</p>
        ) : null}

        <button
          type="submit"
          disabled={isSubmitting}
          style={{ marginTop: "16px", ...ui.button }}
        >
          {isSubmitting ? "Se trimite..." : "Login"}
        </button>

        <button
          type="button"
          disabled={isPasskeySubmitting}
          onClick={handlePasskeyLogin}
          style={{ marginTop: "12px", ...ui.buttonSmall, width: "100%" }}
        >
          {isPasskeySubmitting ? "Se verifică passkey..." : "Login cu passkey"}
        </button>
      </form>

      <p style={{ marginTop: "16px" }}>
        Nu ai cont? <Link to="/register">Register</Link>
      </p>
    </div>
  );
}
