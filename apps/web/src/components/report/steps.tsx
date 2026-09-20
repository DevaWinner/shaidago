"use client";

import { useState, type ChangeEvent, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/feedback";
import { IDS, errorMessage, type Copy } from "@/components/report/shared";
import { Checkbox, Radio } from "@/components/ui/choice";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { formatMessageLite } from "@/lib/directory/format-lite";
import type { PrepareFailure } from "@/lib/report/image-prep";
import {
  CATEGORIES,
  CHANNELS,
  LIMITS,
  type IdentityMode,
  type ReportForm,
  type StepError
} from "@/lib/report/flow";

function errorFor(errors: readonly StepError[], field: StepError["field"], copy: Copy) {
  const found = errors.find((error) => error.field === field);

  return found === undefined ? undefined : errorMessage(copy, found.key);
}

export function ObservationStep({
  copy,
  errors,
  form,
  onChange
}: Readonly<{
  copy: Copy;
  errors: readonly StepError[];
  form: ReportForm;
  onChange: (patch: Partial<ReportForm>) => void;
}>): ReactNode {
  const text = copy.observation;

  return (
    <div className="grid gap-5">
      <Field
        controlId={IDS.category}
        error={errorFor(errors, "category", copy)}
        label={text.categoryLabel}
        required
      >
        <Select
          onChange={(event: ChangeEvent<HTMLSelectElement>) =>
            onChange({ category: event.target.value as ReportForm["category"] })
          }
          value={form.category}
        >
          <option value="">{text.categoryPlaceholder}</option>
          {CATEGORIES.map((value) => (
            <option key={value} value={value}>
              {text.categories[value]}
            </option>
          ))}
        </Select>
      </Field>
      <Field
        controlId={IDS.description}
        description={`${formatMessageLite(text.descriptionHint, {
          min: LIMITS.descriptionMin,
          max: LIMITS.descriptionMax
        })} ${formatMessageLite(text.counter, {
          count: form.description.length,
          max: LIMITS.descriptionMax
        })}`}
        error={errorFor(errors, "description", copy)}
        label={text.descriptionLabel}
        required
      >
        <Textarea
          autoComplete="off"
          maxLength={LIMITS.descriptionMax}
          onChange={(event) => onChange({ description: event.target.value })}
          rows={8}
          value={form.description}
        />
      </Field>
    </div>
  );
}

export type FileView = Readonly<{
  id: number;
  kind: "image" | "pdf";
  cleaned: boolean;
  url: string | null;
  sizeLabel: string;
}>;

export type FileNote = Readonly<{ reason: PrepareFailure | "tooMany"; number: number }>;

export function EvidenceStep({
  copy,
  files,
  notes,
  onAdd,
  onRemove,
  preparing
}: Readonly<{
  copy: Copy;
  files: readonly FileView[];
  notes: readonly FileNote[];
  onAdd: (list: FileList) => void;
  onRemove: (id: number) => void;
  preparing: number;
}>): ReactNode {
  const text = copy.evidence;
  const megabytes = LIMITS.fileBytes / (1024 * 1024);
  const full = files.length >= LIMITS.files;

  return (
    <div className="grid gap-4">
      <p className="m-0 max-w-[68ch]">{text.lead}</p>
      <Callout title={text.heading} tone="information">
        {text.role}
      </Callout>
      <Field
        controlId="report-files"
        description={formatMessageLite(text.hint, { max: LIMITS.files, size: megabytes })}
        label={text.pick}
      >
        <input
          accept="image/jpeg,image/png,image/webp,application/pdf"
          aria-disabled={full}
          className="box-border min-h-11 w-full min-w-0 max-w-full rounded-ledger-control border border-border bg-card px-3 py-2"
          data-slot="input"
          disabled={full}
          id="report-files"
          multiple
          onChange={(event) => {
            if (event.target.files !== null && event.target.files.length > 0) {
              onAdd(event.target.files);
            }
            // The same file can be chosen again after it is removed.
            event.target.value = "";
          }}
          type="file"
        />
      </Field>
      {notes.length === 0 ? null : (
        <ul className="m-0 grid list-none gap-1 p-0 text-destructive" role="alert">
          {notes.map((note) => (
            <li key={`${note.reason}-${note.number}`}>
              {formatMessageLite(
                note.reason === "tooMany" ? text.errors.tooMany : text.errors[note.reason],
                { number: note.number, size: megabytes, max: LIMITS.files }
              )}
            </li>
          ))}
        </ul>
      )}
      {preparing > 0 ? (
        <p className="m-0" role="status">
          {formatMessageLite(text.preparing, { number: files.length + 1 })}
        </p>
      ) : null}
      {files.length === 0 ? (
        <p className="m-0 text-muted-foreground">{text.none}</p>
      ) : (
        <ol className="m-0 grid list-none gap-3 p-0">
          {files.map((file, index) => (
            <li className="grid gap-2 border border-border bg-card p-3" key={file.id}>
              <div className="flex flex-wrap items-center gap-3">
                {file.url === null ? (
                  <span className="text-sm text-muted-foreground">{text.previewNone}</span>
                ) : (
                  // A preview of the sanitised copy, a local object URL that is revoked on removal.
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    alt={formatMessageLite(text.preview, { number: index + 1 })}
                    className="max-h-32 max-w-full object-contain"
                    height={128}
                    src={file.url}
                    width={128}
                  />
                )}
                <span className="text-sm">{file.sizeLabel}</span>
              </div>
              <p className="m-0 text-sm text-muted-foreground">
                {file.cleaned ? text.prepared : text.pdfNotPrepared}
              </p>
              <div>
                <Button onClick={() => onRemove(file.id)} variant="secondary">
                  {formatMessageLite(text.remove, { number: index + 1 })}
                </Button>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export function AnonymityStep({
  copy,
  errors,
  form,
  handleHref,
  onChange,
  onMode
}: Readonly<{
  copy: Copy;
  errors: readonly StepError[];
  form: ReportForm;
  handleHref: string;
  onChange: (patch: Partial<ReportForm>) => void;
  onMode: (mode: IdentityMode) => void;
}>): ReactNode {
  const text = copy.anonymity;
  const [reveal, setReveal] = useState(false);
  const modes: readonly IdentityMode[] = ["anonymous", "contact", "handle"];

  return (
    <div className="grid gap-4">
      <p className="m-0 max-w-[68ch]">{text.lead}</p>
      <fieldset className="m-0 grid gap-1 border-0 p-0">
        <legend className="mb-1 font-semibold">{copy.steps.anonymity}</legend>
        {modes.map((mode) => (
          <Radio
            checked={form.mode === mode}
            description={text.modes[mode].body}
            key={mode}
            label={text.modes[mode].label}
            name="report-identity"
            onChange={() => onMode(mode)}
            value={mode}
          />
        ))}
      </fieldset>
      {form.mode === "contact" ? (
        <div className="grid gap-4">
          <Field
            controlId={IDS.contactChannel}
            error={errorFor(errors, "contactChannel", copy)}
            label={text.channelLabel}
            required
          >
            <Select
              onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                onChange({ contactChannel: event.target.value as ReportForm["contactChannel"] })
              }
              value={form.contactChannel}
            >
              <option value="">{text.channelLabel}</option>
              {CHANNELS.map((value) => (
                <option key={value} value={value}>
                  {text.channels[value]}
                </option>
              ))}
            </Select>
          </Field>
          <Field
            controlId={IDS.contactValue}
            description={text.contactHint}
            error={errorFor(errors, "contactValue", copy)}
            label={text.contactLabel}
            required
          >
            <Input
              autoComplete="off"
              maxLength={LIMITS.contactMax}
              onChange={(event) => onChange({ contactValue: event.target.value })}
              value={form.contactValue}
            />
          </Field>
        </div>
      ) : null}
      {form.mode === "handle" ? (
        <div className="grid gap-4">
          <Callout title={text.modes.handle.label} tone="warning">
            {text.modes.handle.warning}
          </Callout>
          <Field
            controlId={IDS.handle}
            error={errorFor(errors, "handle", copy)}
            label={text.handleLabel}
            required
          >
            <Input
              autoCapitalize="off"
              autoComplete="off"
              maxLength={LIMITS.handleMax}
              onChange={(event) => onChange({ handle: event.target.value })}
              spellCheck={false}
              value={form.handle}
            />
          </Field>
          <Field
            controlId={IDS.passphrase}
            description={text.handleNote}
            error={errorFor(errors, "passphrase", copy)}
            label={text.passphraseLabel}
            required
          >
            <Input
              autoCapitalize="off"
              autoComplete="off"
              maxLength={LIMITS.passphraseMax}
              onChange={(event) => onChange({ passphrase: event.target.value })}
              spellCheck={false}
              type={reveal ? "text" : "password"}
              value={form.passphrase}
            />
          </Field>
          <div>
            <Button
              aria-pressed={reveal}
              onClick={() => setReveal((value) => !value)}
              variant="secondary"
            >
              {reveal ? text.hide : text.reveal}
            </Button>
          </div>
          <p className="m-0">
            <a className="font-semibold text-ledger-accent-strong underline" href={handleHref}>
              {text.createHandle}
            </a>
          </p>
        </div>
      ) : null}
    </div>
  );
}

export function ReviewStep({
  copy,
  fileCount,
  form,
  onChange
}: Readonly<{
  copy: Copy;
  fileCount: number;
  form: ReportForm;
  /** Jumps to the step that owns a row, so a mistake is one action away. */
  onChange: (step: "observation" | "evidence" | "anonymity") => void;
}>): ReactNode {
  const text = copy.review;
  const identity =
    form.mode === "anonymous"
      ? text.identity.anonymous
      : form.mode === "contact"
        ? formatMessageLite(text.identity.contact, {
            channel: form.contactChannel === "" ? "" : copy.anonymity.channels[form.contactChannel]
          })
        : formatMessageLite(text.identity.handle, { handle: form.handle.trim() });
  const rows: readonly (readonly [string, ReactNode, "observation" | "evidence" | "anonymity"])[] =
    [
      [
        text.rows.concern,
        form.category === "" ? "" : copy.observation.categories[form.category],
        "observation"
      ],
      [
        text.rows.description,
        <span className="whitespace-pre-wrap" key="d">
          {form.description.trim()}
        </span>,
        "observation"
      ],
      [
        text.rows.files,
        fileCount === 0 ? text.noFiles : formatMessageLite(text.files, { count: fileCount }),
        "evidence"
      ],
      [text.rows.identity, identity, "anonymity"]
    ];

  return (
    <div className="grid gap-4">
      <p className="m-0 max-w-[68ch]">{text.lead}</p>
      <dl className="m-0 grid gap-3">
        {rows.map(([label, value, step]) => (
          <div className="grid gap-1 border border-border bg-card p-3" key={label}>
            <dt className="text-sm text-muted-foreground">{label}</dt>
            <dd className="m-0 font-semibold [overflow-wrap:anywhere]">{value}</dd>
            <dd className="m-0">
              <Button onClick={() => onChange(step)} variant="secondary">
                {text.change}
                <span className="sr-only">{label}</span>
              </Button>
            </dd>
          </div>
        ))}
      </dl>
      <p className="m-0 max-w-[68ch]">{text.sendNote}</p>
    </div>
  );
}

export function DraftConsent({
  canSave,
  consent,
  copy,
  note,
  onConsent,
  onRemove
}: Readonly<{
  canSave: boolean;
  consent: boolean;
  copy: Copy;
  note: "none" | "removed" | "restored" | "unavailable";
  onConsent: (on: boolean) => void;
  onRemove: () => void;
}>): ReactNode {
  return (
    <fieldset className="m-0 grid gap-2 border border-border p-3">
      <legend className="px-1 font-semibold">{copy.draft.heading}</legend>
      <Checkbox
        checked={consent}
        description={copy.draft.warning}
        disabled={!canSave && !consent}
        label={copy.draft.consent}
        onChange={(event) => onConsent(event.target.checked)}
      />
      {consent ? (
        <div>
          <Button onClick={onRemove} variant="secondary">
            {copy.draft.remove}
          </Button>
        </div>
      ) : null}
      {note === "removed" ? <p className="m-0 text-sm">{copy.draft.removed}</p> : null}
      {note === "restored" ? <p className="m-0 text-sm">{copy.draft.restored}</p> : null}
      {note === "unavailable" ? <p className="m-0 text-sm">{copy.draft.unavailable}</p> : null}
    </fieldset>
  );
}
