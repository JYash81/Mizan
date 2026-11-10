import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, test } from "vitest";
import { App } from "./App";

test("renders the Mizan enterprise homepage with brand positioning and signin/signup options", async () => {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <App />
    </QueryClientProvider>
  );

  // Verifies Enterprise Hero headline and core positioning
  expect(
    await screen.findByRole("heading", { name: /Build AI with evidence/i }, { timeout: 8000 })
  ).toBeInTheDocument();

  // Verifies Sign In and Sign Up options exist on homepage
  const signInLinks = screen.getAllByRole("link", { name: /Sign In/i });
  expect(signInLinks.length).toBeGreaterThan(0);

  const signUpLinks = screen.getAllByRole("link", { name: /Sign Up|Create an organization account/i });
  expect(signUpLinks.length).toBeGreaterThan(0);

  // Verifies Request a Pilot CTAs exist
  const pilotButtons = screen.getAllByRole("button", { name: /Request a Pilot|Request Pilot/i });
  expect(pilotButtons.length).toBeGreaterThan(0);

  // Verifies key sections exist using accessible headings
  expect(screen.getByRole("heading", { name: /AI adoption is accelerating/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /One platform/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /From data readiness/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /Trust should be part of the architecture/i })).toBeInTheDocument();
}, 15000);

test("navigates to authentication screen when clicking Sign In", async () => {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <App />
    </QueryClientProvider>
  );

  const signInLink = screen.getAllByRole("link", { name: /Sign In/i })[0];
  fireEvent.click(signInLink);

  expect(await screen.findByText("Sign in to Mizan", {}, { timeout: 8000 })).toBeInTheDocument();
  expect(screen.getByLabelText("Work Email")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Sign in/i })).toBeInTheDocument();
}, 15000);
