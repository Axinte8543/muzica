import { Link, useLocation } from "react-router-dom";

function NavLink({ to, label, isActive }) {
  return (
    <Link
      to={to}
      style={{
        textDecoration: isActive ? "underline" : "none",
        fontWeight: isActive ? 700 : 400,
      }}
    >
      {label}
    </Link>
  );
}

export default function ProfileNav() {
  const location = useLocation();
  const path = location.pathname || "";

  return (
    <div
      style={{
        padding: "12px 24px",
        borderBottom: "1px solid #e5e7eb",
        display: "flex",
        gap: "12px",
        alignItems: "center",
      }}
    >
      <NavLink
        to="/profile/listens"
        label="Listens"
        isActive={path.startsWith("/profile/listens")}
      />
      <NavLink
        to="/profile/want-to-listen"
        label="Want To Listen"
        isActive={path.startsWith("/profile/want-to-listen")}
      />
      <NavLink
        to="/profile/challenges/weekly"
        label="Provocări"
        isActive={path.startsWith("/profile/challenges/weekly")}
      />
      <NavLink
        to="/profile/badges"
        label="Insigne"
        isActive={path.startsWith("/profile/badges")}
      />
      <NavLink
        to="/profile/achievements"
        label="Realizări"
        isActive={path.startsWith("/profile/achievements")}
      />
      <NavLink
        to="/profile/reviews"
        label="Reviews"
        isActive={path.startsWith("/profile/reviews")}
      />
      <NavLink
        to="/profile/lists"
        label="Lists"
        isActive={path.startsWith("/profile/lists")}
      />
      <NavLink
        to="/profile/following"
        label="Following"
        isActive={path.startsWith("/profile/following")}
      />
      <NavLink
        to="/profile/ratings"
        label="Ratings"
        isActive={path.startsWith("/profile/ratings")}
      />
      <NavLink
        to="/profile/liked-albums"
        label="Liked Albums"
        isActive={path.startsWith("/profile/liked-albums")}
      />
      <NavLink
        to="/profile/friends"
        label="Friends"
        isActive={path.startsWith("/profile/friends")}
      />
      <NavLink
        to="/profile/stats"
        label="Stats"
        isActive={path.startsWith("/profile/stats")}
      />
      <NavLink
        to="/profile/top"
        label="Top-ul meu"
        isActive={path.startsWith("/profile/top")}
      />
      <NavLink
        to="/profile/suggestions"
        label="Sugestiile mele"
        isActive={path.startsWith("/profile/suggestions")}
      />
      <NavLink
        to="/profile/privacy"
        label="Confidențialitate"
        isActive={path.startsWith("/profile/privacy")}
      />
      <NavLink
        to="/profile/export"
        label="Export Date"
        isActive={path.startsWith("/profile/export")}
      />
      <NavLink
        to="/profile/metadata-suggestions"
        label="Corecturi sugerate"
        isActive={path.startsWith("/profile/metadata-suggestions")}
      />
    </div>
  );
}
