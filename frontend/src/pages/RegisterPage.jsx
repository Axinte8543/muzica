import { useState } from "react";
import { Link } from "react-router-dom";

import { registerUser, resendVerification } from "../api/auth.js";
import { ui } from "../ui/ui.js";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [registeredEmail, setRegisteredEmail] = useState(null);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendMessage, setResendMessage] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    // Prevent submitting when password doesn't meet requirements
    const checks = passwordChecks(password);
    if (!Object.values(checks).every(Boolean)) {
      setError("Parola nu îndeplinește cerințele minime.");
      return;
    }
    setIsSubmitting(true);
    setError(null);

    try {
      await registerUser({
        username: username.trim(),
        email: email.trim(),
        password,
      });

      // show confirmation UI and allow resending verification
      setRegisteredEmail(email.trim());
      setResendMessage(null);
      setPassword("");
      setUsername("");
    } catch (err) {
      console.error(err);
      const serverDetail = err?.response?.data?.detail;
      if (serverDetail) {
        setError(serverDetail);
        return;
      }

      const responseData = err?.response?.data;
      if (responseData && typeof responseData === "object") {
        const fieldErrors = Object.entries(responseData)
          .map(([field, value]) => {
            const message = Array.isArray(value)
              ? value.join(" ")
              : String(value);
            return `${field}: ${message}`;
          })
          .join(" | ");
        if (fieldErrors) {
          setError(fieldErrors);
          return;
        }
      }

      setError("Înregistrarea a eșuat. Verifică datele și încearcă din nou.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div style={{ padding: "24px", maxWidth: "420px", margin: "0 auto" }}>
      <h1>Register</h1>

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
          <div style={{ fontWeight: 600 }}>email</div>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
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
            autoComplete="new-password"
            style={{ width: "100%", marginTop: "6px", ...ui.input }}
          />
        </label>

        <PasswordRequirements password={password} />

        {error ? (
          <p style={{ ...ui.errorText, marginTop: "12px" }}>{error}</p>
        ) : null}

        <button
          type="submit"
          disabled={
            isSubmitting ||
            !Object.values(passwordChecks(password)).every(Boolean)
          }
          style={{ marginTop: "16px", ...ui.button }}
        >
          {isSubmitting ? "Se trimite..." : "Înregistrează-te"}
        </button>
      </form>

      {registeredEmail ? (
        <div
          style={{
            marginTop: 18,
            padding: 12,
            background: "var(--surface-strong)",
            borderRadius: 6,
          }}
        >
          <p style={{ margin: 0 }}>
            Cont creat. Verifică căsuța de email:{" "}
            <strong>{registeredEmail}</strong>
          </p>
          <div style={{ marginTop: 8 }}>
            <button
              onClick={async () => {
                setResendLoading(true);
                setResendMessage(null);
                try {
                  await resendVerification({ email: registeredEmail });
                  setResendMessage(
                    "Email de verificare retrimis. Verifică inbox-ul.",
                  );
                } catch (e) {
                  console.error(e);
                  setResendMessage(
                    "Eroare la retrimitere. Încearcă din nou mai târziu.",
                  );
                } finally {
                  setResendLoading(false);
                }
              }}
              disabled={resendLoading}
              style={{ marginRight: 8, ...ui.button }}
            >
              {resendLoading ? "Se trimite..." : "Retrimite verificarea"}
            </button>
            <Link to="/login" style={{ marginLeft: 8 }}>
              Autentifică-te
            </Link>
          </div>
          {resendMessage ? (
            <p style={{ marginTop: 8 }}>{resendMessage}</p>
          ) : null}
        </div>
      ) : (
        <p style={{ marginTop: "16px" }}>
          Ai deja cont? <Link to="/login">Login</Link>
        </p>
      )}
    </div>
  );
}

function passwordChecks(pw = "") {
  const s = String(pw || "");
  return {
    minLength: s.length >= 8,
    lowercase: /[a-z]/.test(s),
    uppercase: /[A-Z]/.test(s),
    number: /[0-9]/.test(s),
    special: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?`~]/.test(s),
  };
}

function PasswordRequirements({ password }) {
  const checks = passwordChecks(password);
  return (
    <div className="password-requirements" aria-live="polite">
      <div style={{ marginTop: 8, marginBottom: 6, fontWeight: 600 }}>
        Cerințe parolă
      </div>
      <ul style={{ margin: 0, paddingLeft: 18 }}>
        <Requirement met={checks.minLength}>Minim 8 caractere</Requirement>
        <Requirement met={checks.lowercase}>
          Cel puțin o literă mică
        </Requirement>
        <Requirement met={checks.uppercase}>
          Cel puțin o literă mare
        </Requirement>
        <Requirement met={checks.number}>Cel puțin o cifră</Requirement>
        <Requirement met={checks.special}>
          Cel puțin un caracter special (!@#$...)
        </Requirement>
      </ul>
    </div>
  );
}

function Requirement({ met, children }) {
  return (
    <li className={`requirement ${met ? "met" : "unmet"}`}>
      <span aria-hidden style={{ marginRight: 8 }}>
        {met ? "✓" : "○"}
      </span>
      <span>{children}</span>
    </li>
  );
}
