/* global test, expect */

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "../../src/App";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

test("renders app shell and fallback", () => {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>
      <App />
    </MemoryRouter></QueryClientProvider>,
  );
  // Suspense fallback shows loading text
  expect(screen.getByText(/Se încarcă/i)).toBeInTheDocument();
});
