# Cross-stack judge workflows only. Package-specific scripts stay with their stack.
# Every backend target has one implementation and runs through `uv` with the frozen lockfile.

PLATFORM_DIR := services/platform
UV := uv --directory $(PLATFORM_DIR)
RUN := $(UV) run --frozen

# pytest exits 5 when a layer has no tests. That is accepted only for layers whose first
# tests arrive in a later task; the target says so instead of reporting a pass silently.
define run_layer
$(RUN) pytest $(1) -m "not live"; status=$$?; \
if [ $$status -eq 5 ]; then echo "backend: no tests collected yet for $(1)"; exit 0; fi; \
exit $$status
endef

.DEFAULT_GOAL := help
.PHONY: help backend-sync backend-format backend-format-check backend-lint backend-typecheck \
	backend-unit backend-integration backend-contract backend-security backend-test backend-verify \
	openapi-generate openapi-check

help:
	@echo "Backend targets: backend-sync backend-format backend-format-check backend-lint"
	@echo "  backend-typecheck backend-unit backend-integration backend-contract"
	@echo "  backend-security backend-test backend-verify openapi-generate openapi-check"

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
	@$(call run_layer,tests/unit)

backend-integration:
	@$(call run_layer,tests/integration)

backend-contract:
	@$(call run_layer,tests/contract)

backend-security:
	$(RUN) bandit -q -r src
	$(RUN) pip-audit --skip-editable

# All deterministic backend tests; live provider tests are excluded.
backend-test:
	@$(call run_layer,tests)

# The contract is generated from the FastAPI app with synthetic settings: no environment,
# database, or provider is needed.
openapi-generate:
	$(RUN) python -m shaidago.api.openapi --output ../../contracts/openapi.json

openapi-check:
	$(RUN) python -m shaidago.api.openapi --output ../../contracts/openapi.json --check

backend-verify: backend-sync backend-format-check backend-lint backend-typecheck backend-security \
	openapi-check backend-test
