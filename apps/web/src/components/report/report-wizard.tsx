"use client";

import type { Route } from "next";
import { useRouter } from "next/navigation";
import {
  Suspense,
  lazy,
  useEffect,
  useId,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode
} from "react";

import { NoticeStep } from "@/components/report/notice-step";
import { IDS, errorMessage } from "@/components/report/shared";
import type { FileNote, FileView } from "@/components/report/steps";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/feedback";
import { ErrorSummary } from "@/components/ui/error-summary";
import type { Messages } from "@/i18n/catalogue";
import { setUnsavedDraft } from "@/lib/draft-guard";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { createFormatters } from "@/lib/format/formatters";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import { describeProblem, mapFieldErrors, type SafeProblem } from "@/lib/problems/problem-messages";
import {
  clearDraft,
  draftStorageAvailable,
  parseDraft,
  readRawDraft,
  saveDraft,
  subscribeToDraft
} from "@/lib/report/draft";
import {
  EMPTY_FORM,
  LIMITS,
  STEPS,
  firstInvalidStep,
  hasContent,
  nextStep,
  previousStep,
  stepForApiField,
  stepIndex,
  validateStep,
  withMode,
  type ReportForm,
  type Step,
  type StepError
} from "@/lib/report/flow";
import type { PreparedFile } from "@/lib/report/image-prep";
import { setReceipt } from "@/lib/report/receipt-store";

// The later steps load on demand: the first screen is only the notice, and the first-load
// JavaScript budget of a public page is small.
const steps = () => import("@/components/report/steps");
const ObservationStep = lazy(() => steps().then((m) => ({ default: m.ObservationStep })));
const EvidenceStep = lazy(() => steps().then((m) => ({ default: m.EvidenceStep })));
const AnonymityStep = lazy(() => steps().then((m) => ({ default: m.AnonymityStep })));
const DraftConsent = lazy(() => steps().then((m) => ({ default: m.DraftConsent })));
const ReviewStep = lazy(() => steps().then((m) => ({ default: m.ReviewStep })));

type Held = Readonly<{ id: number; prepared: PreparedFile; url: string | null }>;

type Sending =
  | Readonly<{ phase: "idle" }>
  | Readonly<{ phase: "sending"; progress: number }>
  | Readonly<{ phase: "cancelled" }>
  | Readonly<{ phase: "offline" }>
  | Readonly<{ phase: "unknown" }>
  | Readonly<{ phase: "problem"; problem: SafeProblem }>;

type ServerErrors = Readonly<{
  step: Step;
  items: readonly { controlId: string; message: string }[];
  extra: readonly string[];
}>;

const CONTROL_IDS: Readonly<Record<string, string>> = {
  concern_category: IDS.category,
  description: IDS.description,
  contact_channel: IDS.contactChannel,
  contact_value: IDS.contactValue,
  reporter_handle: IDS.handle,
  reporter_passphrase: IDS.passphrase
};

// After these, the server may or may not have stored the report; a resend with the same key is safe.
const COMPLETION_UNKNOWN: ReadonlySet<string> = new Set([
  "upstream_timeout",
  "dependency_unavailable",
  "network_unavailable",
  "internal_error"
]);

const CREDENTIAL_CODES: ReadonlySet<string> = new Set([
  "invalid_credentials",
  "invalid_reporter_credentials"
]);

function subscribeNever(): () => void {
  return () => undefined;
}

function sizeLabel(bytes: number, locale: string): string {
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(
    bytes >= 1024 * 1024 ? bytes / (1024 * 1024) : Math.max(bytes / 1024, 0.1)
  )} ${bytes >= 1024 * 1024 ? "MB" : "KB"}`;
}

/**
 * The private report wizard. Everything a person types lives in this component's memory and is
 * sent once, to the same-origin route handler, when they choose to send. Nothing is written to a
 * URL, cookie, or storage, except the opt-in draft (concern and description only, expiring in 24
 * hours). Files are prepared in the browser for the person's benefit only; the server is the
 * security boundary. A retry of the same reviewed report reuses one idempotency key, so it cannot
 * create a second report.
 */
export function ReportWizard({
  copy,
  handleHref,
  language,
  locale,
  problems,
  projectTitle,
  slug,
  trustHref
}: Readonly<{
  copy: Messages["report"];
  handleHref: string;
  language: ApiLocale;
  locale: ApiLocale;
  problems: Messages["problems"];
  projectTitle: string;
  slug: string;
  trustHref: string;
}>): ReactNode {
  const router = useRouter();
  const headingId = useId();
  const [step, setStep] = useState<Step>("notice");
  const [form, setForm] = useState<ReportForm>(EMPTY_FORM);
  const [held, setHeld] = useState<readonly Held[]>([]);
  const [notes, setNotes] = useState<readonly FileNote[]>([]);
  const [preparing, setPreparing] = useState(0);
  const [errors, setErrors] = useState<readonly StepError[]>([]);
  const [serverErrors, setServerErrors] = useState<ServerErrors | undefined>(undefined);
  const [sending, setSending] = useState<Sending>({ phase: "idle" });
  const [consent, setConsent] = useState(false);
  const [draftNote, setDraftNote] = useState<"none" | "removed" | "restored" | "unavailable">(
    "none"
  );
  const ready = useSyncExternalStore(
    subscribeNever,
    () => true,
    () => false
  );
  const canSave = useSyncExternalStore(subscribeNever, draftStorageAvailable, () => true);
  const heading = useRef<HTMLHeadingElement>(null);
  const failure = useRef<HTMLDivElement>(null);
  const previousStepRef = useRef<Step>("notice");
  const nextId = useRef(1);
  const controller = useRef<AbortController | undefined>(undefined);
  const keyRef = useRef<{ key: string; signature: string } | undefined>(undefined);
  const urls = useRef<Set<string>>(new Set());
  const [mountedAt] = useState(() => Date.now());
  const format = createFormatters(language);

  const rawDraft = useSyncExternalStore(subscribeToDraft, readRawDraft, () => null);
  // Once the person has consented, the stored draft is their own and is not re-judged against the
  // time this page opened: a draft saved a moment ago would otherwise look dated in the future.
  const lookup = consent ? ({ kind: "none" } as const) : parseDraft(rawDraft, slug, mountedAt);
  const found = lookup.kind === "found" && step === "notice" ? lookup.draft : undefined;

  useEffect(() => {
    // A stored draft that is expired, corrupt, or of another version is deleted, not kept.
    if (lookup.kind === "invalid") {
      clearDraft();
    }
  }, [lookup.kind]);

  const dirty = hasContent(form, held.length);

  useEffect(() => {
    // The language switch warns only when something written here would not survive it.
    setUnsavedDraft(dirty && !consent);

    return () => setUnsavedDraft(false);
  }, [dirty, consent]);

  useEffect(() => {
    if (!dirty) {
      return undefined;
    }

    const warn = (event: BeforeUnloadEvent): void => {
      if (!consent) {
        event.preventDefault();
      }
    };

    window.addEventListener("beforeunload", warn);

    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty, consent]);

  useEffect(() => {
    const previews = urls.current;

    return () => {
      controller.current?.abort();
      // Object URLs are revoked when the wizard leaves, so a preview never outlives the page.
      for (const url of previews) {
        URL.revokeObjectURL(url);
      }
      previews.clear();
    };
  }, []);

  useEffect(() => {
    if (previousStepRef.current !== step) {
      previousStepRef.current = step;
      heading.current?.focus();
    }
  }, [step]);

  useEffect(() => {
    if (sending.phase !== "idle" && sending.phase !== "sending") {
      failure.current?.focus();
    }
  }, [sending.phase]);

  function persist(nextForm: ReportForm, nextStepValue: Step): void {
    if (consent) {
      setDraftNote(saveDraft(slug, nextStepValue, nextForm, Date.now()) ? "none" : "unavailable");
    }
  }

  function edit(patch: Partial<ReportForm>): void {
    const next = { ...form, ...patch };

    setForm(next);
    setErrors([]);
    setServerErrors(undefined);
    persist(next, step);
  }

  function go(target: Step): void {
    setErrors([]);
    setStep(target);
    persist(form, target);
  }

  function forward(): void {
    const problems_ = validateStep(step, form);

    if (problems_.length > 0) {
      setErrors(problems_);
      return;
    }
    go(nextStep(step));
  }

  async function add(list: FileList): Promise<void> {
    const incoming = [...list];
    const room = LIMITS.files - held.length;
    const found_: FileNote[] = [];
    const accepted: Held[] = [];

    if (incoming.length > room) {
      found_.push({ reason: "tooMany", number: held.length + room + 1 });
    }

    setPreparing((count) => count + 1);

    for (const [offset, file] of incoming.slice(0, Math.max(room, 0)).entries()) {
      const number = held.length + accepted.length + 1;
      // Loaded only when a file is added: most reports have none, and the first load stays small.
      const { prepareFile } = await import("@/lib/report/image-prep");
      const result = await prepareFile(file, number);

      if (!result.ok) {
        found_.push({ reason: result.reason, number: held.length + offset + 1 });
        continue;
      }

      const url =
        result.prepared.kind === "image" ? URL.createObjectURL(result.prepared.file) : null;

      if (url !== null) {
        urls.current.add(url);
      }
      accepted.push({ id: nextId.current++, prepared: result.prepared, url });
    }

    setPreparing((count) => count - 1);
    setNotes(found_);
    setHeld((current) => [...current, ...accepted].slice(0, LIMITS.files));
    setServerErrors(undefined);
  }

  function remove(id: number): void {
    const target = held.find((entry) => entry.id === id);

    if (target?.url !== null && target?.url !== undefined) {
      URL.revokeObjectURL(target.url);
      urls.current.delete(target.url);
    }
    setHeld((current) => current.filter((entry) => entry.id !== id));
    setNotes([]);
  }

  function reset(): void {
    for (const url of urls.current) {
      URL.revokeObjectURL(url);
    }
    urls.current.clear();
    setHeld([]);
    setForm(EMPTY_FORM);
    keyRef.current = undefined;
  }

  async function send(): Promise<void> {
    if (controller.current !== undefined) {
      return;
    }

    const invalid = firstInvalidStep(form);

    if (invalid !== undefined) {
      setErrors(validateStep(invalid, form));
      setStep(invalid);
      return;
    }
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      setSending({ phase: "offline" });
      return;
    }

    // Claimed before the module loads, so a second click during the load cannot send twice.
    const active = new AbortController();

    controller.current = active;
    setServerErrors(undefined);
    setSending({ phase: "sending", progress: 0 });

    const { payloadSignature, submitReport } = await import("@/lib/report/submit");
    const input = { slug, form, files: held.map((entry) => entry.prepared.file) };
    const signature = payloadSignature(input);

    // The same reviewed report keeps its key across retries; an edited report is a new intent.
    if (keyRef.current?.signature !== signature) {
      keyRef.current = { key: crypto.randomUUID(), signature };
    }

    const outcome = await submitReport({
      input,
      idempotencyKey: keyRef.current.key,
      locale,
      onProgress: (fraction) => setSending({ phase: "sending", progress: fraction }),
      signal: active.signal
    });

    controller.current = undefined;

    if (outcome.kind === "received") {
      setReceipt(outcome.receipt);
      clearDraft();
      setUnsavedDraft(false);
      reset();
      router.push(`/${locale}/report/complete` as Route);
      return;
    }
    if (outcome.kind === "aborted") {
      setSending({ phase: "cancelled" });
      return;
    }
    if (outcome.kind === "network") {
      setSending({ phase: "unknown" });
      return;
    }

    const { problem } = outcome;

    if (problem.code === "idempotency_conflict") {
      keyRef.current = undefined;
    }

    const described = describeProblem(problem, problems, formatMessageLite);
    const mapped = mapFieldErrors(described.fieldErrors, CONTROL_IDS);
    const owner =
      problem.fieldErrors
        .map((entry) => stepForApiField(entry.field))
        .find((value): value is Step => value !== undefined) ??
      (CREDENTIAL_CODES.has(problem.code) ? "anonymity" : undefined) ??
      (problem.status === 413 || problem.status === 415 ? "evidence" : undefined);

    if (owner !== undefined) {
      setServerErrors({
        step: owner,
        items: mapped.mapped,
        extra: [described.message, ...mapped.unmapped]
      });
      setStep(owner);
    }
    setSending({ phase: "problem", problem });
  }

  const summary = errors.map((error) => ({
    controlId: IDS[error.field],
    message: errorMessage(copy, error.key)
  }));
  const current = stepIndex(step) + 1;
  const stepName = copy.steps[step];
  const busy = sending.phase === "sending";
  const status =
    sending.phase === "sending"
      ? copy.send.sending
      : sending.phase === "cancelled"
        ? copy.send.cancelled
        : sending.phase === "offline"
          ? copy.send.offline
          : sending.phase === "unknown"
            ? copy.send.unknown
            : sending.phase === "problem"
              ? copy.send.failedTitle
              : "";
  const problemView =
    sending.phase === "problem"
      ? describeProblem(sending.problem, problems, formatMessageLite)
      : undefined;

  return (
    <section
      aria-labelledby={headingId}
      className="grid max-w-[68ch] gap-6"
      data-slot="report-wizard"
    >
      <p className="m-0 text-sm text-muted-foreground" hidden={ready}>
        {copy.needsScript}
      </p>
      <nav aria-label={copy.steps.label}>
        <ol className="m-0 flex list-none flex-wrap gap-x-4 gap-y-1 p-0 text-sm">
          {STEPS.map((name, index) => (
            <li
              aria-current={name === step ? "step" : undefined}
              className={name === step ? "font-bold underline" : "text-muted-foreground"}
              key={name}
            >
              {index + 1}. {copy.steps[name]}
            </li>
          ))}
        </ol>
      </nav>
      <p className="m-0 text-sm text-muted-foreground">
        {formatMessageLite(copy.steps.progress, { number: current, total: STEPS.length })}
      </p>
      <h2 className="m-0 text-ledger-xl" id={headingId} ref={heading} tabIndex={-1}>
        {stepName}
      </h2>
      <p className="m-0 text-sm text-muted-foreground">
        {formatMessageLite(copy.context, { title: projectTitle })}
      </p>

      {found === undefined ? null : (
        <Callout title={copy.draft.heading} tone="information">
          <p className="m-0">
            {formatMessageLite(copy.draft.found, {
              when: format.dateTime(new Date(found.savedAt).toISOString())
            })}
          </p>
          <div className="mt-2 flex flex-wrap gap-3">
            <Button
              onClick={() => {
                setForm({
                  ...EMPTY_FORM,
                  category: found.category,
                  description: found.description
                });
                setConsent(true);
                setDraftNote("restored");
                setStep(found.step);
              }}
              variant="secondary"
            >
              {copy.draft.restore}
            </Button>
            <Button
              onClick={() => {
                clearDraft();
                setDraftNote("removed");
              }}
              variant="secondary"
            >
              {copy.draft.discard}
            </Button>
          </div>
        </Callout>
      )}

      {serverErrors?.step === step || summary.length > 0 ? (
        <ErrorSummary
          extra={serverErrors?.step === step ? serverErrors.extra : []}
          items={
            summary.length > 0 ? summary : serverErrors?.step === step ? serverErrors.items : []
          }
          title={copy.nav.stepErrors}
        />
      ) : null}

      {step === "notice" ? <NoticeStep copy={copy} trustHref={trustHref} /> : null}
      <Suspense fallback={<p role="status">{copy.nav.loading}</p>}>
        {step === "observation" ? (
          <ObservationStep copy={copy} errors={errors} form={form} onChange={edit} />
        ) : null}
        {step === "evidence" ? (
          <EvidenceStep
            copy={copy}
            files={
              held.map((entry) => ({
                id: entry.id,
                kind: entry.prepared.kind,
                cleaned: entry.prepared.cleaned,
                url: entry.url,
                sizeLabel: sizeLabel(entry.prepared.file.size, locale)
              })) satisfies readonly FileView[]
            }
            notes={notes}
            onAdd={(list) => void add(list)}
            onRemove={remove}
            preparing={preparing}
          />
        ) : null}
        {step === "anonymity" ? (
          <AnonymityStep
            copy={copy}
            errors={errors}
            form={form}
            handleHref={handleHref}
            onChange={edit}
            onMode={(mode) => {
              setErrors([]);
              setForm(withMode(form, mode));
            }}
          />
        ) : null}
        {step === "review" ? (
          <ReviewStep copy={copy} fileCount={held.length} form={form} onChange={go} />
        ) : null}
      </Suspense>

      {step === "observation" ||
      step === "evidence" ||
      step === "anonymity" ||
      step === "review" ? (
        <Suspense fallback={null}>
          <DraftConsent
            canSave={canSave}
            consent={consent}
            copy={copy}
            note={draftNote}
            onConsent={(on) => {
              setConsent(on);
              if (on) {
                setDraftNote(saveDraft(slug, step, form, Date.now()) ? "none" : "unavailable");
              } else {
                clearDraft();
                setDraftNote("removed");
              }
            }}
            onRemove={() => {
              clearDraft();
              setConsent(false);
              setDraftNote("removed");
            }}
          />
        </Suspense>
      ) : null}

      {problemView !== undefined ||
      sending.phase === "cancelled" ||
      sending.phase === "offline" ||
      sending.phase === "unknown" ? (
        <div
          className="grid gap-2 border-2 border-destructive bg-card p-4"
          data-slot="send-failure"
          ref={failure}
          tabIndex={-1}
        >
          <h3 className="m-0 text-ledger-lg">{copy.send.failedTitle}</h3>
          <p className="m-0">{problemView?.message ?? status}</p>
          {sending.phase === "problem" && sending.problem.retryAfterSeconds !== undefined ? (
            <p className="m-0">
              {formatMessageLite(copy.send.wait, { seconds: sending.problem.retryAfterSeconds })}
            </p>
          ) : null}
          {sending.phase === "problem" && COMPLETION_UNKNOWN.has(sending.problem.code) ? (
            <p className="m-0">{copy.send.unknown}</p>
          ) : null}
          {problemView?.referenceLine === undefined ? null : (
            <p className="m-0 text-sm">{problemView.referenceLine}</p>
          )}
        </div>
      ) : null}

      {busy ? (
        <div className="grid gap-2">
          <progress
            aria-label={copy.send.sending}
            className="w-full"
            max={100}
            value={Math.round(sending.progress * 100)}
          />
          <p className="m-0 text-sm">
            {formatMessageLite(copy.send.progress, { percent: Math.round(sending.progress * 100) })}
          </p>
        </div>
      ) : null}
      <p aria-live="polite" className="sr-only" role="status">
        {status}
      </p>

      <div className="flex flex-wrap gap-3">
        {step === "notice" ? null : (
          <Button disabled={busy} onClick={() => go(previousStep(step))} variant="secondary">
            {copy.nav.back}
          </Button>
        )}
        {step === "review" ? (
          <Button
            aria-disabled={busy || !ready}
            data-action="send"
            disabled={!ready}
            onClick={() => void send()}
          >
            {sending.phase === "idle" || sending.phase === "sending"
              ? copy.review.submit
              : copy.send.retry}
          </Button>
        ) : (
          <Button
            data-action="next"
            disabled={!ready}
            onClick={step === "notice" ? () => go("observation") : forward}
          >
            {step === "notice" ? copy.notice.start : copy.nav.next}
          </Button>
        )}
        {busy ? (
          <Button onClick={() => controller.current?.abort()} variant="secondary">
            {copy.send.cancel}
          </Button>
        ) : null}
      </div>
    </section>
  );
}
