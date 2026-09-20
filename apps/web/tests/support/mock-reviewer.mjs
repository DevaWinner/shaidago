import { createHash } from "node:crypto";

import { analysisFor, defaultSources, manySources } from "./mock-discovery.mjs";

/**
 * Fictional reviewer endpoints for the browser test servers. Everything returned is synthetic.
 * It enforces the same header contract as the real API (`X-Shaidago-Session`, and
 * `X-Shaidago-Csrf` on mutations), so a test proves the BFF forwarded the HttpOnly cookies, and it
 * records only counts and request shapes, never a credential value.
 */

export const SESSION_TOKEN = "fictional-session-token-0123456789abcdef";
export const CSRF_TOKEN = "fictional-csrf-token-0123456789abcdef0";
export const IDENTIFIER = "reviewer-demo";
export const PASSWORD = "fictional-password-not-a-secret";

const log = [];

const STATUSES = [
  "received",
  "needs_information",
  "under_review",
  "verified_for_public_update",
  "referred",
  "closed"
];
const RISKS = ["standard", "elevated", "high"];
const CATEGORIES = [
  "no_visible_work",
  "incomplete_work",
  "unsafe_construction",
  "suspected_incorrect_status",
  "access_barrier",
  "other_concern"
];
const PROJECTS = ["synthetic-example-clinic", "synthetic-example-school", "synthetic-example-road"];

export const REPORT_IDS = [];

const queue = Array.from({ length: 45 }, (_, index) => {
  const report_id = `0198f1a2-7b3c-4d4e-8f5a-${String(index + 1).padStart(12, "0")}`;

  REPORT_IDS.push(report_id);

  return {
    report_id,
    // Verified reports belong to a generated synthetic record so a public update has citations to use.
    project_slug:
      STATUSES[index % STATUSES.length] === "verified_for_public_update"
        ? "synthetic-project-20"
        : PROJECTS[index % PROJECTS.length],
    concern_category: CATEGORIES[index % CATEGORIES.length],
    risk_level: RISKS[index % RISKS.length],
    status: STATUSES[index % STATUSES.length],
    version: 1 + (index % 3),
    created_at: `2026-09-${String(1 + (index % 28)).padStart(2, "0")}T09:00:00Z`,
    status_updated_at: `2026-09-${String(2 + (index % 27)).padStart(2, "0")}T10:00:00Z`,
    has_contact: index % 4 === 0,
    evidence_count: index % 3,
    open_follow_ups: index % 5 === 0 ? 1 : 0
  };
});

export const DESCRIPTION =
  "Fictional description line one.\nLine two with <script>alert(1)</script> and <b>bold</b> that must stay text.";
export const CONTACT_VALUE = "fictional-contact@example.invalid";
const NO_CONTACT_CAPABILITY = REPORT_IDS[4];
const UNAVAILABLE_REPORT = REPORT_IDS[43];
const FORBIDDEN_REPORT = REPORT_IDS[44];

// Per-report state that the browser tests change: notes and questions are append-only or withdrawn.
const notes = new Map([
  [
    REPORT_IDS[0],
    Array.from({ length: 22 }, (_, index) => ({
      note_id: `0198f1a2-7b3c-4d4e-8f5a-b${String(index).padStart(11, "0")}`,
      created_at: `2026-09-10T09:${String(index).padStart(2, "0")}:00Z`,
      author: "reviewer-demo",
      body:
        index === 1
          ? "Seeded note with <b>markup</b> that must stay text."
          : `Seeded fictional note ${index + 1}.`
    }))
  ]
]);
const questions = new Map();
// Status changes made through the transition endpoint, so a reload shows the new state.
const changes = new Map();
// Reports where another reviewer "acts first": the first attempt is refused as stale.
const RACE_IDS = new Set([REPORT_IDS[24], REPORT_IDS[30]]);
const raced = new Set();
const discoveryRuns = new Map();
let runCounter = 0;
const DISCOVERY_DIGEST = "a".repeat(64);
const MACHINE = {
  received: {
    start_review: "under_review",
    request_information: "needs_information",
    close: "closed"
  },
  needs_information: { resume_review: "under_review", close: "closed" },
  under_review: {
    request_information: "needs_information",
    verify_for_public_update: "verified_for_public_update",
    refer: "referred",
    close: "closed"
  },
  verified_for_public_update: { resume_review: "under_review", refer: "referred", close: "closed" },
  referred: { resume_review: "under_review", close: "closed" },
  closed: { reopen: "under_review" }
};

// Public updates: drafts per report, and the ones that were published, per project.
const drafts = new Map();
const published = new Map();

export function publishedFor(slug) {
  return published.get(slug) ?? [];
}

function digestOf(draft, version) {
  return createHash("sha256")
    .update(JSON.stringify([draft.update, version]))
    .digest("hex");
}

function previewOf(draft, item) {
  const status = current(item);
  const issues = [];

  if (/corrupt|fraud/i.test(draft.update.statement)) {
    issues.push({ field: "statement", code: "unsupported_term_corrupt" });
  }
  if (draft.update.statement.includes("SECRET-REPORT-TEXT")) {
    issues.push({ field: "statement", code: "report_text" });
  }

  return {
    public_update_id: draft.id,
    state: draft.state,
    project_slug: item.project_slug,
    report_status: status.status,
    report_version: status.version,
    update: draft.update,
    issues,
    can_publish:
      issues.length === 0 &&
      draft.state === "draft" &&
      status.status === "verified_for_public_update",
    preview_digest: digestOf(draft, status.version)
  };
}

function current(item) {
  const change = changes.get(item.report_id);

  return change === undefined
    ? item
    : { ...item, status: change.status, version: change.version, status_updated_at: change.at };
}
let counter = 0;
const nextId = (prefix) =>
  `0198f1a2-7b3c-4d4e-8f5a-${prefix}${String(++counter).padStart(11, "0")}`;

function detailFor(source, includeContact) {
  const item = current(source);
  const first = item.report_id === REPORT_IDS[0];

  return {
    ...item,
    description: first ? DESCRIPTION : "A fictional observation for this demo report.",
    events: [
      {
        event_id: `0198f1a2-7b3c-4d4e-8f5a-e${item.report_id.slice(-11)}`,
        previous_status: null,
        new_status: "received",
        public_message: "Your fictional report was received.",
        actor_type: "system",
        occurred_at: item.created_at,
        internal_reason: null
      },
      ...(changes.get(item.report_id)?.events ?? []),
      ...(first
        ? [
            {
              event_id: "0198f1a2-7b3c-4d4e-8f5a-e00000000099",
              previous_status: "received",
              new_status: item.status,
              public_message: "",
              actor_type: "reviewer",
              occurred_at: item.status_updated_at,
              internal_reason: "Fictional internal reason for the change."
            }
          ]
        : [])
    ],
    follow_ups: [
      ...(questions.get(item.report_id) ?? []),
      ...(first
        ? [
            {
              question_id: "0198f1a2-7b3c-4d4e-8f5a-f00000000001",
              question: "Which side of the building is the fictional crack on?",
              asked_at: "2026-09-05T09:00:00Z",
              withdrawn: false,
              answer_kind: "answered",
              answer: "The north side, fictionally."
            },
            {
              question_id: "0198f1a2-7b3c-4d4e-8f5a-f00000000002",
              question: "Is there a fictional sign at the gate?",
              asked_at: "2026-09-05T10:00:00Z",
              withdrawn: false,
              answer_kind: null,
              answer: null
            }
          ]
        : [])
    ],
    evidence: first
      ? [
          {
            evidence_id: "0198f1a2-7b3c-4d4e-8f5a-a00000000001",
            display_name: "evidence-1.jpg",
            mime_type: "image/jpeg",
            size_bytes: 2048,
            sanitation_state: "sanitised",
            scan_state: "not_scanned_demo",
            created_at: "2026-09-01T09:05:00Z"
          },
          {
            evidence_id: "0198f1a2-7b3c-4d4e-8f5a-a00000000002",
            display_name: "evidence-2.png",
            mime_type: "image/png",
            size_bytes: 3 * 1024 * 1024,
            sanitation_state: "sanitised",
            scan_state: "clean",
            created_at: "2026-09-01T09:06:00Z"
          }
        ]
      : [],
    track_record: first
      ? {
          handle: "fictional-handle-one",
          reports_total: 3,
          verified_for_public_update: 1,
          closed: 1
        }
      : null,
    contact: includeContact && item.has_contact ? { channel: "email", value: CONTACT_VALUE } : null
  };
}

function cursorFor(offset, key) {
  return Buffer.from(JSON.stringify({ offset, key })).toString("base64url");
}

function offsetFrom(value, key) {
  try {
    const parsed = JSON.parse(Buffer.from(value, "base64url").toString("utf8"));

    return parsed.key === key && Number.isInteger(parsed.offset) ? parsed.offset : undefined;
  } catch {
    return undefined;
  }
}

export function reviewerLog() {
  return log;
}

export function resetReviewer() {
  log.length = 0;
}

function json(response, status, body, headers = {}) {
  response.writeHead(status, {
    "Content-Type": "application/json",
    "Cache-Control": "no-store",
    ...headers
  });
  response.end(JSON.stringify(body));
}

function authorised(request) {
  return request.headers["x-shaidago-session"] === SESSION_TOKEN;
}

function hasCsrf(request) {
  return request.headers["x-shaidago-csrf"] === CSRF_TOKEN;
}

/** Returns true when the request was a reviewer request and has been answered. */
export function handleReviewer({ request, response, url, problem, readBody }) {
  const path = url.pathname;
  const method = request.method;

  if (path === "/v1/auth/sessions" && method === "POST") {
    readBody(request, (body) => {
      log.push({ op: "sign_in" });

      if (body?.identifier === "rate-limited") {
        problem(response, 429, "rate_limited", { "Retry-After": "2" });
      } else if (body?.identifier === IDENTIFIER && body?.password === PASSWORD) {
        json(response, 201, {
          session_token: SESSION_TOKEN,
          csrf_token: CSRF_TOKEN,
          expires_at: "2099-01-01T00:00:00Z",
          idle_timeout_seconds: 1800,
          cookie: {
            name: "sg_session",
            secure: false,
            http_only: true,
            same_site: "lax",
            path: "/",
            max_age_seconds: 3600
          },
          reviewer: { role: "reviewer" }
        });
      } else {
        problem(response, 401, "invalid_credentials");
      }
    });
    return true;
  }

  if (path === "/v1/auth/sessions/current" && method === "DELETE") {
    log.push({ op: "sign_out", csrf: hasCsrf(request) });
    response.writeHead(204, { "Cache-Control": "no-store" }).end();
    return true;
  }

  if (!path.startsWith("/v1/reviewer/")) {
    return false;
  }

  if (!authorised(request)) {
    problem(response, 401, "unauthenticated");
    return true;
  }

  const discoveryPlan = /^\/v1\/reviewer\/reports\/([^/]+)\/discovery-runs:plan$/.exec(path);

  if (discoveryPlan !== null && method === "POST") {
    if (!hasCsrf(request)) {
      problem(response, 403, "csrf_invalid");
      return true;
    }
    readBody(request, (body) => {
      const concepts = Array.isArray(body?.concepts) ? body.concepts : [];
      log.push({ op: "discovery_plan", concepts });
      json(response, 200, {
        plan_digest: DISCOVERY_DIGEST,
        policy_version: "fictional-policy-v1",
        query: "Abuja AMAC public works official source",
        terms: [
          { text: "Abuja", source: "project locality", suggested_by: "policy" },
          { text: "AMAC", source: "project area council", suggested_by: "policy" }
        ],
        rejected: [
          { source: "report description", reason: "private report text is never searched" },
          { source: "contact details", reason: "identity and contact data are never searched" }
        ]
      });
    });
    return true;
  }

  const discoveryCreate = /^\/v1\/reviewer\/reports\/([^/]+)\/discovery-runs$/.exec(path);

  if (discoveryCreate !== null && method === "POST") {
    if (!hasCsrf(request)) {
      problem(response, 403, "csrf_invalid");
      return true;
    }
    readBody(request, (body) => {
      if (body?.approved_digest !== DISCOVERY_DIGEST) {
        problem(response, 409, "query_changed");
        return;
      }
      const concepts = Array.isArray(body?.concepts) ? body.concepts : [];
      const scenario = String(concepts[0] ?? "default");
      const run_id = `0198f1a2-7b3c-4d4e-8f5a-d${String(++runCounter).padStart(11, "0")}`;
      const prefix = `e${String(runCounter).padStart(3, "0")}`;

      discoveryRuns.set(run_id, {
        report_id: discoveryCreate[1],
        scenario,
        prefix,
        reads: 0,
        status: scenario === "zz-queued" ? "queued" : "searching",
        version: 1,
        cancel_requested: false,
        dispositions: new Map()
      });
      log.push({ op: "discovery_create", concepts });
      json(response, 201, { run_id, status: "searching" });
    });
    return true;
  }

  const discoveryRun = /^\/v1\/reviewer\/discovery-runs\/([^/:]+)(?::(cancel|review))?$/.exec(path);

  if (discoveryRun !== null) {
    const run = discoveryRuns.get(discoveryRun[1]);

    if (run === undefined) {
      problem(response, 404, "not_found");
      return true;
    }
    if (method === "POST" && !hasCsrf(request)) {
      problem(response, 403, "csrf_invalid");
      return true;
    }
    if (method === "POST" && discoveryRun[2] === "cancel") {
      log.push({ op: "discovery_cancel" });
      if (["queued", "searching", "analysing"].includes(run.status)) {
        run.cancel_requested = true;
        run.status = "cancelled";
        run.version += 1;
      }
      json(response, 200, { status: run.status, cancel_requested: run.cancel_requested });
      return true;
    }
    if (method === "POST" && discoveryRun[2] === "review") {
      readBody(request, (body) => {
        log.push({ op: "discovery_review", command: body?.command });
        if (run.status !== "needs_review") {
          problem(response, 409, "conflict");
          return;
        }
        run.status = body?.command === "approve_completion" ? "complete" : "failed";
        run.failure_code = body?.command === "approve_completion" ? null : "analysis_invalid";
        run.version += 1;
        json(response, 200, { status: run.status });
      });
      return true;
    }
    if (method === "GET") {
      run.reads += 1;
      const scenario = run.scenario;

      if (scenario === "zz-down" && run.reads <= 2) {
        problem(response, 503, "dependency_unavailable");
        return true;
      }
      if (scenario === "zz-progress") {
        if (run.reads === 1) [run.status, run.version] = ["searching", 1];
        else if (run.reads === 2) [run.status, run.version] = ["analysing", 2];
        else if (run.status !== "cancelled") [run.status, run.version] = ["complete", 3];
      } else if (!run.settled && !["cancelled", "queued"].includes(run.status)) {
        run.settled = true;
        run.status =
          scenario === "zz-failed"
            ? "failed"
            : scenario === "zz-invalid"
              ? "complete"
              : "needs_review";
        run.version = 2;
      }
      if (url.searchParams.get("since_version") === String(run.version)) {
        response.writeHead(304, { "Cache-Control": "no-store" }).end();
        return true;
      }

      const failed = run.status === "failed" && scenario === "zz-failed";
      const sources =
        failed || (scenario === "zz-progress" && run.status !== "complete")
          ? []
          : scenario === "zz-cap"
            ? manySources(run.prefix, true, 10)
            : scenario === "zz-partial" || run.status === "cancelled"
              ? defaultSources(run.prefix, true).slice(0, 1)
              : defaultSources(run.prefix, true);

      for (const source of sources) {
        source.disposition = run.dispositions.get(source.source_id) ?? source.disposition;
      }

      const withAnalysis = ["complete", "needs_review"].includes(run.status) && sources.length > 0;

      json(response, 200, {
        run_id: discoveryRun[1],
        report_id: run.report_id,
        scope: "reviewer",
        status: run.status,
        version: run.version,
        created_at: "2026-09-20T09:00:00Z",
        finished_at: ["queued", "searching", "analysing"].includes(run.status)
          ? null
          : "2026-09-20T09:01:00Z",
        demo_replay: true,
        label: "discovered \u2014 not yet reviewed",
        query_text: "Abuja AMAC public works official source",
        query_policy_version: "fictional-policy-v1",
        results_found: sources.length,
        fetched_count: run.status === "searching" ? 0 : sources.length,
        analysed_count: withAnalysis ? sources.length : 0,
        cancel_requested: run.cancel_requested,
        failure_code: failed ? "provider_unavailable" : (run.failure_code ?? null),
        sources,
        analysis: withAnalysis ? analysisFor(sources, { invalid: scenario === "zz-invalid" }) : null
      });
      return true;
    }
  }

  const answerMatch = /^\/v1\/reviewer\/discovery-runs\/([^/]+)\/follow-up-answers$/.exec(path);

  if (answerMatch !== null && method === "POST") {
    if (!hasCsrf(request)) {
      problem(response, 403, "csrf_invalid");
      return true;
    }
    readBody(request, (body) => {
      // Only the shape is logged: an answer's text is never recorded, even here.
      log.push({
        op: "discovery_answer",
        kind: body?.kind,
        index: body?.question_index,
        hasText: typeof body?.answer === "string"
      });
      if (!discoveryRuns.has(answerMatch[1])) {
        problem(response, 404, "not_found");
      } else {
        json(response, 200, { acknowledged: true });
      }
    });
    return true;
  }

  const decisionMatch = /^\/v1\/reviewer\/discovered-sources\/([^/]+)\/decision$/.exec(path);

  if (decisionMatch !== null && method === "POST") {
    if (!hasCsrf(request)) {
      problem(response, 403, "csrf_invalid");
      return true;
    }
    readBody(request, (body) => {
      const owner = [...discoveryRuns.values()].find((run) =>
        decisionMatch[1].includes(run.prefix)
      );
      const current = owner?.dispositions.get(decisionMatch[1]) ?? "not_reviewed";
      const next = {
        not_reviewed: { attach: "attached", reject: "rejected", defer: "deferred" },
        deferred: { attach: "attached", reject: "rejected" },
        attached: { reconsider: "deferred" },
        rejected: { reconsider: "deferred" }
      }[current]?.[body?.command];

      log.push({ op: "source_decision", command: body?.command });
      if (owner === undefined) {
        problem(response, 404, "not_found");
      } else if (next === undefined) {
        problem(response, 409, "conflict");
      } else {
        owner.dispositions.set(decisionMatch[1], next);
        json(response, 200, {
          source_id: decisionMatch[1],
          disposition: next,
          attached_source_id: null
        });
      }
    });
    return true;
  }

  if (path === "/v1/reviewer/reports" && method === "GET") {
    const query = url.searchParams;
    const project = query.get("project");

    if (project === "zz-unavailable") {
      problem(response, 503, "dependency_unavailable");
      return true;
    }
    if (project === "zz-forbidden") {
      problem(response, 403, "forbidden");
      return true;
    }
    if (project === "zz-limited") {
      problem(response, 429, "rate_limited", { "Retry-After": "5" });
      return true;
    }

    const statuses = query.getAll("status");
    const key = JSON.stringify([
      statuses,
      query.get("risk_level"),
      query.get("concern_category"),
      project
    ]);
    const limit = Math.min(Number(query.get("limit") ?? 20), 50);
    let offset = 0;

    if (query.get("cursor") !== null) {
      const parsed = offsetFrom(query.get("cursor"), key);

      if (parsed === undefined) {
        problem(response, 400, "invalid_cursor");
        return true;
      }
      offset = parsed;
    }

    log.push({ op: "queue", filters: key });
    const matching = queue.filter(
      (item) =>
        (statuses.length === 0 || statuses.includes(item.status)) &&
        (query.get("risk_level") === null || item.risk_level === query.get("risk_level")) &&
        (query.get("concern_category") === null ||
          item.concern_category === query.get("concern_category")) &&
        (project === null || item.project_slug === project)
    );

    json(response, 200, {
      items: matching.slice(offset, offset + limit),
      next_cursor: offset + limit < matching.length ? cursorFor(offset + limit, key) : null
    });
    return true;
  }

  const detail = /^\/v1\/reviewer\/reports\/([^/]+)$/.exec(path);

  if (detail !== null && method === "GET") {
    const item = queue.find((entry) => entry.report_id === detail[1]);
    const contact = url.searchParams.get("include_contact") === "true";

    if (item === undefined) {
      problem(response, 404, "not_found");
    } else if (item.report_id === UNAVAILABLE_REPORT) {
      problem(response, 503, "dependency_unavailable");
    } else if (item.report_id === FORBIDDEN_REPORT) {
      problem(response, 403, "forbidden");
    } else if (contact && item.report_id === NO_CONTACT_CAPABILITY) {
      log.push({ op: "detail", contact: true, denied: true });
      problem(response, 403, "forbidden");
    } else {
      log.push({ op: "detail", contact });
      json(response, 200, detailFor(item, contact));
    }
    return true;
  }

  const notesMatch = /^\/v1\/reviewer\/reports\/([^/]+)\/notes$/.exec(path);

  if (notesMatch !== null) {
    const all = notes.get(notesMatch[1]) ?? [];

    if (method === "GET") {
      const cursor = Number(url.searchParams.get("cursor") ?? 0);
      const limit = Math.min(Number(url.searchParams.get("limit") ?? 20), 50);

      json(response, 200, {
        items: all.slice(cursor, cursor + limit),
        next_cursor: cursor + limit < all.length ? String(cursor + limit) : null
      });
      return true;
    }
    if (method === "POST") {
      if (!hasCsrf(request)) {
        problem(response, 403, "csrf_invalid");
        return true;
      }
      readBody(request, (body) => {
        const text = String(body?.body ?? "");

        log.push({ op: "note_create" });
        if (text.includes("zz-fail")) {
          problem(response, 503, "dependency_unavailable");
        } else if (/<[a-z/]/i.test(text)) {
          problem(response, 422, "markup_not_allowed");
        } else {
          const note = {
            note_id: nextId("c"),
            created_at: "2026-09-20T09:00:00Z",
            author: "reviewer-demo",
            body: text
          };

          notes.set(notesMatch[1], [...all, note]);
          json(response, 201, { note_id: note.note_id, created_at: note.created_at });
        }
      });
      return true;
    }
  }

  const evidenceMatch = /^\/v1\/reviewer\/reports\/([^/]+)\/evidence\/([^/]+)\/content$/.exec(path);

  if (evidenceMatch !== null && method === "GET") {
    log.push({ op: "evidence_download" });
    response.writeHead(200, {
      "Content-Type": "image/jpeg",
      "Content-Disposition": 'attachment; filename="evidence-1.jpg"',
      "X-Content-Type-Options": "nosniff",
      "X-Evidence-Scan-State": "not_scanned_demo",
      "Cache-Control": "no-store"
    });
    response.end(Buffer.from("fictional-image-bytes"));
    return true;
  }

  const askMatch = /^\/v1\/reviewer\/reports\/([^/]+)\/follow-up-questions$/.exec(path);

  if (askMatch !== null && method === "POST") {
    if (!hasCsrf(request)) {
      problem(response, 403, "csrf_invalid");
      return true;
    }
    readBody(request, (body) => {
      const question = {
        question_id: nextId("d"),
        question: String(body?.question ?? ""),
        asked_at: "2026-09-20T09:00:00Z",
        withdrawn: false,
        answer_kind: null,
        answer: null
      };

      log.push({ op: "question_create" });
      questions.set(askMatch[1], [...(questions.get(askMatch[1]) ?? []), question]);
      json(response, 201, { question_id: question.question_id });
    });
    return true;
  }

  const withdrawMatch =
    /^\/v1\/reviewer\/reports\/([^/]+)\/follow-up-questions\/([^/]+):withdraw$/.exec(path);

  if (withdrawMatch !== null && method === "POST") {
    if (!hasCsrf(request)) {
      problem(response, 403, "csrf_invalid");
      return true;
    }
    log.push({ op: "question_withdraw" });
    questions.set(
      withdrawMatch[1],
      (questions.get(withdrawMatch[1]) ?? []).map((item) =>
        item.question_id === withdrawMatch[2] ? { ...item, withdrawn: true } : item
      )
    );
    response.writeHead(204, { "Cache-Control": "no-store" }).end();
    return true;
  }

  const transition = /^\/v1\/reviewer\/reports\/([^/]+)\/status-transitions$/.exec(path);

  if (transition !== null && method === "POST") {
    if (!hasCsrf(request)) {
      problem(response, 403, "csrf_invalid");
      return true;
    }
    readBody(request, (body) => {
      const source = queue.find((entry) => entry.report_id === transition[1]);

      if (source === undefined) {
        problem(response, 404, "not_found");
        return;
      }

      const item = current(source);

      log.push({ op: "transition", command: body?.command });
      if (RACE_IDS.has(item.report_id) && !raced.has(item.report_id)) {
        raced.add(item.report_id);
        changes.set(item.report_id, {
          status: item.status,
          version: item.version + 1,
          at: "2026-09-20T08:00:00Z",
          events: []
        });
        problem(response, 409, "report_version_conflict");
        return;
      }
      if (body?.expected_version !== item.version || body?.expected_status !== item.status) {
        problem(response, 409, "report_version_conflict");
        return;
      }

      const to = MACHINE[item.status]?.[body?.command];

      if (to === undefined) {
        problem(response, 409, "report_status_transition_not_allowed");
        return;
      }
      if (body.command === "reopen" && !body.internal_reason) {
        problem(response, 422, "validation_failed");
        return;
      }

      const version = item.version + 1;
      const previous = changes.get(item.report_id)?.events ?? [];

      changes.set(item.report_id, {
        status: to,
        version,
        at: "2026-09-20T09:30:00Z",
        events: [
          ...previous,
          {
            event_id: nextId("e"),
            previous_status: item.status,
            new_status: to,
            public_message: body.reporter_message ?? "Standard fictional message.",
            actor_type: "reviewer",
            occurred_at: "2026-09-20T09:30:00Z",
            internal_reason: body.internal_reason ?? null
          }
        ]
      });
      json(response, 200, {
        report_id: item.report_id,
        previous_status: item.status,
        status: to,
        version,
        occurred_at: "2026-09-20T09:30:00Z",
        published: false
      });
    });
    return true;
  }

  const draftsMatch = /^\/v1\/reviewer\/reports\/([^/]+)\/public-updates$/.exec(path);

  if (draftsMatch !== null) {
    const source = queue.find((entry) => entry.report_id === draftsMatch[1]);

    if (source === undefined) {
      problem(response, 404, "not_found");
      return true;
    }
    if (method === "GET") {
      json(response, 200, {
        items: (drafts.get(source.report_id) ?? []).map((draft) => ({
          public_update_id: draft.id,
          state: draft.state,
          created_at: draft.created_at
        }))
      });
      return true;
    }
    if (method === "POST") {
      if (!hasCsrf(request)) {
        problem(response, 403, "csrf_invalid");
        return true;
      }
      readBody(request, (body) => {
        log.push({ op: "draft_create" });
        if (current(source).status !== "verified_for_public_update") {
          problem(response, 409, "public_update_report_not_verified");
          return;
        }
        if (
          typeof body?.statement !== "string" ||
          body.statement.length < 10 ||
          !Array.isArray(body.citations) ||
          body.citations.length < 1 ||
          body.citations.length > 5
        ) {
          problem(response, 422, "validation_failed");
          return;
        }

        const draft = {
          id: nextId("f"),
          state: "draft",
          created_at: "2026-09-20T09:00:00Z",
          update: {
            id: nextId("9"),
            statement: body.statement,
            effective_on: body.effective_on,
            last_checked_on: body.last_checked_on ?? null,
            verification_state: body.verification_state,
            information_class: "official_source",
            ai_generated: false,
            citations: body.citations.map((entry, index) => ({
              canonical_url: "https://example.org/synthetic/published",
              information_class: "official_source",
              location_label: entry.location_label,
              passage: entry.passage,
              publisher: "Synthetic Publisher",
              retrieved_at: "2026-09-01T09:00:00Z",
              source_id: `0198f1a2-7b3c-4d4e-8f5a-50000000000${index + 1}`,
              source_version_id: entry.source_version_id,
              source_title: "Synthetic bulletin",
              source_type: "government_publication"
            }))
          }
        };

        drafts.set(source.report_id, [...(drafts.get(source.report_id) ?? []), draft]);
        json(response, 201, previewOf(draft, source));
      });
      return true;
    }
  }

  const draftMatch =
    /^\/v1\/reviewer\/reports\/([^/]+)\/public-updates\/([^/:]+)(?::(publish|withdraw))?$/.exec(
      path
    );

  if (draftMatch !== null) {
    const source = queue.find((entry) => entry.report_id === draftMatch[1]);
    const draft = (drafts.get(draftMatch[1]) ?? []).find((entry) => entry.id === draftMatch[2]);

    if (source === undefined || draft === undefined) {
      problem(response, 404, "not_found");
      return true;
    }
    if (method === "GET" && draftMatch[3] === undefined) {
      json(response, 200, previewOf(draft, source));
      return true;
    }
    if (method === "POST" && !hasCsrf(request)) {
      problem(response, 403, "csrf_invalid");
      return true;
    }
    if (method === "POST" && draftMatch[3] === "withdraw") {
      log.push({ op: "draft_withdraw" });
      draft.state = "withdrawn";
      response.writeHead(204, { "Cache-Control": "no-store" }).end();
      return true;
    }
    if (method === "POST" && draftMatch[3] === "publish") {
      readBody(request, (body) => {
        const preview = previewOf(draft, source);

        log.push({ op: "publish", digest: typeof body?.preview_digest });
        if (draft.state !== "draft") {
          problem(response, 409, "public_update_not_draft");
        } else if (current(source).status !== "verified_for_public_update") {
          problem(response, 409, "public_update_report_not_verified");
        } else if (body?.preview_digest !== preview.preview_digest) {
          problem(response, 409, "preview_stale");
        } else if (!preview.can_publish) {
          problem(response, 422, "publication_incomplete");
        } else {
          draft.state = "published";
          published.set(source.project_slug, [...publishedFor(source.project_slug), draft.update]);
          json(response, 200, {
            public_update_id: draft.id,
            project_slug: source.project_slug,
            published_at: "2026-09-20T10:00:00Z"
          });
        }
      });
      return true;
    }
  }

  return false;
}
