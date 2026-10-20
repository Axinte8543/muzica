import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";

function NavLink({ to, label, isActive, onNavigate }) {
  return (
    <Link
      to={to}
      onClick={onNavigate}
      style={{
        color: isActive ? "#f59e0b" : "inherit",
        textDecoration: isActive ? "underline" : "none",
        fontWeight: isActive ? 700 : 400,
        padding: "8px 10px",
        borderRadius: 10,
        background: isActive ? "rgba(245, 158, 11, 0.12)" : "transparent",
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </Link>
  );
}

const NAV_ITEMS = [
  { to: "/profile/listens", label: "Ascultate" },
  { to: "/profile/want-to-listen", label: "De ascultat" },
  { to: "/profile/challenges/weekly", label: "Provocări" },
  { to: "/profile/badges", label: "Insigne" },
  { to: "/profile/achievements", label: "Realizări" },
  { to: "/profile/reviews", label: "Review-uri" },
  { to: "/profile/ratings", label: "Ratinguri" },
  { to: "/profile/liked-albums", label: "Albume apreciate" },
  { to: "/profile/friends", label: "Prieteni" },
  { to: "/profile/stats", label: "Statistici" },
  { to: "/profile/top", label: "Top-ul meu" },
  { to: "/profile/suggestions", label: "Sugestiile mele" },
  { to: "/profile/privacy", label: "Confidențialitate" },
  { to: "/profile/export", label: "Export date" },
];

export default function ProfileNav() {
  const location = useLocation();
  const path = location.pathname || "";
  const [isCompact, setIsCompact] = useState(() => {
    if (typeof window === "undefined") {
      return false;
    }
    return window.matchMedia("(max-width: 1180px)").matches;
  });
  const [isOpen, setIsOpen] = useState(false);

  const activeItem = useMemo(() => {
    return NAV_ITEMS.find((item) => path.startsWith(item.to)) || NAV_ITEMS[0];
  }, [path]);

  useEffect(() => {
    const media = window.matchMedia("(max-width: 1180px)");

    const updateLayout = () => {
      setIsCompact(media.matches);
    };

    updateLayout();

    if (typeof media.addEventListener === "function") {
      media.addEventListener("change", updateLayout);
      return () => media.removeEventListener("change", updateLayout);
    }

    media.addListener(updateLayout);
    return () => media.removeListener(updateLayout);
  }, []);

  return (
    <div
      style={{
        padding: "12px 24px",
        borderBottom: "1px solid #e5e7eb",
        display: "grid",
        gap: 12,
      }}
    >
      {isCompact ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <button
            type="button"
            onClick={() => setIsOpen((value) => !value)}
            aria-expanded={isOpen}
            aria-controls="profile-nav-menu"
            style={{
              border: "1px solid rgba(245, 158, 11, 0.25)",
              background: "rgba(17, 24, 39, 0.92)",
              color: "#f8fafc",
              borderRadius: 14,
              padding: "10px 14px",
              fontWeight: 700,
              cursor: "pointer",
              boxShadow: "0 8px 24px rgba(0, 0, 0, 0.18)",
            }}
          >
            Profil: {activeItem.label} {isOpen ? "▴" : "▾"}
          </button>
          <span style={{ opacity: 0.75, fontSize: "0.95rem" }}>
            Atinge pentru navigare rapidă
          </span>
        </div>
      ) : null}

      {isCompact && isOpen ? (
        <div
          id="profile-nav-menu"
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 10,
            padding: 12,
            borderRadius: 16,
            border: "1px solid rgba(229, 231, 235, 0.12)",
            background: "rgba(15, 23, 42, 0.62)",
          }}
        >
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              label={item.label}
              isActive={path.startsWith(item.to)}
              onNavigate={() => setIsOpen(false)}
            />
          ))}
        </div>
      ) : null}

      {!isCompact ? (
        <div
          style={{
            display: "flex",
            gap: "10px",
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              label={item.label}
              isActive={path.startsWith(item.to)}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
