#!/usr/bin/env bash
# Builds the backend image and proves its properties (BE-110). Needs Docker and the local Compose
# services (`make infra-up-core`). Prints only pass/fail lines; never prints an environment value.
#   scripts/verify-container.sh            # everything except the Trivy scan
#   TRIVY=1 scripts/verify-container.sh    # also scan the image (pulls aquasec/trivy)
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE="${IMAGE:-shaidago-platform:verify}"
REVISION="$(git rev-parse HEAD)"
ENV_FILE="$(mktemp)"
trap 'rm -f "$ENV_FILE"; docker rm -f sg-verify-api sg-verify-worker >/dev/null 2>&1 || true' EXIT
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; exit 1; }

docker build -q -f services/platform/Dockerfile --build-arg "REVISION=$REVISION" \
  --build-arg "CREATED=$(date -u +%Y-%m-%dT%H:%M:%SZ)" -t "$IMAGE" . >/dev/null
pass "image builds"

[ "$(docker run --rm "$IMAGE" id -u)" = "10001" ] && pass "runs as a non-root user" || fail "user is root"
[ "$(docker inspect "$IMAGE" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')" = "$REVISION" ] \
  && pass "OCI revision label is the commit" || fail "revision label"
docker run --rm "$IMAGE" python - <<'PY' || fail "final image has build or dev tooling"
import importlib.util as u, shutil, sys
bad = [n for n in ("pytest", "ruff", "pyright", "hypothesis", "schemathesis", "bandit") if u.find_spec(n)]
bad += [t for t in ("gcc", "cc", "uv", "git", "curl") if shutil.which(t)]
sys.exit(1 if bad else 0)
PY
pass "no compiler, uv, git, curl, or development dependencies in the final image"
docker run --rm "$IMAGE" sh -c 'test ! -e /app/.env && test -z "$(find /app -not -path "*/.venv/*" \( -name ".env*" -o -name "*.pem" -o -name "*.key" \) 2>/dev/null)"' \
  && pass "no credentials or key files in the image" || fail "credential-like files in the image"

# Environment for the containers: the local Compose services, reached through the host.
python3 - "$ENV_FILE" <<'PY'
import re, sys
out = []
for line in open(".env", encoding="utf-8"):
    if re.match(r"^[A-Z][A-Z0-9_]*=", line):
        out.append(line.rstrip("\n").replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal"))
# An older local .env may predate DATABASE_URL_WORKER: build it from the worker role's password.
values = dict(line.split("=", 1) for line in out)
if "DATABASE_URL_WORKER" not in values and "DB_PASSWORD_WORKER" in values:
    base = values["DATABASE_URL_REVIEWER"]
    out.append("DATABASE_URL_WORKER=" + re.sub(r"//[^:]+:[^@]+@", f"//shaidago_worker:{values['DB_PASSWORD_WORKER']}@", base))
# The Compose ClamAV is published on 53310; the container reaches it through the host.
out += ["CLAMD_HOST=host.docker.internal", "CLAMD_PORT=53310"]
open(sys.argv[1], "w", encoding="utf-8").write("\n".join(out) + "\n")
PY
CREDENTIAL="$(grep -E '^INTERNAL_WEB_CREDENTIAL_CURRENT=' .env | cut -d= -f2-)"

HARDEN=(--read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m --cap-drop ALL --security-opt no-new-privileges --add-host host.docker.internal:host-gateway)
docker run -d --name sg-verify-api "${HARDEN[@]}" --env-file "$ENV_FILE" -p 18000:8000 "$IMAGE" >/dev/null
for _ in $(seq 1 40); do
  curl -fsS http://127.0.0.1:18000/health/live >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS http://127.0.0.1:18000/health/live >/dev/null && pass "API answers liveness with a read-only root filesystem, no capabilities, and no privilege escalation" || fail "API liveness"
STATUS="$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer web.${CREDENTIAL}" http://127.0.0.1:18000/health/ready)"
[ "$STATUS" = "200" ] && pass "API is ready against the local services (200)" || fail "API readiness ($STATUS)"
[ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18000/v1/projects)" = "401" ] && pass "an unauthenticated request is refused (401)" || fail "unauthenticated request"
START=$(date +%s)
docker stop -t 30 sg-verify-api >/dev/null
ELAPSED=$(( $(date +%s) - START ))
CODE="$(docker inspect sg-verify-api --format '{{.State.ExitCode}}')"
[ "$CODE" = "0" ] && [ "$ELAPSED" -le 15 ] && pass "SIGTERM drains and exits 0 in ${ELAPSED}s" || fail "graceful termination (exit $CODE after ${ELAPSED}s)"
docker rm sg-verify-api >/dev/null

docker run -d --name sg-verify-worker "${HARDEN[@]}" --env-file "$ENV_FILE" "$IMAGE" \
  dramatiq shaidago.worker.entry --queues discovery --processes 1 --threads 2 >/dev/null
for _ in $(seq 1 40); do
  docker logs sg-verify-worker 2>&1 | grep -q "Worker process is ready" && break
  sleep 1
done
docker logs sg-verify-worker 2>&1 | grep -q "Worker process is ready" && pass "the worker starts from the same image and connects" || fail "worker start"
START=$(date +%s)
docker stop -t 30 sg-verify-worker >/dev/null
ELAPSED=$(( $(date +%s) - START ))
[ "$(docker inspect sg-verify-worker --format '{{.State.ExitCode}}')" = "0" ] && [ "$ELAPSED" -le 20 ] && pass "the worker drains and exits 0 in ${ELAPSED}s" || fail "worker termination"
docker rm sg-verify-worker >/dev/null

DB="shaidago_verify_$RANDOM"
docker exec shaidago-postgres-1 psql -U shaidago -d postgres -qc "CREATE DATABASE $DB" >/dev/null
OWNER_URL="$(grep -E '^DATABASE_URL=' "$ENV_FILE" | cut -d= -f2- | sed "s#/shaidago\$#/$DB#")"
docker run --rm "${HARDEN[@]}" -e "DATABASE_URL=$OWNER_URL" "$IMAGE" alembic upgrade head >/dev/null 2>&1 \
  && pass "the migration job runs from the same image against an empty database" || { docker exec shaidago-postgres-1 psql -U shaidago -d postgres -qc "DROP DATABASE $DB WITH (FORCE)" >/dev/null; fail "migration job"; }
docker exec shaidago-postgres-1 psql -U shaidago -d postgres -qc "DROP DATABASE $DB WITH (FORCE)" >/dev/null

if [ "${TRIVY:-0}" = "1" ]; then
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image \
    --quiet --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 "$IMAGE" \
    && pass "Trivy: no fixable high or critical vulnerability" || fail "Trivy found fixable high or critical vulnerabilities"
fi
echo "verified image $IMAGE at $REVISION"
