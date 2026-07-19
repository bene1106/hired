# Hired. — Backend API Reference

The FastAPI sidecar listens on `127.0.0.1:8765` (overridable via `HIRED_PORT`). All endpoints are JSON; CORS is open to `tauri://localhost` and `http://localhost:*` only.

A machine-readable OpenAPI 3.1 schema is committed at [`api.openapi.json`](api.openapi.json), covering all **50 paths**. Regenerate it with `make openapi` after any route change — CI fails if the committed file is stale. Render it with [Redoc](https://redocly.com/redoc/) or [Swagger UI](https://swagger.io/tools/swagger-ui/) for an interactive view.

While the sidecar is running, FastAPI also serves the live schema at `/openapi.json` and interactive docs at `/docs`.

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
| PUT    | `/api/setup/model`                | Change the model on the active provider without re-running setup     |

Five providers are registered in `llm/__init__.py`: `mock`, `anthropic_api`,
`claude_code`, `codex_cli`, and `ollama`. `claude_code` and `codex_cli` shell out
to a locally installed CLI and bill against the user's existing subscription;
`anthropic_api` is pay-per-token; `ollama` is fully local. See
[ADR-0010](adr/0010-codex-cli-provider.md) for the Codex CLI rationale.

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
| POST   | `/api/jobs/rescore`                     | Re-score the existing feed against the current profile      |
| GET    | `/api/jobs/scoring-status`              | Poll progress of an in-flight scoring pass                  |

### Feedback loop (Phase 9)

Thumbs up/down on a job card, plus the read-tracking that drives unread badges.
The stored signal feeds back into subsequent scoring passes.

| Method | Path                          | Purpose                                                             |
|--------|-------------------------------|---------------------------------------------------------------------|
| POST   | `/api/jobs/{job_id}/interact` | Record `read`, or a `+1` / `-1` feedback signal with optional reason |
| DELETE | `/api/jobs/{job_id}/interact` | Clear the feedback signal on a job (keeps read state)               |
| GET    | `/api/jobs/interactions`      | Feedback history across all jobs                                    |

### Sources (scheduled crawling)

Per-source crawl configuration backed by `crawl_sources`. Supported
`source_type` values: `wellfound`, `indeed`, `remotive`, `stepstone`.

| Method | Path                             | Purpose                                                    |
|--------|----------------------------------|------------------------------------------------------------|
| GET    | `/api/sources`                   | List configured sources with last-run state and errors     |
| POST   | `/api/sources`                   | Add a source                                               |
| PUT    | `/api/sources/{source_id}`       | Update label / enabled / company slug                      |
| DELETE | `/api/sources/{source_id}`       | Remove a source                                            |
| POST   | `/api/sources/{source_id}/run-now` | Trigger one source immediately                           |
| POST   | `/api/sources/run-now`           | Trigger every enabled source immediately                   |
| GET    | `/api/sources/config`            | Read scheduler config (`interval_hours`)                   |
| PUT    | `/api/sources/config`            | Write scheduler config                                     |

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
| POST   | `/api/applications/{id}/interview/sessions`                                | Open a coach chat session                        |
| GET    | `/api/applications/{id}/interview/sessions/{session_id}`                   | Load a session with its transcript               |
| DELETE | `/api/applications/{id}/interview/sessions/{session_id}`                   | Delete a coach session                           |
| POST   | `/api/applications/{id}/interview/sessions/{session_id}/messages`          | Send a turn; streams the coach reply (SSE)       |

### Mock interviews (Phase 8+)

A mock interview is a saved configuration per application (type, interviewer
gender, prepared question set). A **run** is one recorded sitting against it, in
text or voice mode, which can then be evaluated.

| Method | Path                                                              | Purpose                                          |
|--------|-------------------------------------------------------------------|--------------------------------------------------|
| POST   | `/api/applications/{id}/interviews`                               | Create an interview config                       |
| GET    | `/api/applications/{id}/interviews`                               | List interviews for the application              |
| PATCH  | `/api/applications/{id}/interviews/{interview_id}`                | Update type / gender / label                     |
| DELETE | `/api/applications/{id}/interviews/{interview_id}`                | Remove the interview and its runs                |
| POST   | `/api/applications/{id}/interviews/{interview_id}/questions`      | Generate and cache the question set              |
| POST   | `/api/applications/{id}/interviews/{interview_id}/runs`           | Start a run (`voice_mode` opt-in)                |
| GET    | `/api/applications/{id}/interviews/{interview_id}/runs`           | List past runs                                   |
| GET    | `/api/applications/{id}/interviews/{interview_id}/runs/{run_id}`  | Run detail incl. transcript                      |
| POST   | `…/runs/{run_id}/complete`                                        | Close the run and freeze the transcript          |
| POST   | `…/runs/{run_id}/evaluate`                                        | LLM evaluation + structured feedback for the run |

### Voice (local STT/TTS)

Speech runs entirely on-device via Piper (TTS) and faster-whisper (STT). Models
download on first use; `GET /status` reports what is missing so the UI can offer
a one-time "Set up voice" step. Audio uploads are capped at 25 MB.

| Method | Path                  | Purpose                                                        |
|--------|-----------------------|----------------------------------------------------------------|
| GET    | `/api/voice/status`   | `deps_available`, `models_ready`, `prepare_state`, `error`     |
| POST   | `/api/voice/prepare`  | Kick off model download in the background (503 if deps absent) |
| POST   | `/api/voice/tts`      | Text → audio bytes; optional interviewer `gender`              |
| POST   | `/api/voice/stt`      | Audio upload → transcribed text                                |

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
