import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  Button,
  Callout,
  Checkbox,
  Combobox,
  ConfirmDialog,
  Disclosure,
  Field,
  FilePicker,
  IconButton,
  Input,
  LiveRegion,
  Modal,
  Pagination,
  PopoverCard,
  Progress,
  Radio,
  Select,
  Sheet,
  Skeleton,
  StatusLabel,
  Switch,
  Textarea,
  Toast
} from "@/components/primitives/primitives";

const longLabel =
  "Ọ̀nà àbáyọ tí a fọwọ́sí fún ìròyìn àṣírí tí kò ní ìdánimọ̀ àti àwọn ìwé ẹ̀rí tí a kò tíì yẹ̀wò";

describe("form fields", () => {
  it("wires the label, description, error, and required state to the control", () => {
    render(
      <Field
        controlId="update"
        description="Use neutral wording."
        error="Enter a neutral update"
        label="Public update"
        required
        requiredLabel="required"
      >
        <Textarea />
      </Field>
    );

    const control = screen.getByRole("textbox", { name: /Public update/ });

    expect(screen.getByRole("textbox", { name: "Public update (required)" })).toBe(control);
    expect(control).toBeRequired();
    expect(control).toBeInvalid();
    expect(control).toHaveAccessibleDescription("Use neutral wording. Enter a neutral update");
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a neutral update");
    expect(control).toHaveAttribute("id", "update");
  });

  it("applies the same wiring to input, select, combobox, and file picker", () => {
    render(
      <>
        <Field controlId="a" description="Hint A" label="Name">
          <Input />
        </Field>
        <Field controlId="b" error="Pick one" label="Council">
          <Select>
            <option>AMAC</option>
          </Select>
        </Field>
        <Field controlId="c" description="Type to filter" label="Project">
          <Combobox name="project" options={["Clinic", "School"]} />
        </Field>
        <Field controlId="d" description="Up to three files" label="Attachments">
          <FilePicker multiple />
        </Field>
      </>
    );

    expect(screen.getByRole("textbox", { name: "Name" })).toHaveAccessibleDescription("Hint A");
    expect(screen.getByRole("combobox", { name: "Council" })).toBeInvalid();
    expect(screen.getByRole("combobox", { name: "Project" })).toHaveAccessibleDescription(
      "Type to filter"
    );
    expect(screen.getByLabelText("Attachments")).toHaveAccessibleDescription("Up to three files");
  });

  it("keeps an explicit description and merges it with the field's", () => {
    render(
      <Field controlId="x" description="From field" label="Label">
        <Input aria-describedby="extra" />
      </Field>
    );
    expect(document.getElementById("x")?.getAttribute("aria-describedby")).toBe(
      "extra x-description"
    );
  });

  it("distinguishes read-only (focusable, selectable) from disabled (inert)", async () => {
    const user = userEvent.setup();
    render(
      <>
        <Field controlId="ro" label="Read only">
          <Input defaultValue="kept" readOnly />
        </Field>
        <Field controlId="off" label="Disabled">
          <Input defaultValue="inert" disabled />
        </Field>
      </>
    );

    await user.tab();
    expect(screen.getByLabelText("Read only")).toHaveFocus();
    expect(screen.getByLabelText("Read only")).toHaveValue("kept");
    await user.tab();
    expect(screen.getByLabelText("Disabled")).toBeDisabled();
    expect(screen.getByLabelText("Disabled")).not.toHaveFocus();
  });

  it("gives choices a label-sized target, a role, and an associated description", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <>
        <Checkbox
          description="Stays on this device only."
          label="Save a draft"
          onChange={onChange}
        />
        <Radio label="Anonymous" name="mode" />
        <Switch label="Low-data mode" />
      </>
    );

    const checkbox = screen.getByRole("checkbox", { name: /Save a draft/ });
    expect(checkbox).toHaveAccessibleDescription("Stays on this device only.");
    await user.click(screen.getByText("Save a draft"));
    expect(onChange).toHaveBeenCalledOnce();
    expect(checkbox).toBeChecked();
    expect(screen.getByRole("radio", { name: "Anonymous" })).toBeVisible();
    const toggle = screen.getByRole("switch", { name: "Low-data mode" });
    toggle.focus();
    await user.keyboard(" ");
    expect(toggle).toBeChecked();
  });

  it("carries long translated labels without truncating them", () => {
    render(
      <>
        <Field controlId="long" label={longLabel}>
          <Input />
        </Field>
        <Checkbox label={longLabel} />
        <Button>{longLabel}</Button>
      </>
    );
    expect(screen.getByRole("textbox", { name: longLabel })).toBeVisible();
    expect(screen.getByRole("checkbox", { name: longLabel })).toBeVisible();
    expect(screen.getByRole("button", { name: longLabel })).toBeVisible();
  });
});

describe("actions", () => {
  it("activates a button by keyboard and names an icon button without its glyph", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <>
        <Button onClick={onClick} variant="danger">
          Delete draft
        </Button>
        <IconButton label="Close notice">×</IconButton>
      </>
    );

    await user.tab();
    await user.keyboard("{Enter}");
    await user.keyboard(" ");
    expect(onClick).toHaveBeenCalledTimes(2);
    const icon = screen.getByRole("button", { name: "Close notice" });
    expect(icon).toHaveAccessibleName("Close notice");
    expect(within(icon).getByText("×")).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByRole("button", { name: "Delete draft" })).toHaveClass(
      "primitive-button--danger"
    );
  });

  it("does not activate a disabled button", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Send
      </Button>
    );
    await user.click(screen.getByRole("button", { name: "Send" }));
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe("status, notices, progress, and loading", () => {
  it("states status in words with a decorative shape, and notices as notes", () => {
    render(
      <>
        <StatusLabel tone="under-review">Under review</StatusLabel>
        <StatusLabel tone="problem">Could not check</StatusLabel>
        <Callout title="Limited evidence" tone="warning">
          Read the source before sharing.
        </Callout>
        <Progress label="Upload preparation" value={40} valueText="40 percent" />
        <Skeleton label="Loading project records" />
        <LiveRegion>Saved</LiveRegion>
        <LiveRegion politeness="assertive">Failed</LiveRegion>
      </>
    );

    expect(screen.getByText("Under review")).toBeVisible();
    expect(screen.getByText("Under review").querySelector("[aria-hidden='true']")).not.toBeNull();
    expect(screen.getByRole("note")).toHaveTextContent("Limited evidence");
    expect(screen.getByRole("progressbar", { name: "Upload preparation" })).toHaveValue(40);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuetext", "40 percent");
    expect(screen.getAllByRole("status")).toHaveLength(2);
    expect(screen.getByText("Loading project records")).toBeVisible();
    expect(screen.getByText("Failed").closest("[role='alert']")).not.toBeNull();
  });

  it("keeps disclosures operable and toasts dismissible", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    render(
      <>
        <Disclosure summary="Why is this source limited?">
          The reviewer has not approved it.
        </Disclosure>
        <Toast dismissLabel="Dismiss message" onDismiss={onDismiss} tone="danger">
          Upload failed
        </Toast>
        <Toast dismissLabel="Dismiss saved" onDismiss={onDismiss}>
          Saved
        </Toast>
      </>
    );

    await user.click(screen.getByText("Why is this source limited?"));
    expect(screen.getByText("The reviewer has not approved it.")).toBeVisible();
    expect(screen.getByRole("alert")).toHaveTextContent("Upload failed");
    await user.click(screen.getByRole("button", { name: "Dismiss message" }));
    expect(onDismiss).toHaveBeenCalledOnce();
    expect(screen.getByText("Saved").closest("[role='status']")).not.toBeNull();
  });
});

describe("pagination", () => {
  it("offers only the links that exist, as plain URL-owned navigation", () => {
    const { rerender } = render(
      <Pagination label="Project pages" next={{ href: "?cursor=opaque", label: "Next records" }} />
    );
    const nav = screen.getByRole("navigation", { name: "Project pages" });
    expect(within(nav).getAllByRole("link")).toHaveLength(1);
    expect(within(nav).getByRole("link", { name: "Next records" })).toHaveAttribute(
      "href",
      "?cursor=opaque"
    );
    expect(within(nav).getByRole("link")).toHaveAttribute("rel", "next");

    rerender(
      <Pagination label="Project pages" previous={{ href: "?", label: "Earlier records" }} />
    );
    expect(screen.getByRole("link", { name: "Earlier records" })).toHaveAttribute("rel", "prev");
  });
});

describe("overlays and focus restoration", () => {
  it("opens a modal from its trigger, names it, and returns focus on Escape and Close", async () => {
    const user = userEvent.setup();
    render(
      <Modal
        closeLabel="Close"
        description="Nothing is saved to your device."
        title="Shared device warning"
        triggerLabel="Read the warning"
      >
        <p>Use a private browser window.</p>
      </Modal>
    );

    const trigger = screen.getByRole("button", { name: "Read the warning" });
    await user.click(trigger);
    const dialog = await screen.findByRole("dialog", { name: "Shared device warning" });
    expect(dialog).toHaveAccessibleDescription("Nothing is saved to your device.");

    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(trigger).toHaveFocus();

    await user.click(trigger);
    await user.click(await screen.findByRole("button", { name: "Close" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(trigger).toHaveFocus();
  });

  it("supports a sheet placement with the same dialog semantics", async () => {
    const user = userEvent.setup();
    render(
      <Sheet
        closeLabel="Done"
        description="Filter by locality."
        title="Filters"
        triggerLabel="Filters"
      >
        <p>Body</p>
      </Sheet>
    );
    await user.click(screen.getByRole("button", { name: "Filters" }));
    const dialog = await screen.findByRole("dialog", { name: "Filters" });
    expect(dialog).toHaveClass("primitive-overlay--sheet");
  });

  it("never confirms on cancel, Escape, or dismissal, and confirms exactly once", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        cancelLabel="Keep draft"
        confirmLabel="Delete draft"
        description="This removes the draft from this device."
        destructive
        onConfirm={onConfirm}
        title="Delete draft?"
        triggerLabel="Delete"
      />
    );

    const trigger = screen.getByRole("button", { name: "Delete" });
    await user.click(trigger);
    expect(await screen.findByRole("alertdialog", { name: "Delete draft?" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Keep draft" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(trigger).toHaveFocus();

    await user.click(trigger);
    await screen.findByRole("alertdialog");
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(onConfirm).not.toHaveBeenCalled();

    await user.click(trigger);
    await user.click(await screen.findByRole("button", { name: "Delete draft" }));
    expect(onConfirm).toHaveBeenCalledOnce();
    expect(screen.getByRole("button", { name: "Delete" })).toHaveClass("primitive-button");
  });

  it("opens a popover from its trigger and restores focus on Escape", async () => {
    const user = userEvent.setup();
    render(<PopoverCard content={<p>Passage from the cited source.</p>} triggerLabel="Source" />);

    const trigger = screen.getByRole("button", { name: "Source" });
    await user.click(trigger);
    expect(await screen.findByText("Passage from the cited source.")).toBeVisible();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByText("Passage from the cited source.")).toBeNull());
    expect(trigger).toHaveFocus();
  });
});
