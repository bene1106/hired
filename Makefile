# Hired. — convenience targets. Optional; the underlying commands are
# documented in CLAUDE.md and run fine standalone.

.PHONY: eval bias-audit test backend-test frontend-test openapi openapi-check

# Regenerate the committed OpenAPI schema from the live FastAPI app.
# Run after any route change; CI fails if the committed file is stale.
openapi:
	cd backend && HIRED_DB_URL=sqlite:///./scratch-openapi.db uv run python ../scripts/gen_openapi.py

# CI guard: regenerate into a temp file and diff against the committed one.
openapi-check: openapi
	git diff --exit-code docs/api.openapi.json

# Run scoring eval against the configured provider.
# Pass PROVIDER=mock or PROVIDER=anthropic_api to override.
eval:
	cd backend && uv run python ../eval/run_eval.py $(if $(PROVIDER),--provider $(PROVIDER),)

# Run the name-swap bias audit. Same PROVIDER override applies.
bias-audit:
	cd backend && uv run python ../eval/bias_audit.py $(if $(PROVIDER),--provider $(PROVIDER),)

backend-test:
	cd backend && uv run pytest

frontend-test:
	cd frontend && pnpm test --run

test: backend-test frontend-test
