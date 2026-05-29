import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "../../src/App";

test("renders app shell and fallback", () => {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  );
  // Suspense fallback shows loading text
  expect(screen.getByText(/Se încarcă/i)).toBeInTheDocument();
});
