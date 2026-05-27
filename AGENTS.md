# API for Gemini

Gemini API proxy that receives Google Gemini API requests and routes them to Gemini or OpenAI-compatible backends based on `config.toml` rules.

## Setup

- **Python 3.10+** (uses `match/case`). Standard venv + pip.
- Install: `pip install -e .`
- Dev server: `python main.py` — uvicorn on port 18000 with hot reload. Do not restart it manually.

## Architecture

```
Request → APIRequest (Gemini types)
       → ConfigManager.resolve_model() → ModelSchema (with template)
       → ClientRequest.build()         → per-template request (GoogleRequest / OpenaiRequest / DeepseekRequest)
       → aiclient.getChatFuncion()     → backend call
       → response conversion back to Gemini format
```

- `main.py` — entry point, runs uvicorn.
- `server/main.py` — FastAPI app, mounts routers under `/v1beta/models`.
- `server/api/generateContent.py` — non-streaming `POST /{model}:generateContent`.
- `server/api/generateStreaming.py` — streaming `POST /{model}:streamGenerateContent`. Both files dispatch by `target.template` via `match/case`.
- `server/api/probe.py` — catch-all debug route.
- `server/api/OldgenerateContent.py` — **legacy dead code**, do not reference.

### Schema-Driven Request Layer (`server/schema/model/`)

Each backend template has a `ClientRequest` subclass with a static `build()` factory:

| File | Class | Backend | Notes |
|---|---|---|---|
| `base.py` | `ClientRequest` | abstract base | `build(data, model_name, isStream)`, `args()` returns dict |
| `google.py` | `GoogleRequest` | `google-genai` | Pass-through of `contents`/`config`/`model` |
| `openai.py` | `OpenaiRequest` | `openai.AsyncOpenAI` | Full Gemini→OpenAI conversion (messages, tools, generation_config) |
| `deepseek.py` | `DeepseekRequest` | `openai.AsyncOpenAI` | Like OpenAI but preserves `reasoning_content` (thinking) in assistant messages |

- `build()` receives `APIRequest` (Gemini-native) and produces the backend-specific request.
- `args()` serializes to a dict for `**kwargs` passing to the backend client.
- `clean_json_schema()` is duplicated in both `openai.py` and `deepseek.py` — changes to one should be mirrored.

### Response Layer (`server/schema/response.py`)

Three `GenerateContentResponse` subclasses: `APIResponse`, `APIStreamChunk` (no usage), `APIStreamFinal` (forces `usage_metadata`). All responses are converted back to Gemini wire format.

### Config (`server/utils/config.py`)

- `ConfigManager` — singleton, loads `config.toml` at import time from project root.
- Pydantic models: `ProviderSchema`, `ModelSchema`, `TransferSchema`, `Config`.
- **`template`** (not `schema`) selects the backend: `"gemini"` | `"openai"` | `"deepseek"`.
- Models inherit `template`/`api_url`/`api_key` from a named `[provider.*]`, or define them inline.
- `[[transfer]]` entries reroute one model name to another via `resolve_model()`.
- `config.toml` is **gitignored**; copy from `config.example.toml`.

### Client Factory (`server/utils/aiclient.py`)

- `getClient()` → `GeminiClient` for `"gemini"`, `AsyncOpenAI` for `"openai"`/`"deepseek"`.
- `getChatFuncion()` → returns the async callable (`client.aio.models.generate_content` or `client.chat.completions.create`).

## Key Behaviors

- No formal test runner. `tests/` contains standalone scripts (not pytest), run them individually with `python`.
- No `os.environ.clear()` — the old AGENTS.md was wrong about this; the current code does not wipe env vars.
- `ConfigManager` is a singleton. Call `ConfigManager.reset()` (or patch `_instance`) in tests to allow re-initialization.
- The codebase uses `match/case` on `target.template` extensively — adding a new template requires updating: `config.py` (`Literal` type), `schema/model/` (new class), `aiclient.py`, and both API route files.
- `pydantic` is not a direct dependency — it comes from `fastapi` and `google-genai`.

## Dependencies

- `fastapi` + `uvicorn` — HTTP server
- `google-genai` — Gemini client, request/response types, and `pydantic` transitive dep
- `openai` — OpenAI-compatible backend client
- `tomli` — TOML parsing for Python < 3.12 (stdlib `tomllib` for 3.12+)
- Build: `hatchling`, package is `server/` dir
