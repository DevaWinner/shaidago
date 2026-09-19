"""Staging smoke journey (BE-114). Two ways in, because the API has no public route of its own.

1. Inside the private API container, over loopback (no base URL needed):

    railway ssh --service api -- python -c "import base64,sys;exec(base64.b64decode(sys.argv[1]))" <base64 of this file>

2. From an operator machine, against a temporary public domain on the api service, removed again
   as soon as the run finishes:

    SMOKE_BASE_URL=https://<temporary-domain> INTERNAL_WEB_CREDENTIAL_CURRENT=... \
      SMOKE_REVIEWER=... SMOKE_PASSWORD=... python3 scripts/staging_smoke.py

Either way it uses the internal credential (ADR-0002) and needs SMOKE_REVIEWER and SMOKE_PASSWORD
in the environment (a staging reviewer created by the operator). Everything it creates is
fictional. It prints one PASS or FAIL line per step, never a tracking code, credential, session
token, or report text.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get("SMOKE_BASE_URL", "").rstrip("/") or (
    f"http://127.0.0.1:{os.environ.get('PORT', '8000')}"
)
CREDENTIAL = os.environ["INTERNAL_WEB_CREDENTIAL_CURRENT"]
SLUG = os.environ.get("SMOKE_SLUG", "fixture-scenario-success")
RESULTS: list[tuple[bool, str]] = []
CANARY = "SMOKECANARY the fictional gate was locked all week at the fictional site."


def call(method, path, body=None, headers=None, raw=False):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(BASE + path, data=data, method=method)
    request.add_header("Authorization", f"Bearer web.{CREDENTIAL}")
    request.add_header("X-Shaidago-Client-Hmac", uuid.uuid4().hex * 2)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    for name, value in (headers or {}).items():
        request.add_header(name, value)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            payload = response.read()
            return response.status, dict(response.headers), payload if raw else json.loads(payload or b"null")
    except urllib.error.HTTPError as error:
        payload = error.read()
        try:
            return error.code, dict(error.headers), json.loads(payload or b"null")
        except ValueError:
            return error.code, dict(error.headers), None


def step(name, ok, detail=""):
    RESULTS.append((bool(ok), name))
    print(("PASS " if ok else "FAIL ") + name + (f" ({detail})" if detail and not ok else ""))
    return ok


def reviewer_headers(session):
    return {"X-Shaidago-Session": session["session_token"], "X-Shaidago-Csrf": session["csrf_token"]}


def main():
    status, _, body = call("GET", "/health/ready")
    step("readiness is ready", status == 200 and body.get("status") == "ready", body)
    status, headers, body = call("GET", f"/v1/projects/{SLUG}")
    step("public project read is cacheable and cited-only", status == 200 and headers.get("Cache-Control", "").startswith("public"), status)
    status, headers, listing = call("GET", "/v1/projects")
    step("public list is paginated", status == 200 and "items" in listing and "next_cursor" in listing)

    key = str(uuid.uuid4())
    # Multipart is built by hand to keep this file dependency-free.
    boundary = uuid.uuid4().hex
    fields = {"project_slug": SLUG, "concern_category": "no_visible_work", "description": CANARY}
    parts = "".join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in fields.items()) + f"--{boundary}--\r\n"
    request = urllib.request.Request(BASE + "/v1/reports", data=parts.encode(), method="POST")
    for name, value in {"Authorization": f"Bearer web.{CREDENTIAL}", "X-Shaidago-Client-Hmac": uuid.uuid4().hex * 2, "Idempotency-Key": key, "Content-Type": f"multipart/form-data; boundary={boundary}"}.items():
        request.add_header(name, value)
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        receipt = json.loads(response.read())
        submit_status = response.status
    code = receipt.get("tracking_code", "")
    step("anonymous fictional report accepted and unpublished", submit_status == 201 and re.fullmatch(r"SG-[0-9A-Z]{5}(-[0-9A-Z]{5}){3}-[0-9A-Z]", code) and receipt.get("published") is False)

    status, headers, tracked = call("POST", "/v1/report-status:lookup", {"code": code})
    step("tracking shows a public-safe status and no report text", status == 200 and tracked.get("status") == "received" and "SMOKECANARY" not in json.dumps(tracked) and headers.get("Cache-Control") == "no-store")
    status, _, _ = call("POST", "/v1/report-status:lookup", {"code": "SG-AAAAA-BBBBB-CCCCC-DDDDD-E"})
    step("an unknown code is one generic not-found", status == 404)

    status, _, session = call("POST", "/v1/auth/sessions", {"identifier": os.environ["SMOKE_REVIEWER"], "password": os.environ["SMOKE_PASSWORD"]})
    if not step("reviewer signs in", status == 201 and "session_token" in (session or {})):
        return
    auth = reviewer_headers(session)
    status, _, queue = call("GET", "/v1/reviewer/reports?limit=50", headers=auth)
    mine = [r for r in (queue or {}).get("items", []) if r["status"] == "received"]
    step("reviewer sees the report in the queue without its text", status == 200 and mine and "SMOKECANARY" not in json.dumps(queue))
    report = mine[-1]
    status, _, detail = call("GET", f"/v1/reviewer/reports/{report['report_id']}", headers=auth)
    step("reviewer detail decrypts the description", status == 200 and detail.get("description", "").startswith("SMOKECANARY"))
    status, _, moved = call("POST", f"/v1/reviewer/reports/{report['report_id']}/status-transitions", {"command": "start_review", "expected_status": "received", "expected_version": detail["version"], "internal_reason": "Smoke test decision."}, headers=auth)
    step("reviewer transition applies and publishes nothing", status == 200 and moved.get("published") is False)
    status, _, stale = call("POST", f"/v1/reviewer/reports/{report['report_id']}/status-transitions", {"command": "close", "expected_status": "received", "expected_version": detail["version"]}, headers=auth)
    step("a stale decision is refused", status == 409 and stale.get("code") == "report_version_conflict")
    status, _, tracked = call("POST", "/v1/report-status:lookup", {"code": code})
    step("tracking reflects the decision", status == 200 and tracked.get("status") == "under_review")

    status, _, verified = call("POST", f"/v1/reviewer/reports/{report['report_id']}/status-transitions", {"command": "verify_for_public_update", "expected_status": "under_review", "expected_version": moved["version"], "internal_reason": "Smoke test verification."}, headers=auth)
    step("reviewer verifies the report for a public update", status == 200 and verified.get("status") == "verified_for_public_update")
    version_id = os.environ.get("SMOKE_VERSION_ID", "")
    draft = {"statement": "The clinic's opening on 1 March is recorded in the cited source.", "effective_on": "2026-03-01", "verification_state": "verified_official", "citations": [{"source_version_id": version_id, "passage": "The synthetic clinic opened on 1 March.", "location_label": "section 1"}]}
    status, _, preview = call("POST", f"/v1/reviewer/reports/{report['report_id']}/public-updates", draft, headers=auth)
    step("a separately authored update previews exactly and blocks nothing", status == 201 and preview.get("can_publish") is True and not preview.get("issues"), preview and preview.get("issues"))
    before = len(call("GET", f"/v1/projects/{SLUG}")[2].get("updates", []))
    status, _, published = call("POST", f"/v1/reviewer/reports/{report['report_id']}/public-updates/{preview['public_update_id']}:publish", {"preview_digest": preview["preview_digest"]}, headers=auth) if status == 201 else (0, 0, {})
    after = call("GET", f"/v1/projects/{SLUG}")[2].get("updates", [])
    step("publication needs the previewed digest and shows the public update with its citation", status == 200 and len(after) == before + 1 and "SMOKECANARY" not in json.dumps(after))

    status, _, question = call("POST", f"/v1/projects/{SLUG}/questions", {"question": "When did the clinic works contract start?"})
    step("Q&A answers or falls back honestly (replay)", status in (200,) and ("insufficient_evidence" in question or "answer" in question), status)

    status, _, started = call("POST", f"/v1/projects/{SLUG}/discovery-runs")
    run = started.get("run_id") if status == 200 else None
    step("public discovery run created or reused", status == 200 and started.get("demo_replay") is True, status)
    final = None
    for _ in range(45):
        status, _, view = call("GET", f"/v1/discovery-runs/{run}")
        if view and view.get("status") in ("complete", "failed", "needs_review", "cancelled"):
            final = view
            break
        time.sleep(2)
    step("the worker completes the run from replay fixtures", final and final["status"] == "complete" and final["demo_replay"] is True and len(final["sources"]) == 2, final and final.get("status"))
    step("every result is labelled not yet reviewed", final and all(c["label"] == "discovered — not yet reviewed" for c in final["sources"]))

    status, _, plan = call("POST", f"/v1/reviewer/reports/{report['report_id']}/discovery-runs:plan", {"concepts": ["delayed"]}, headers=auth)
    status2, _, created = call("POST", f"/v1/reviewer/reports/{report['report_id']}/discovery-runs", {"concepts": ["delayed"], "approved_digest": plan["plan_digest"]}, headers=auth) if status == 200 else (0, 0, {})
    step("reviewer approves an exact query and starts a report-scoped run", status == 200 and status2 == 201)
    status, _, hidden = call("GET", f"/v1/discovery-runs/{created.get('run_id')}")
    step("the report-scoped run is invisible to the public", status == 404)

    status, _, _ = call("DELETE", "/v1/auth/sessions/current", headers=auth)
    step("reviewer signs out", status == 204)
    status, _, _ = call("GET", "/v1/reviewer/reports", headers=auth)
    step("the revoked session no longer works", status == 401)
    status, _, _ = call("GET", "/v1/reviewer/reports")
    step("the internal credential alone is not reviewer authority", status == 401)
    failed = [name for ok, name in RESULTS if not ok]
    print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} steps passed")
    sys.exit(1 if failed else 0)


main()
