export const ui = {
  colors: {
    border: "var(--border-color)",
    mutedBg: "var(--muted-bg)",
    error: "var(--error-color)",
  },

  container: {
    padding: "24px",
  },

  card: {
    border: "1px solid var(--border-color)",
    borderRadius: "18px",
    padding: "16px",
    backgroundColor: "var(--surface-color)",
    boxShadow: "var(--shadow-card)",
    backdropFilter: "blur(16px)",
  },

  input: {
    padding: "10px 12px",
    border: "1px solid var(--border-color)",
    borderRadius: "12px",
    backgroundColor: "var(--input-bg)",
    color: "var(--text-color)",
    boxShadow: "var(--shadow-soft)",
  },

  button: {
    padding: "9px 14px",
    border: "1px solid var(--border-color)",
    borderRadius: "12px",
    cursor: "pointer",
    backgroundColor: "var(--button-bg)",
    color: "var(--text-color)",
    boxShadow: "var(--shadow-soft)",
  },

  buttonSmall: {
    padding: "7px 12px",
    border: "1px solid var(--border-color)",
    borderRadius: "10px",
    cursor: "pointer",
    backgroundColor: "var(--button-bg)",
    color: "var(--text-color)",
    boxShadow: "var(--shadow-soft)",
  },

  // Mobile-friendly action button (min 44px tap target)
  actionButton: {
    padding: "12px 16px",
    minHeight: "44px",
    minWidth: "44px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    border: "1px solid var(--border-color)",
    borderRadius: "10px",
    cursor: "pointer",
    backgroundColor: "transparent",
    color: "var(--text-color)",
    fontSize: "14px",
    transition: "all 0.2s ease",
    touchAction: "manipulation",
  },

  // Compact spacing for crowded areas
  spacing: {
    xs: "4px",
    sm: "8px",
    md: "12px",
    lg: "16px",
    xl: "24px",
  },

  // Mobile-first responsive utilities
  responsive: {
    mobileOnly: "@media (max-width: 640px)",
    tablet: "@media (min-width: 641px) and (max-width: 1024px)",
    desktop: "@media (min-width: 1025px)",
  },

  // Common mobile-first patterns
  mobileGrid: {
    display: "grid",
    gridTemplateColumns: "1fr",
    gap: "12px",
    "@media (min-width: 641px)": {
      gridTemplateColumns: "repeat(2, 1fr)",
      gap: "16px",
    },
    "@media (min-width: 1025px)": {
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: "16px",
    },
  },

  errorText: {
    color: "var(--error-color)",
  },
};
