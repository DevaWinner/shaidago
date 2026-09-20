#!/usr/bin/env bash
# Builds the web image and proves its properties (FE-160). Needs Docker. It contacts no private API
# and uses only fictional values. Prints only pass/fail lines.
#   scripts/verify-web-container.sh            # everything except the Trivy scan
#   TRIVY=1 scripts/verify-web-container.sh    # also scan the image (pulls aquasec/trivy)
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE="${IMAGE:-shaidago-web:verify}"
NAME=sg-verify-web
REVISION="$(git rev-parse HEAD)"
trap 'docker rm -f $NAME >/dev/null 2>&1 || true' EXIT
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; exit 1; }

docker build -q -f apps/web/Dockerfile --build-arg "REVISION=$REVISION" \
  --build-arg "CREATED=$(date -u +%Y-%m-%dT%H:%M:%SZ)" -t "$IMAGE" . >/dev/null
pass "image builds with no private API and no secret"

[ "$(docker run --rm --entrypoint id "$IMAGE" -u)" = "10001" ] && pass "runs as a non-root user" || fail "user is root"
[ "$(docker inspect "$IMAGE" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')" = "$REVISION" ] \
  && pass "OCI revision label is the commit" || fail "revision label"
docker run --rm --entrypoint sh "$IMAGE" -c '
  test ! -d /app/apps/web/tests && test ! -e /app/.env &&
  test -z "$(find /app/apps/web/.next/static /app/apps/web/public -name "*.map" 2>/dev/null)" &&
  test -z "$(find /app -name ".env*" -o -name "*.pem" -o -name "*.key" 2>/dev/null)" &&
  ! command -v npm >/dev/null && ! command -v corepack >/dev/null && ! command -v git >/dev/null' \
  && pass "no tests, source maps in public files, credentials, package managers, or git in the final image" \
  || fail "unwanted files or tools in the image"

CREDENTIAL="shaida-go-container-verify-credential-not-a-secret"
docker run -d --name "$NAME" --read-only --tmpfs /app/apps/web/.next/cache --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop ALL --security-opt no-new-privileges -p 127.0.0.1:18300:3000 \
  -e APP_ENV=test -e API_INTERNAL_URL=http://api.internal.invalid:8000 \
  -e "INTERNAL_WEB_CREDENTIAL_CURRENT=$CREDENTIAL" "$IMAGE" >/dev/null
for _ in $(seq 1 30); do curl -fsS http://127.0.0.1:18300/health/live >/dev/null 2>&1 && break; sleep 1; done
curl -fsS http://127.0.0.1:18300/health/live >/dev/null \
  && pass "answers liveness with a read-only root filesystem, no capabilities, and no privilege escalation" || fail "liveness"
[ "$(curl -s http://127.0.0.1:18300/health/ready)" = '{"status":"ready"}' ] && pass "reports its own configuration ready without calling the API" || fail "readiness"
[ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18300/en/offline)" = "200" ] \
  && pass "serves a static page with the private API unreachable" || fail "static page"
HEADERS="$(curl -s -D - -o /dev/null http://127.0.0.1:18300/en/offline)"
for header in "content-security-policy: default-src 'self'" "x-frame-options: DENY" "x-content-type-options: nosniff" "referrer-policy: same-origin" "permissions-policy:"; do
  echo "$HEADERS" | grep -qi "$header" || fail "missing header $header"
done
pass "security headers are present"
echo "$HEADERS" | grep -qi "strict-transport-security" && fail "HSTS sent over local HTTP" || pass "no HSTS over local HTTP"
docker logs "$NAME" 2>&1 | grep -q "$CREDENTIAL" && fail "the credential appears in the logs" || pass "the internal credential is not logged"

# Termination: the container must exit 0 on SIGTERM without dropping a download that is in flight.
# (Draining a genuinely slow request is proven by apps/web/tests/unit/serve-shutdown.test.ts; a
# static file is buffered by the kernel, so this only proves the signal is handled and the exit is clean.)
# The largest script the offline page names, so the transfer is still running when the signal comes.
CHUNK=""; BIGGEST=0
for candidate in $(curl -s http://127.0.0.1:18300/en/offline | grep -o '/_next/static/chunks/[^"]*\.js' | sort -u); do
  SIZE="$(curl -sI "http://127.0.0.1:18300$candidate" | tr -d '\r' | awk 'tolower($1)=="content-length:" {print $2}')"
  if [ "${SIZE:-0}" -gt "$BIGGEST" ]; then BIGGEST="$SIZE"; CHUNK="$candidate"; fi
done
[ "$BIGGEST" -gt 100000 ] || fail "no script large enough to test draining (largest $BIGGEST bytes)"
OUT="$(mktemp)"
curl -s --limit-rate 60k -o "$OUT" -w '%{http_code} %{size_download}' "http://127.0.0.1:18300$CHUNK" > "$OUT.result" &
DOWNLOAD=$!
sleep 1
START=$(date +%s)
docker stop -t 30 "$NAME" >/dev/null
ELAPSED=$(( $(date +%s) - START ))
wait "$DOWNLOAD" || true
CODE="$(docker inspect "$NAME" --format '{{.State.ExitCode}}')"
read -r HTTP BYTES < "$OUT.result" || true
[ "$CODE" = "0" ] && [ "${HTTP:-0}" = "200" ] && [ "${BYTES:-0}" -ge "$BIGGEST" ] && [ "$ELAPSED" -le 25 ] \
  && pass "SIGTERM is handled: the in-flight download completes and the container exits 0 in ${ELAPSED}s" \
  || fail "graceful termination (exit $CODE, http ${HTTP:-none}, ${BYTES:-0} bytes, ${ELAPSED}s)"
rm -f "$OUT" "$OUT.result"
docker rm "$NAME" >/dev/null

if [ "${TRIVY:-0}" = "1" ]; then
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image \
    --quiet --severity HIGH,CRITICAL --exit-code 1 --ignore-unfixed "$IMAGE" >/dev/null \
    && pass "Trivy finds no fixable high or critical vulnerability" || fail "Trivy findings"
fi
echo "web container verified for $REVISION"
