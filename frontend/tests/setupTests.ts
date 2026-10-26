import "@testing-library/jest-dom";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn((query) => ({ matches: false, media: query, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
});
window.HTMLElement.prototype.scrollIntoView = vi.fn();
window.scrollTo = vi.fn();
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
});
