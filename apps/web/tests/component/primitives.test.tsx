import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  Button,
  Callout,
  Checkbox,
  Combobox,
  Disclosure,
  Field,
  IconButton,
  Input,
  Pagination,
  Progress,
  Radio,
  Select,
  Skeleton,
  StatusLabel,
  Switch,
  Textarea
} from "@/components/primitives/primitives";

describe("project-owned primitives", () => {
  it("keeps labelled form controls, errors, and read-only state semantic", () => {
    render(
      <>
        <Field controlId="public-update" error="Enter a neutral update" label="Public update">
          <Textarea aria-invalid="true" id="public-update" readOnly />
        </Field>
        <Field controlId="area-council" label="Area council">
          <Select id="area-council">
            <option>AMAC</option>
          </Select>
        </Field>
        <Combobox
          aria-label="Project"
          name="project"
          options={["Long source-backed project name"]}
        />
        <Checkbox aria-label="Agree" />
        <Radio aria-label="Option" name="option" />
        <Switch aria-label="Low-data mode" />
      </>
    );
    expect(screen.getByLabelText("Public update")).toHaveAttribute("readonly");
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a neutral update");
    expect(screen.getByRole("combobox", { name: "Project" })).toBeVisible();
    expect(screen.getByRole("switch", { name: "Low-data mode" })).toBeVisible();
  });

  it("exposes explicit names, state text, progress, and pagination actions", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    render(
      <>
        <Button>Continue</Button>
        <IconButton label="Close notice">×</IconButton>
        <StatusLabel tone="under-review">Under review</StatusLabel>
        <Callout title="Limited evidence">Read the source before sharing.</Callout>
        <Progress label="Upload preparation" value={40} />
        <Skeleton />
        <Pagination currentPage={2} onPageChange={onPageChange} pageCount={3} />
      </>
    );
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(onPageChange).toHaveBeenCalledWith(3);
    expect(screen.getByRole("button", { name: "Close notice" })).toBeVisible();
    expect(screen.getByText("Under review")).toBeVisible();
    expect(screen.getByRole("progressbar", { name: "Upload preparation" })).toHaveValue(40);
    expect(screen.getByRole("status", { name: "Loading content" })).toBeVisible();
  });

  it("keeps disclosures keyboard-operable without JavaScript-only content", async () => {
    const user = userEvent.setup();
    render(
      <Disclosure summary="Why is this source limited?">
        The reviewer has not approved it.
      </Disclosure>
    );
    const summary = screen.getByText("Why is this source limited?");
    await user.click(summary);
    expect(screen.getByText("The reviewer has not approved it.")).toBeVisible();
  });
});
