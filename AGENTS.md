# Grovider

Gemini API proxy that receives Google Gemini API requests and routes them to Gemini or OpenAI-compatible backends based on `config.toml` rules.

## Setup

- **Python 3.10+**, using standard venv + pip.
- Install: `pip install -e .`
- Run dev server: `python main.py` (uvicorn on port 18000 with hot reload)

## Architecture

- `main.py` — entry point, runs uvicorn.
- `server/main.py` — FastAPI app. **Calls `os.environ.clear()` at module level (line 7)** — all env vars are wiped on import.
- `server/api/generateContent.py` — `POST /v1beta/models/{model}:generateContent` and `:streamGenerateContent`. Converts between Gemini and OpenAI request/response formats depending on the target backend's `schema`.
- `server/api/probe.py` — catch-all route for debugging; logs full request details.
- `server/schema/request.py` — Pydantic `GoogleRequest` model wrapping `google-genai` types.
- `server/schema/model/` — request transfer logic: `to_openai.py` (Gemini→OpenAI conversion), `to_gemini.py` (pass-through), `transfer.py` dispatches by target schema.
- `server/utils/config.py` — `ConfigManager` singleton. Loads `config.toml` at import time. Call `ConfigManager.reset()` in tests to allow re-initialization.
- `config.toml` — **gitignored** runtime config (API keys, provider URLs, model definitions, transfer rules). Must exist locally to run.

## Key Behaviors

- `server/main.py:7` wipes all environment variables at import time — never rely on env vars at runtime.
- `ConfigManager` is a singleton initialized at module import from `config.toml` at the project root.
- Models can inherit `schema`/`api_url`/`api_key` from a named provider, or override inline.
- Transfer rules: `[[transfer]]` entries reroute requests from one model name to another.
- Two backend schemas: `"gemini"` uses `google-genai` client; anything else uses `openai.AsyncOpenAI`.

## Dependencies

- `fastapi` + `uvicorn` — HTTP server
- `google-genai` — Gemini client and types (request/response schemas and API calls)
- `openai` — OpenAI-compatible backend client
- `pydantic` — pulled in by FastAPI, used for request model
- `tomli` — TOML parsing for Python < 3.12 (stdlib `tomllib` for 3.12+)

## Build

- Build system: `hatchling` (configured in `pyproject.toml`)
- Package: `server` directory is the installable package
