import SimilarUsers from "../components/SimilarUsers.jsx";
import { ui } from "../ui/ui.js";

export default function SimilarUsersPage() {
  return (
    <div style={ui.container}>
      <h1 style={{ marginTop: 0 }}>Utilizatori cu gusturi similare</h1>
      <SimilarUsers />
    </div>
  );
}
