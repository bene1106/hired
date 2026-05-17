# Hired. — Backend API Reference

The FastAPI sidecar listens on `127.0.0.1:8765` (overridable via `HIRED_PORT`). All endpoints are JSON; CORS is open to `tauri://localhost` and `http://localhost:*` only.

A machine-readable OpenAPI 3.1 schema is committed at [`api.openapi.json`](api.openapi.json) and is regenerated from `app.openapi()` whenever a route changes — render it with [Redoc](https://redocly.com/redoc/) or [Swagger UI](https://swagger.io/tools/swagger-ui/) for an interactive view.

## Endpoints by area

### Health

| Method | Path      | Purpose                             |
|--------|-----------|-------------------------------------|
| GET    | `/health` | Liveness + DB round-trip (no auth)  |

### Setup (onboarding)

| Method | Path                              | Purpose                                                              |
|--------|-----------------------------------|----------------------------------------------------------------------|
| GET    | `/api/setup/providers`            | UI metadata: label, `is_experimental`, `requires_api_key`, default model |
| POST   | `/api/setup/detect-providers`     | Probe for installed/configured Anthropic key, Claude Code CLI, Ollama |
| POST   | `/api/setup/test-provider`        | One round-trip per provider; returns latency + classified error kind |
| POST   | `/api/setup/select-provider`      | Persist provider + (optional) model; stores API key in OS keychain   |

### Profile

| Method | Path                          | Purpose                                                      |
|--------|-------------------------------|--------------------------------------------------------------|
| GET    | `/api/profile`                | Current profile (404 when empty)                             |
| POST   | `/api/profile`                | Partial upsert — missing fields untouched                    |
| POST   | `/api/profile/cv`             | Parse pasted CV text and upsert profile                      |
| POST   | `/api/profile/cv/upload`      | Multipart PDF upload (≤5MB, 30KB pre-LLM truncation)         |

### Jobs (feed + crawler)

| Method | Path                                    | Purpose                                                     |
|--------|-----------------------------------------|-------------------------------------------------------------|
| POST   | `/api/jobs/crawl`                       | Kick off background crawl (manual_url default; linkedin opt-in) |
| GET    | `/api/jobs/crawl/status/{job_id}`       | Poll crawl progress                                         |
| GET    | `/api/jobs/feed`                        | Ranked job feed (filter + min-score + exclude-status)       |
| POST   | `/api/jobs/{job_id}/action`             | apply / save / skip — upserts an Application row            |

### Applications (Phase 5)

| Method | Path                                                                       | Purpose                                          |
|--------|----------------------------------------------------------------------------|--------------------------------------------------|
| POST   | `/api/applications/{job_id}`                                               | Start the three-step apply pipeline (background) |
| GET    | `/api/applications/{id}/generation/{task_id}`                              | Poll per-step state                              |
| GET    | `/api/applications/{id}/materials`                                         | Latest of each material type                     |
| PUT    | `/api/applications/{id}/materials/{type}`                                  | Save a user edit                                 |
| POST   | `/api/applications/{id}/materials/{type}/regenerate`                       | Force-regenerate one material                    |
| GET    | `/api/applications`                                                        | Dashboard list (filter by status)                |
| GET    | `/api/applications/{id}`                                                   | Detail (job + materials + status)                |
| PUT    | `/api/applications/{id}/status`                                            | Update status + notes                            |
| GET    | `/api/applications/{id}/interview/questions`                               | Generate or load cached question bank + role summary |
| POST   | `/api/applications/{id}/interview/practice`                                | Submit a practice answer; returns LLM feedback   |
| GET    | `/api/applications/{id}/interview/attempts`                                | Past practice answers                            |

### Stats (Settings panel)

| Method | Path                       | Purpose                                                        |
|--------|----------------------------|----------------------------------------------------------------|
| GET    | `/api/stats/cost`          | Today + week token spend, with per-provider label              |
| GET    | `/api/stats/provider`      | Last latency, success, calls today, success rate today         |

### Data

| Method | Path             | Purpose                                                                  |
|--------|------------------|--------------------------------------------------------------------------|
| DELETE | `/api/data/all`  | Wipe every user-owned table, delete keychain entry, reset provider cache |

## Error shapes

Every endpoint returns FastAPI's default error envelope on failure:

```json
{ "detail": "Unknown application id." }
```

Provider-layer failures surface via the typed `LLMError` hierarchy (`LLMAuthError`, `LLMRateLimitError`, `LLMNetworkError`, `LLMResponseError`); `POST /api/setup/test-provider` flattens these into a stable `error_kind` string set so the UI can render friendly messages without parsing free text.

## Background tasks

- **Crawl** and **application generation** both use FastAPI `BackgroundTasks` with an in-process progress dict (`services/crawl_progress.py`, `services/generation_progress.py`). Progress resets on backend restart — acceptable for MVP per the phase notes.

## Auth

There is none. The sidecar binds to loopback only and trusts whatever process calls it. The Tauri shell is the only intended caller.
