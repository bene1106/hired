# Hired. — Frontend

React + TypeScript (strict) + Tailwind + shadcn/ui scaffolding. The Tauri shell
loads this as its webview.

## Develop

```bash
pnpm install
pnpm dev               # Vite dev server on :5173
pnpm test              # Vitest, run-once
pnpm test:watch        # Vitest watch
pnpm lint              # ESLint (flat config)
pnpm typecheck         # tsc -b across app + node configs
pnpm format            # Prettier write
pnpm format:check      # Prettier check (CI)
pnpm build             # typecheck + production build into dist/
```

The dev page hits the FastAPI sidecar at `http://localhost:8765/health`. Start
the sidecar separately during Phase 1 — see `../backend/README.md`. (Sidecar
bundling into the Tauri build is deferred to Phase 6.)
