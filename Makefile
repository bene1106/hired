# Hired. — convenience targets. Optional; the underlying commands are
# documented in CLAUDE.md and run fine standalone.

.PHONY: eval bias-audit test backend-test frontend-test

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
