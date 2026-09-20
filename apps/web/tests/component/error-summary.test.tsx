import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ErrorSummary } from "@/components/ui/error-summary";
import { Field, Input, Textarea } from "@/components/ui/field";

function Form({ errors }: Readonly<{ errors: boolean }>) {
  return (
    <form>
      <ErrorSummary
        extra={errors ? ["The service is unavailable right now."] : []}
        items={
          errors
            ? [
                { controlId: "description", message: "This is too short." },
                { controlId: "slug", message: "Enter a value." }
              ]
            : []
        }
        title="Fix 3 problems to continue"
      />
      <Field
        controlId="description"
        error={errors ? "This is too short." : undefined}
        label="Description"
      >
        <Textarea defaultValue="kept text" />
      </Field>
      <Field controlId="slug" error={errors ? "Enter a value." : undefined} label="Project">
        <Input />
      </Field>
    </form>
  );
}

describe("error summary", () => {
  it("renders nothing when there are no problems", () => {
    const { container } = render(<Form errors={false} />);

    expect(container.querySelector("[data-slot=error-summary]")).toBeNull();
  });

  it("takes focus when errors appear, states the count, and lists every message", () => {
    const { container, rerender } = render(<Form errors={false} />);
    rerender(<Form errors />);

    const heading = screen.getByRole("heading", { name: "Fix 3 problems to continue" });

    expect(heading).toHaveFocus();
    // The summary is a live alert region in its own right (each field error is one too).
    expect(container.querySelector("[data-slot=error-summary]")).toHaveAttribute("role", "alert");
    expect(screen.getAllByRole("link")).toHaveLength(2);
    expect(screen.getByText("The service is unavailable right now.")).toBeVisible();
  });

  it("moves focus to the linked field, which keeps its entered value and is programmatically invalid", async () => {
    const user = userEvent.setup();
    render(<Form errors />);

    await user.click(screen.getByRole("link", { name: "This is too short." }));

    const field = screen.getByLabelText("Description");
    expect(field).toHaveFocus();
    expect(field).toHaveValue("kept text");
    expect(field).toBeInvalid();
    expect(field).toHaveAccessibleDescription("This is too short.");
  });

  it("supports keyboard activation of a summary link", async () => {
    const user = userEvent.setup();
    render(<Form errors />);

    await user.tab();
    await user.tab();
    await user.keyboard("{Enter}");

    expect(screen.getByLabelText("Project")).toHaveFocus();
  });
});
