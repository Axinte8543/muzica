import { useContext } from "react";

import { NoticeContext } from "./NoticeContext.js";

export function useNotice() {
  const ctx = useContext(NoticeContext);
  if (!ctx) {
    throw new Error("useNotice must be used within NoticeProvider");
  }
  return ctx;
}
