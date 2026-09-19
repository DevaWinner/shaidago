# Cross-stack judge workflows only. Package-specific scripts stay with their stack.
# Every backend target has one implementation and runs through `uv` with the frozen lockfile.

PLATFORM_DIR := services/platform
UV := uv --directory $(PLATFORM_DIR)
RUN := $(UV) run --frozen

# Integration tests need the Compose services (`make infra-up-core`) and read their connection
# settings from the infrastructure env file. Unit and contract tests stay hermetic.
INFRA_ENV ?= .env
ENV_FILE_FLAG := $(if $(wildcard $(INFRA_ENV)),--env-file $(abspath $(INFRA_ENV)),)
RUN_WITH_ENV := $(UV) run --frozen $(ENV_FILE_FLAG)

# pytest exits 5 when a layer has no tests. That is accepted only for layers whose first
# tests arrive in a later task; the target says so instead of reporting a pass silently.
define run_layer
$(1) pytest $(2) -m "not live"; status=$$?; \
if [ $$status -eq 5 ]; then echo "backend: no tests collected yet for $(2)"; exit 0; fi; \
exit $$status
endef

# Local infrastructure. Every command names the fixed project "shaidago", so it can only see or
# change ShaidaGo's own containers, networks, and volumes.
COMPOSE := docker compose --project-name shaidago --env-file $(INFRA_ENV) -f infra/docker/compose.yml

.DEFAULT_GOAL := help
.PHONY: help backend-sync backend-format backend-format-check backend-lint backend-typecheck \
	backend-unit backend-integration backend-contract backend-security backend-test backend-verify \
	openapi-generate openapi-check migrate db-roles infra-up infra-up-core infra-down infra-logs infra-clean infra-check-env

help:
	@echo "Backend targets: backend-sync backend-format backend-format-check backend-lint"
	@echo "  backend-typecheck backend-unit backend-integration backend-contract"
	@echo "  backend-security backend-test backend-verify openapi-generate openapi-check"
	@echo "Database targets: migrate db-roles (need make infra-up-core first)"
	@echo "Infrastructure targets: infra-up infra-up-core infra-down infra-logs infra-clean"
	@echo "  (need $(INFRA_ENV); copy .env.example first)"

backend-sync:
	$(UV) sync --all-groups --frozen

backend-format:
	$(RUN) ruff format .

backend-format-check:
	$(RUN) ruff format --check .

backend-lint:
	$(RUN) ruff check .

backend-typecheck:
	$(RUN) pyright

backend-unit:
	@$(call run_layer,$(RUN),tests/unit)

backend-integration:
	@$(call run_layer,$(RUN_WITH_ENV),tests/integration)

backend-contract:
	@$(call run_layer,$(RUN),tests/contract)

backend-security:
	$(RUN) bandit -q -r src
	$(RUN) pip-audit --skip-editable

# All deterministic backend tests; live provider tests are excluded.
backend-test:
	@$(call run_layer,$(RUN_WITH_ENV),tests)

# The contract is generated from the FastAPI app with synthetic settings: no environment,
# database, or provider is needed.
openapi-generate:
	$(RUN) python -m shaidago.api.openapi --output ../../contracts/openapi.json

openapi-check:
	$(RUN) python -m shaidago.api.openapi --output ../../contracts/openapi.json --check

backend-verify: backend-sync backend-format-check backend-lint backend-typecheck backend-security \
	openapi-check backend-test

# Applies Alembic revisions as the migration owner (DATABASE_URL). Idempotent.
migrate:
	$(RUN_WITH_ENV) alembic upgrade head

# Enables application-role logins from the DB_PASSWORD_* variables. Run after `make migrate`.
db-roles:
	$(RUN_WITH_ENV) python -m shaidago.db.provision

infra-check-env:
	@test -f "$(INFRA_ENV)" || { echo "infra: $(INFRA_ENV) not found; run: cp .env.example .env"; exit 1; }

# PostgreSQL, Redis, MinIO with its private bucket, and the ClamAV scanner.
# `up --wait` treats an exited one-shot container as failure, so the bucket provisioner runs
# separately after the long-running services are healthy.
infra-up: infra-check-env
	$(COMPOSE) --profile scanner up --detach --wait postgres redis minio clamav
	$(COMPOSE) run --rm minio-init

# Everything except ClamAV, which needs about 1.5-3 GB of memory.
infra-up-core: infra-check-env
	$(COMPOSE) up --detach --wait postgres redis minio
	$(COMPOSE) run --rm minio-init

# Stops containers and keeps volumes.
infra-down: infra-check-env
	$(COMPOSE) --profile scanner down --remove-orphans

infra-logs: infra-check-env
	$(COMPOSE) --profile scanner logs --tail=200

# Deletes ShaidaGo's local database, queue, object, and signature volumes. Destructive.
infra-clean: infra-check-env
	@test "$(CONFIRM_DESTROY_SHAIDAGO_DATA)" = "yes" || { \
		echo "infra-clean deletes ShaidaGo's local Docker volumes."; \
		echo "Re-run with CONFIRM_DESTROY_SHAIDAGO_DATA=yes to proceed."; exit 1; }
	$(COMPOSE) --profile scanner down --volumes --remove-orphans
