"use client";

import { useRouter } from "next/navigation";
import { useId, useState, type ReactNode } from "react";

import { CitationEntry } from "@/components/evidence/evidence";
import { PublicUpdateEntry, citationView, type EntryCopy } from "@/components/project/update-entry";
import { ActionFeedback } from "@/components/reviewer/action-feedback";
import { Button, ButtonLink } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/choice";
import { Callout } from "@/components/ui/feedback";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { ConfirmDialog } from "@/components/ui/overlay";
import type { Messages } from "@/i18n/catalogue";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { createFormatters } from "@/lib/format/formatters";
import { networkProblem, readBrowserProblem } from "@/lib/problems/browser-problem";
import type { SafeProblem } from "@/lib/problems/problem-messages";
import {
  issueKind,
  parsePreview,
  type CitationOption,
  type PreviewView
} from "@/lib/reviewer/publication";
import { postJson } from "@/lib/tracking/client";

export const STATEMENT_MIN = 10;
export const STATEMENT_MAX = 2000;
const VERIFICATION_CHOICES = [
  "verified_official",
  "corroborated",
  "community_reviewed",
  "disputed",
  "outdated"
] as const;

type Copy = Messages["reviewer"]["publication"];
type Mode = "compose" | "preview" | "published";
type Draft = Readonly<{ id: string; state: string; createdAt: string }>;

const DIGEST_OK = /^[0-9a-f]{64}$/;

function issueText(copy: Copy, issue: { field: string; code: string }): string {
  const kind = issueKind(issue.code);

  if (kind.kind === "term") {
    return formatMessageLite(copy.issues.term, { term: kind.term });
  }
  if (kind.kind === "known" && Object.hasOwn(copy.issues.known, kind.key)) {
    return (copy.issues.known as Readonly<Record<string, string>>)[kind.key] ?? issue.code;
  }

  return formatMessageLite(copy.issues.other, { code: issue.code });
}

/**
 * Drafts, previews, and publishes one public update for a report. It is deliberately separate from
 * the status controls and never prefilled: the statement starts empty, the citations are chosen from
 * the approved ones the public record already shows for the project, and the preview is drawn with
 * the very component the public timeline uses. Publishing sends only the preview's digest, so what
 * is confirmed is what was previewed; a changed report or text makes the digest stale and the API
 * refuses it. Nothing is stored in the browser.
 */
export function PublicUpdatePanel({
  actions,
  copy,
  drafts,
  entryCopy,
  language,
  locale,
  now,
  options,
  problems,
  projectHref,
  reportId,
  reportVerified,
  signInHref
}: Readonly<{
  actions: Messages["reviewer"]["actions"];
  copy: Copy;
  drafts: readonly Draft[];
  entryCopy: EntryCopy;
  language: ApiLocale;
  locale: string;
  /** Server time as an ISO string, so the preview labels a future date the same way the public page does. */
  now: string;
  /** `undefined` when the approved citations could not be loaded. */
  options: readonly CitationOption[] | undefined;
  problems: Messages["problems"];
  projectHref: string;
  reportId: string;
  reportVerified: boolean;
  signInHref: string;
}>): ReactNode {
  const id = useId();
  const router = useRouter();
  const base = `/api/reviewer/reports/${encodeURIComponent(reportId)}/public-updates`;
  const [mode, setMode] = useState<Mode>("compose");
  const [statement, setStatement] = useState("");
  const [effectiveOn, setEffectiveOn] = useState("");
  const [lastChecked, setLastChecked] = useState("");
  const [verification, setVerification] =
    useState<(typeof VERIFICATION_CHOICES)[number]>("verified_official");
  const [selected, setSelected] = useState<readonly string[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<PreviewView | undefined>(undefined);
  const [busy, setBusy] = useState<"create" | "open" | "publish" | "discard" | undefined>(
    undefined
  );
  const [problem, setProblem] = useState<SafeProblem | undefined>(undefined);
  const [note, setNote] = useState<string | undefined>(undefined);
  const [publishedAt, setPublishedAt] = useState<string | undefined>(undefined);
  const [publishOpen, setPublishOpen] = useState(false);
  const [discardOpen, setDiscardOpen] = useState(false);
  const format = createFormatters(language);
  const invalid: SafeProblem = {
    code: "internal_error",
    status: 200,
    requestId: undefined,
    retryAfterSeconds: undefined,
    fieldErrors: []
  };

  function reset(next?: string): void {
    setProblem(undefined);
    setNote(next);
  }

  async function createPreview(): Promise<void> {
    const next: Record<string, string> = {};
    const trimmed = statement.trim();

    if (trimmed === "") {
      next["statement"] = copy.errors.statementRequired;
    } else if (trimmed.length < STATEMENT_MIN) {
      next["statement"] = copy.errors.statementShort;
    } else if (trimmed.length > STATEMENT_MAX) {
      next["statement"] = copy.errors.statementLong;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(effectiveOn)) {
      next["effective"] = copy.errors.dateRequired;
    }
    if (selected.length < 1) {
      next["citations"] = copy.errors.citationsRequired;
    } else if (selected.length > 5) {
      next["citations"] = copy.errors.citationsTooMany;
    }

    setErrors(next);
    reset();

    if (Object.keys(next).length > 0 || busy !== undefined) {
      return;
    }

    const chosen = (options ?? []).filter((option) => selected.includes(option.key));

    setBusy("create");
    const outcome = await postJson(
      base,
      {
        statement: trimmed,
        effective_on: effectiveOn,
        ...(lastChecked === "" ? {} : { last_checked_on: lastChecked }),
        verification_state: verification,
        citations: chosen.map((option) => ({
          source_version_id: option.sourceVersionId,
          passage: option.passage,
          location_label: option.locationLabel
        }))
      },
      { locale }
    );

    setBusy(undefined);

    if (outcome.kind !== "ok") {
      setProblem(outcome.kind === "problem" ? outcome.problem : networkProblem());
      return;
    }

    const parsed = parsePreview(outcome.data);

    if (parsed === undefined) {
      setProblem(invalid);
      return;
    }

    setPreview(parsed);
    setMode("preview");
    router.refresh();
  }

  async function openDraft(draftId: string): Promise<void> {
    if (busy !== undefined) {
      return;
    }

    reset();
    setBusy("open");

    try {
      const response = await fetch(`${base}/${encodeURIComponent(draftId)}`, {
        method: "GET",
        cache: "no-store",
        credentials: "same-origin"
      });

      if (!response.ok) {
        setProblem(await readBrowserProblem(response));
        return;
      }

      const parsed = parsePreview(await response.json());

      if (parsed === undefined) {
        setProblem(invalid);
        return;
      }

      setPreview(parsed);
      setMode("preview");
    } catch {
      setProblem(networkProblem());
    } finally {
      setBusy(undefined);
    }
  }

  async function publish(): Promise<void> {
    if (preview === undefined || busy !== undefined || !DIGEST_OK.test(preview.digest)) {
      return;
    }

    reset();
    setBusy("publish");
    const outcome = await postJson(
      `${base}/${encodeURIComponent(preview.id)}/publish`,
      { preview_digest: preview.digest },
      { locale }
    );

    setBusy(undefined);

    if (outcome.kind === "ok") {
      const data = outcome.data as { published_at?: unknown } | undefined;

      setPublishedAt(typeof data?.published_at === "string" ? data.published_at : undefined);
      setMode("published");
      router.refresh();
      return;
    }

    if (outcome.kind === "problem" && outcome.problem.status === 409) {
      // The preview no longer matches the report or its text: back to editing, nothing published.
      setMode("compose");
      setPreview(undefined);
      setNote(copy.preview.stale);
      router.refresh();
      return;
    }

    setProblem(outcome.kind === "problem" ? outcome.problem : networkProblem());
  }

  async function discard(draftId: string): Promise<void> {
    if (busy !== undefined) {
      return;
    }

    reset();
    setBusy("discard");
    const outcome = await postJson(`${base}/${encodeURIComponent(draftId)}/withdraw`, undefined, {
      locale
    });

    setBusy(undefined);

    if (outcome.kind === "ok") {
      setMode("compose");
      setPreview(undefined);
      setNote(copy.preview.discarded);
      router.refresh();
      return;
    }

    setProblem(outcome.kind === "problem" ? outcome.problem : networkProblem());
  }

  const feedback = (
    <ActionFeedback
      actions={actions}
      problem={problem}
      problems={problems}
      signInHref={signInHref}
      success={note}
    />
  );

  if (mode === "published") {
    return (
      <div className="grid gap-3" data-slot="publication-published">
        <Callout title={copy.preview.publishedHeading} tone="information">
          {copy.preview.publishedBody}
        </Callout>
        {publishedAt === undefined ? null : (
          <p className="m-0">
            {formatMessageLite(copy.preview.publishedAt, { date: format.dateTime(publishedAt) })}
          </p>
        )}
        <div>
          <ButtonLink href={projectHref} variant="secondary">
            {copy.preview.viewPublic}
          </ButtonLink>
        </div>
      </div>
    );
  }

  if (mode === "preview" && preview !== undefined) {
    const claimId = `preview-${preview.id}`;
    const views = preview.update.citations.map((citation, index) =>
      citationView(claimId, citation, index, entryCopy, language)
    );
    const canPublish = preview.canPublish && preview.state === "draft";

    return (
      <div className="grid gap-4" data-slot="publication-preview">
        <h3 className="m-0 text-ledger-lg">{copy.preview.heading}</h3>
        <p className="m-0">{copy.preview.lead}</p>
        <p className="m-0 text-sm">
          {formatMessageLite(copy.preview.status, {
            status: preview.reportStatus,
            version: preview.reportVersion
          })}
        </p>
        <div className="border-2 border-double border-border p-3" data-slot="public-preview-frame">
          <ol className="m-0 grid list-none gap-4 p-0">
            <PublicUpdateEntry
              claimId={claimId}
              copy={entryCopy}
              format={format}
              language={language}
              now={new Date(now)}
              update={preview.update}
            />
          </ol>
          <h4 className="mb-2 mt-4 text-base">{copy.preview.citationsHeading}</h4>
          <ol className="m-0 grid list-none gap-3 p-0">
            {views.map((view) => (
              <CitationEntry
                backHref={`#${claimId}`}
                backLabel={entryCopy.project.facts.back}
                citation={view}
                key={view.id}
                showFullLabel={entryCopy.source.excerpts.showFull}
              />
            ))}
          </ol>
        </div>
        {preview.issues.length === 0 ? (
          <p className="m-0" role="status">
            {copy.preview.noIssues}
          </p>
        ) : (
          <div className="grid gap-2 border-2 border-destructive bg-card p-3" role="alert">
            <strong>{copy.preview.issuesHeading}</strong>
            <ul className="m-0 grid gap-1 ps-5">
              {preview.issues.map((issue) => (
                <li key={`${issue.field}-${issue.code}`}>
                  {issueText(copy, issue)}{" "}
                  <small>{formatMessageLite(copy.issues.field, { field: issue.field })}</small>
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="flex flex-wrap gap-3">
          <Button
            aria-disabled={!canPublish || busy !== undefined}
            onClick={() => {
              if (canPublish && busy === undefined) {
                setPublishOpen(true);
              }
            }}
          >
            {busy === "publish" ? copy.preview.publishing : copy.preview.publish}
          </Button>
          <Button
            onClick={() => {
              setMode("compose");
              reset();
            }}
            variant="secondary"
          >
            {copy.preview.edit}
          </Button>
          <Button
            aria-disabled={busy !== undefined || preview.state !== "draft"}
            onClick={() => {
              if (busy === undefined && preview.state === "draft") {
                setDiscardOpen(true);
              }
            }}
            variant="secondary"
          >
            {copy.preview.discard}
          </Button>
        </div>
        {canPublish ? null : <p className="m-0 text-sm">{copy.preview.cannot}</p>}
        <ConfirmDialog
          cancelLabel={copy.preview.cancel}
          confirmLabel={copy.preview.confirm}
          description={copy.preview.confirmBody}
          onConfirm={() => {
            void publish();
          }}
          onOpenChange={setPublishOpen}
          open={publishOpen}
          title={copy.preview.confirmTitle}
        />
        <ConfirmDialog
          cancelLabel={copy.preview.cancel}
          confirmLabel={copy.preview.discardConfirm}
          description={copy.preview.discardBody}
          onConfirm={() => {
            void discard(preview.id);
          }}
          onOpenChange={setDiscardOpen}
          open={discardOpen}
          title={copy.preview.discardTitle}
        />
        {feedback}
      </div>
    );
  }

  const blocked = !reportVerified
    ? copy.needsVerified
    : options === undefined
      ? copy.citationsUnavailable
      : options.length === 0
        ? copy.noCitations
        : undefined;

  return (
    <div className="grid gap-5" data-slot="publication-composer">
      <p className="m-0 max-w-[68ch]">{copy.intro}</p>
      <Callout title={copy.guidanceTitle} tone="warning">
        {copy.guidance}
      </Callout>
      {blocked === undefined ? (
        <form
          className="grid gap-4"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            void createPreview();
          }}
        >
          <Field
            controlId={`${id}-statement`}
            description={formatMessageLite(copy.statementHint, { max: STATEMENT_MAX })}
            error={errors["statement"]}
            label={copy.statement}
            required
          >
            <Textarea
              autoComplete="off"
              onChange={(event) => {
                setStatement(event.target.value);
              }}
              rows={5}
              value={statement}
            />
          </Field>
          <small>
            {formatMessageLite(copy.counter, { count: statement.length, max: STATEMENT_MAX })}
          </small>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              controlId={`${id}-effective`}
              description={copy.effectiveHelp}
              error={errors["effective"]}
              label={copy.effectiveOn}
              required
            >
              <Input
                onChange={(event) => {
                  setEffectiveOn(event.target.value);
                }}
                type="date"
                value={effectiveOn}
              />
            </Field>
            <Field
              controlId={`${id}-checked`}
              description={copy.lastCheckedHelp}
              label={copy.lastChecked}
            >
              <Input
                onChange={(event) => {
                  setLastChecked(event.target.value);
                }}
                type="date"
                value={lastChecked}
              />
            </Field>
          </div>
          <Field controlId={`${id}-verification`} label={copy.verification}>
            <Select
              onChange={(event) => {
                setVerification(event.target.value as (typeof VERIFICATION_CHOICES)[number]);
              }}
              value={verification}
            >
              {VERIFICATION_CHOICES.map((choice) => (
                <option key={choice} value={choice}>
                  {entryCopy.evidence.verification[choice]}
                </option>
              ))}
            </Select>
          </Field>
          <fieldset
            aria-describedby={`${id}-citations-hint`}
            className="m-0 grid gap-1 border border-border p-3"
          >
            <legend className="px-1 font-semibold">{copy.citations}</legend>
            <small className="text-muted-foreground" id={`${id}-citations-hint`}>
              {copy.citationsHint}
            </small>
            {(options ?? []).map((option) => (
              <Checkbox
                checked={selected.includes(option.key)}
                description={option.passage}
                key={option.key}
                label={formatMessageLite(copy.citationLine, {
                  title: option.sourceTitle,
                  publisher: option.publisher,
                  location: option.locationLabel
                })}
                onChange={(event) => {
                  setSelected((current) =>
                    event.target.checked
                      ? [...current, option.key]
                      : current.filter((key) => key !== option.key)
                  );
                }}
              />
            ))}
            {errors["citations"] === undefined ? null : (
              <small className="font-semibold text-destructive" role="alert">
                {errors["citations"]}
              </small>
            )}
          </fieldset>
          <div>
            <Button aria-disabled={busy !== undefined} type="submit">
              {busy === "create" ? copy.creating : copy.submit}
            </Button>
          </div>
        </form>
      ) : (
        <p className="m-0 font-semibold" data-slot="publication-blocked" role="status">
          {blocked}
        </p>
      )}
      {feedback}
      <div className="grid gap-2" data-slot="publication-drafts">
        <h3 className="m-0 text-base">{copy.drafts.heading}</h3>
        {drafts.length === 0 ? (
          <p className="m-0">{copy.drafts.empty}</p>
        ) : (
          <ul className="m-0 grid list-none gap-2 p-0">
            {drafts.map((draft) => (
              <li
                className="flex flex-wrap items-center gap-3 border border-border p-2"
                key={draft.id}
              >
                <span>
                  {formatMessageLite(copy.drafts.state, {
                    state:
                      (copy.drafts.states as Readonly<Record<string, string>>)[draft.state] ??
                      draft.state
                  })}
                  {" · "}
                  {formatMessageLite(copy.drafts.created, {
                    date: format.dateTime(draft.createdAt)
                  })}
                </span>
                {draft.state === "draft" ? (
                  <Button
                    aria-disabled={busy !== undefined}
                    onClick={() => {
                      void openDraft(draft.id);
                    }}
                    variant="secondary"
                  >
                    {busy === "open" ? copy.drafts.loading : copy.drafts.open}
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
