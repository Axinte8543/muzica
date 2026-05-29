import { ui } from "../ui/ui.js";

export default function PaginationControls({
  page,
  totalPages,
  totalCount,
  onPrev,
  onNext,
  style,
}) {
  if (!totalPages || totalPages <= 1) return null;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        flexWrap: "wrap",
        marginTop: "16px",
        ...style,
      }}
    >
      <button
        type="button"
        style={ui.buttonSmall}
        onClick={onPrev}
        disabled={page <= 1}
      >
        Înapoi
      </button>

      <div style={{ opacity: 0.9 }}>
        Pagina {page} din {totalPages}
        {typeof totalCount === "number" ? ` • ${totalCount} total` : ""}
      </div>

      <button
        type="button"
        style={ui.buttonSmall}
        onClick={onNext}
        disabled={page >= totalPages}
      >
        Înainte
      </button>
    </div>
  );
}
