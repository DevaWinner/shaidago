import { renderToStaticMarkup } from "react-dom/server";

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
  Link,
  Modal,
  Pagination,
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

/** A word with no break opportunity: the worst case for a translated label or a long identifier. */
export const UNBROKEN = "Ìdánimọ̀àìmọ̀àwọnìwéẹ̀rítíakòtìíyẹ̀wòrárá-ìròyìnàṣírí-àìmọ̀";
export const LONG_LABEL =
  "Ọ̀nà àbáyọ tí a fọwọ́sí fún ìròyìn àṣírí tí kò ní ìdánimọ̀ àti àwọn ìwé ẹ̀rí tí a kò tíì yẹ̀wò";

const noop = () => undefined;
const row = { display: "flex", flexWrap: "wrap", gap: "0.75rem" } as const;

function PrimitiveSheet() {
  return (
    <main style={{ padding: "1rem", display: "grid", gap: "1rem" }}>
      <h1>Primitive sheet (test fixture, fictional text)</h1>
      <Field
        controlId="f1"
        description="Use neutral wording."
        label={LONG_LABEL}
        required
        requiredLabel="required"
      >
        <Textarea defaultValue={UNBROKEN} />
      </Field>
      <Field controlId="f2" error="Enter a name" label="Name">
        <Input />
      </Field>
      <Field controlId="f3" label="Read only">
        <Input defaultValue="kept" readOnly />
      </Field>
      <Field controlId="f4" label="Disabled">
        <Input defaultValue="inert" disabled />
      </Field>
      <Field controlId="f5" label="Area council">
        <Select>
          <option>{UNBROKEN}</option>
        </Select>
      </Field>
      <Field controlId="f6" label="Project">
        <Combobox name="project" options={["Clinic"]} />
      </Field>
      <Field controlId="f7" label="Attachments">
        <FilePicker multiple />
      </Field>
      <Checkbox description="Stays on this device only." label={LONG_LABEL} />
      <Radio label="Anonymous" name="mode" />
      <Switch label="Low-data mode" />
      <div style={row}>
        <Button>{LONG_LABEL}</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="danger">Delete</Button>
        <Button disabled>Disabled</Button>
        <IconButton label="Close notice">×</IconButton>
        <Link href="/">A plain link</Link>
        <Modal closeLabel="Close" description="d" title="t" triggerLabel="Open modal">
          <p>x</p>
        </Modal>
        <Sheet closeLabel="Close" description="d" title="t" triggerLabel="Open sheet">
          <p>x</p>
        </Sheet>
        <ConfirmDialog
          cancelLabel="Keep"
          confirmLabel="Delete"
          description="d"
          onConfirm={noop}
          title="t"
          triggerLabel="Confirm"
        />
      </div>
      <div style={row}>
        <StatusLabel tone="reviewed">Reviewed</StatusLabel>
        <StatusLabel tone="under-review">Under review</StatusLabel>
        <StatusLabel tone="limited-evidence">{LONG_LABEL}</StatusLabel>
        <StatusLabel tone="problem">Could not check</StatusLabel>
      </div>
      <Callout title={UNBROKEN} tone="warning">
        Read the source before sharing.
      </Callout>
      <Toast dismissLabel="Dismiss" onDismiss={noop} tone="danger">
        Upload failed
      </Toast>
      <Progress label="Upload preparation" value={40} valueText="40 percent" />
      <Skeleton label="Loading project records" />
      <Disclosure summary={LONG_LABEL}>Details.</Disclosure>
      <Pagination
        label="Project pages"
        next={{ href: "?cursor=opaque", label: "Next records" }}
        previous={{ href: "?", label: "Earlier records" }}
      />
    </main>
  );
}

export function primitiveSheetMarkup(): string {
  return renderToStaticMarkup(<PrimitiveSheet />);
}
