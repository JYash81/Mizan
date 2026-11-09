import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, test } from "vitest";
import { App } from "./App";

test("renders the Mizan authentication screen when unauthenticated", async () => {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <App />
    </QueryClientProvider>
  );

  // Unauthenticated user is redirected to Login
  expect(await screen.findByText("Sign in to Mizan")).toBeInTheDocument();
  expect(screen.getByLabelText("Work Email")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Sign in/i })).toBeInTheDocument();
});
