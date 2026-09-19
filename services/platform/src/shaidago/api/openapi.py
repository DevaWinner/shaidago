"""Deterministic OpenAPI generation for ``contracts/openapi.json``.

The schema depends only on route and model definitions, so it is built from fixed synthetic
settings: no real environment, credential, database, or provider is read or contacted.

    python -m shaidago.api.openapi --output ../../contracts/openapi.json           # write
    python -m shaidago.api.openapi --output ../../contracts/openapi.json --check   # verify
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from shaidago.api.app import create_app
from shaidago.api.dependencies import Dependencies
from shaidago.shared.config import load_settings

_PLACEHOLDER = "change-me"
# Placeholder values that only satisfy validation. "change-me" keys are refused outside development.
_SYNTHETIC_ENVIRON = {
    "APP_ENV": "development",
    "DATABASE_URL": "postgresql+psycopg://user:change-me@localhost:5432/openapi",
    "DATABASE_URL_PUBLIC": "postgresql+psycopg://public:change-me@localhost:5432/openapi",
    "REDIS_URL": "redis://localhost:6379/0",
    "OBJECT_STORE_ENDPOINT_URL": "http://localhost:9000",
    "OBJECT_STORE_BUCKET": "openapi-schema-only",
    "OBJECT_STORE_ACCESS_KEY_ID": _PLACEHOLDER,
    "OBJECT_STORE_SECRET_ACCESS_KEY": _PLACEHOLDER,
    "ENCRYPTION_KEKS": "kek-schema=Y2hhbmdlLW1lLWNoYW5nZS1tZS1jaGFuZ2UtbWUtMzI=",
    "ENCRYPTION_ACTIVE_KEK_VERSION": "kek-schema",
    "TRACKING_PEPPERS": "pepper-schema=Y2hhbmdlLW1lLWNoYW5nZS1tZS1jaGFuZ2UtbWUtMzI=",
    "TRACKING_ACTIVE_PEPPER_VERSION": "pepper-schema",
    "IDEMPOTENCY_PEPPER": "Y2hhbmdlLW1lLWNoYW5nZS1tZS1jaGFuZ2UtbWUtMzI=",
    "CURSOR_HMAC_KEY": "Y2hhbmdlLW1lLWNoYW5nZS1tZS1jaGFuZ2UtbWUtMzI=",
    "INTERNAL_WEB_CREDENTIAL_CURRENT": "change-me-schema-generation-credential",
    "SESSION_HMAC_KEY": "Y2hhbmdlLW1lLWNoYW5nZS1tZS1jaGFuZ2UtbWUtMzI=",
}


def build_openapi() -> dict[str, Any]:
    app = create_app(load_settings(_SYNTHETIC_ENVIRON), Dependencies())
    return app.openapi()


def render_openapi() -> str:
    return json.dumps(build_openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true", help="fail if the file differs")
    args = parser.parse_args(argv)
    rendered = render_openapi()
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.exists() else None
        if current != rendered:
            sys.stderr.write(f"{args.output} is out of date; run `make openapi-generate`\n")
            return 1
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
