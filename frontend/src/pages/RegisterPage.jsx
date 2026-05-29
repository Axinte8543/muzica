import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { registerUser } from "../api/auth.js";
import { ui } from "../ui/ui.js";

export default function RegisterPage() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();

    setIsSubmitting(true);
    setError(null);

    try {
      await registerUser({
        username: username.trim(),
        email: email.trim(),
        password,
      });

      navigate("/login");
    } catch (err) {
      console.error(err);
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

        {error ? (
          <p style={{ ...ui.errorText, marginTop: "12px" }}>{error}</p>
        ) : null}

        <button
          type="submit"
          disabled={isSubmitting}
          style={{ marginTop: "16px", ...ui.button }}
        >
          {isSubmitting ? "Se trimite..." : "Register"}
        </button>
      </form>

      <p style={{ marginTop: "16px" }}>
        Ai deja cont? <Link to="/login">Login</Link>
      </p>
    </div>
  );
}
