import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import NotFound from "../../app/not-found";
import RouteError from "../../app/error";
import GlobalError from "../../app/global-error";

describe("recovery boundaries", () => {
  it("keeps not-found responses generic about private records", () => {
    render(<NotFound />);

    expect(screen.getByRole("heading", { name: "This page is not available" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Return to ShaidaGo" })).toHaveAttribute("href", "/");
    expect(screen.getByText(/does not confirm whether a private record exists/i)).toBeVisible();
  });

  it("renders only an allowlisted request ID and never the raw error", async () => {
    const reset = vi.fn();
    const user = userEvent.setup();
    const error = Object.assign(new Error("postgres://private-host/secret"), {
      requestId: "A1000000-0000-7000-8000-000000000001"
    });

    render(<RouteError error={error} reset={reset} />);

    expect(
      screen.getByText("Support reference: a1000000-0000-7000-8000-000000000001")
    ).toBeVisible();
    expect(screen.queryByText(/private-host|secret/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(reset).toHaveBeenCalledOnce();
  });

  it("does not display an invalid request reference", () => {
    render(<RouteError error={new Error("internal failure")} reset={vi.fn()} />);

    expect(screen.queryByText(/^Support reference:/)).not.toBeInTheDocument();
  });

  it("keeps the root recovery boundary free of raw error values", () => {
    render(
      <GlobalError
        error={Object.assign(new Error("provider token: private-value"), {
          requestId: "a1000000-0000-7000-8000-000000000002"
        })}
        reset={vi.fn()}
      />
    );

    expect(screen.getByRole("heading", { name: "ShaidaGo could not be opened" })).toBeVisible();
    expect(screen.queryByText(/provider token|private-value/i)).not.toBeInTheDocument();
  });
});
