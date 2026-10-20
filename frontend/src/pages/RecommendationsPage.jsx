import { Link } from "react-router-dom";

import RecommendedAlbums from "../components/RecommendedAlbums.jsx";
import { useAuth } from "../context/useAuth.js";
import { ui } from "../ui/ui.js";

function Section({ title, children, actionTo, actionLabel }) {
  return (
    <section
      style={{
        ...ui.card,
        marginTop: "18px",
        padding: "20px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
          flexWrap: "wrap",
        }}
      >
        <h2 style={{ margin: 0 }}>{title}</h2>
        {actionTo && actionLabel ? (
          <Link
            to={actionTo}
            style={{
              ...ui.button,
              textDecoration: "none",
              color: "inherit",
              display: "inline-block",
            }}
          >
            {actionLabel}
          </Link>
        ) : null}
      </div>
      <div style={{ marginTop: "14px" }}>{children}</div>
    </section>
  );
}

export default function RecommendationsPage() {
  const { isAuthenticated, isAuthVerified } = useAuth();

  if (!isAuthenticated) {
    return (
      <div style={{ ...ui.container, paddingTop: "18px" }}>
        <div
          style={{
            ...ui.card,
            padding: "24px",
            background:
              "linear-gradient(135deg, rgba(245, 158, 11, 0.18), rgba(15, 23, 42, 0.06))",
          }}
        >
          <h1 style={{ marginTop: 0 }}>Recomandări</h1>
          <p style={{ marginBottom: 0 }}>
            Trebuie să fii autentificat ca să vezi recomandările personalizate.
          </p>
          <p style={{ marginBottom: 0 }}>
            <Link to="/login">Mergi la Login</Link>
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthVerified) {
    return (
      <div style={{ ...ui.container, paddingTop: "18px" }}>
        <div
          style={{
            ...ui.card,
            padding: "24px",
          }}
        >
          <h1 style={{ marginTop: 0 }}>Recomandări</h1>
          <p style={{ marginBottom: 0 }}>Se încarcă...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ ...ui.container, paddingTop: "18px" }}>
      <div
        style={{
          ...ui.card,
          padding: "28px",
          background:
            "linear-gradient(135deg, rgba(245, 158, 11, 0.18), rgba(15, 23, 42, 0.04))",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: "20px",
            flexWrap: "wrap",
          }}
        >
          <div style={{ maxWidth: "760px" }}>
            <p
              style={{
                margin: 0,
                textTransform: "uppercase",
                letterSpacing: "0.12em",
                fontSize: "0.8rem",
                opacity: 0.75,
              }}
            >
              Personalizat pentru tine
            </p>
            <h1 style={{ margin: "10px 0 12px", fontSize: "2.1rem" }}>
              Recomandări muzicale
            </h1>
            <p style={{ margin: 0, maxWidth: "62ch" }}>
              Aici vezi albumele sugerate de aplicație, pe baza preferințelor
              tale, a activității din platformă și a conexiunilor sociale.
            </p>
          </div>
          <div
            style={{
              display: "grid",
              gap: "10px",
              minWidth: "220px",
            }}
          >
            <Link
              to="/dashboard"
              style={{
                ...ui.button,
                textDecoration: "none",
                color: "inherit",
                textAlign: "center",
              }}
            >
              Vezi dashboard-ul
            </Link>
            <Link
              to="/similar-users"
              style={{
                ...ui.button,
                textDecoration: "none",
                color: "inherit",
                textAlign: "center",
              }}
            >
              Utilizatori similari
            </Link>
          </div>
        </div>
      </div>

      {/* How recommendations work */}
      <Section
        title="Pentru tine"
        actionTo="/dashboard"
        actionLabel="Deschide dashboard-ul"
      >
        <RecommendedAlbums limit={50} pageSize={10} />
      </Section>

      <Section
        title="Ce mai poți explora"
        actionTo="/artists/highest-rated"
        actionLabel="Artiști apreciați"
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "16px",
          }}
        >
          <Link
            to="/similar-users"
            style={{
              ...ui.card,
              color: "inherit",
              textDecoration: "none",
              display: "block",
            }}
          >
            <div style={{ fontWeight: 800 }}>Utilizatori similari</div>
            <p style={{ marginBottom: 0, opacity: 0.9 }}>
              Vezi ce persoane au gusturi apropiate și ce ascultă ele.
            </p>
          </Link>

          <Link
            to="/following"
            style={{
              ...ui.card,
              color: "inherit",
              textDecoration: "none",
              display: "block",
            }}
          >
            <div style={{ fontWeight: 800 }}>Artiști urmăriți</div>
            <p style={{ marginBottom: 0, opacity: 0.9 }}>
              Folosește artiștii urmăriți ca să descoperi conținut apropiat.
            </p>
          </Link>
        </div>
      </Section>
    </div>
  );
}
