"""Sets the staging service variables on Railway without printing any secret (BE-111).

    PATH="$HOME/.railway/bin:$PATH" python3 scripts/railway_staging_variables.py

Run from a directory linked to the staging project (``railway link``). It generates fresh random
keys and role passwords, reads the Postgres, Redis, and bucket values from Railway itself, and sets
the variables for ``api``, ``worker``, and ``migrate`` with ``--skip-deploys``. Re-running rotates
every generated secret, so do it only on a new environment or as a deliberate rotation. Nothing it
handles is written to disk or printed: only variable *names* are reported.
"""

import base64
import json
import secrets
import subprocess
import sys

HOST = "postgres.railway.internal"
DATABASE = "shaidago"
ROLES = {
    "shaidago_public": "DB_PASSWORD_PUBLIC",
    "shaidago_reviewer": "DB_PASSWORD_REVIEWER",
    "shaidago_worker": "DB_PASSWORD_WORKER",
    "shaidago_readonly_ops": "DB_PASSWORD_READONLY_OPS",
}


def railway(*args: str) -> str:
    done = subprocess.run(["railway", *args], capture_output=True, text=True, check=False)  # noqa: S603, S607
    if done.returncode != 0:
        sys.exit(f"railway {' '.join(args[:3])} failed")
    return done.stdout


def variables(service: str) -> dict[str, str]:
    return json.loads(railway("variable", "list", "--service", service, "--json"))  # type: ignore[no-any-return]


def key() -> str:
    return base64.b64encode(secrets.token_bytes(32)).decode()


def main() -> None:
    postgres = variables("postgres")
    owner_url = f"postgresql+psycopg://{postgres['POSTGRES_USER']}:{postgres['POSTGRES_PASSWORD']}@{HOST}:5432/{DATABASE}"
    passwords = {variable: secrets.token_urlsafe(24) for variable in ROLES.values()}

    def role_url(role: str) -> str:
        return f"postgresql+psycopg://{role}:{passwords[ROLES[role]]}@{HOST}:5432/{DATABASE}"

    redis = variables("Redis")
    redis_url = f"redis://:{redis['REDISPASSWORD']}@{redis['REDISHOST']}:{redis['REDISPORT']}/0"
    bucket = json.loads(railway("bucket", "credentials", "--bucket", "shaidago-evidence-staging", "--json"))

    runtime = {
        "APP_ENV": "staging",
        "SERVICE_NAME": "shaidago-platform",
        "LOG_LEVEL": "INFO",
        # Settings require DATABASE_URL to be present; the running services never connect with it,
        # so it carries the worker role, not the owner (the owner exists only on `migrate`).
        "DATABASE_URL": role_url("shaidago_worker"),
        "DATABASE_URL_PUBLIC": role_url("shaidago_public"),
        "DATABASE_URL_REVIEWER": role_url("shaidago_reviewer"),
        "DATABASE_URL_WORKER": role_url("shaidago_worker"),
        "REDIS_URL": redis_url,
        "OBJECT_STORE_ENDPOINT_URL": bucket["endpoint"],
        "OBJECT_STORE_BUCKET": bucket["bucketName"],
        "OBJECT_STORE_ACCESS_KEY_ID": bucket["accessKeyId"],
        "OBJECT_STORE_SECRET_ACCESS_KEY": bucket["secretAccessKey"],
        "OBJECT_STORE_BUCKET_IS_PUBLIC": "false",
        "SCANNER_MODE": "not_deployed",  # the hosted demo has no scanner; files are labelled as such
        "ENCRYPTION_KEKS": f"kek-staging-1={key()}",
        "ENCRYPTION_ACTIVE_KEK_VERSION": "kek-staging-1",
        "TRACKING_PEPPERS": f"pepper-staging-1={key()}",
        "TRACKING_ACTIVE_PEPPER_VERSION": "pepper-staging-1",
        "IDEMPOTENCY_PEPPER": key(),
        "CURSOR_HMAC_KEY": key(),
        "SESSION_HMAC_KEY": key(),
        "INTERNAL_WEB_CREDENTIAL_CURRENT": secrets.token_urlsafe(40),
        "SESSION_COOKIE_NAME": "__Host-sg_session",
        "SESSION_COOKIE_SECURE": "true",
        "PROVIDER_MODE": "replay",
        "RAILWAY_DOCKERFILE_PATH": "services/platform/Dockerfile",
    }
    migrate = {
        "DATABASE_URL": owner_url,
        "RAILWAY_DOCKERFILE_PATH": "services/platform/Dockerfile",
        **passwords,
    }
    for service, values in (("api", runtime), ("worker", runtime), ("migrate", migrate)):
        pairs = [f"{name}={value}" for name, value in values.items()]
        railway("variable", "set", "--service", service, "--skip-deploys", *pairs)
        print(f"{service}: set {len(pairs)} variables ({', '.join(values)})")  # noqa: T201


if __name__ == "__main__":
    main()
