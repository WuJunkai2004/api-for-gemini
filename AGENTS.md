# Grovider

OpenAI-compatible API proxy for Gemini. Receives Google Gemini API requests and can transfer/route them to other backends (OpenAI-compatible or Gemini).

## Setup

- **Python 3.12+**, managed with `uv`.
- Install: `uv sync`
- Run dev server: `uv run python main.py` (starts uvicorn on port 18000 with hot reload)

## Architecture

```
main.py                 # Entry point, runs uvicorn
server/
  main.py               # FastAPI app, lifespan, CORS, router registration
  api/
    generateContent.py   # POST /v1beta/models/{model}:generateContent and :streamGenerateContent
    probe.py             # Catch-all probe/debug endpoint
  schema/
    request/google.py    # Pydantic request model wrapping google-genai types
    response/google.py   # Re-exports GenerateContentResponse
  utils/
    config.py            # Singleton ConfigManager, reads config.toml
    logger.py            # Request logging
config.toml              # Runtime config (gitignored) — defines providers, models, transfer rules
referrence/              # Reference data, not part of the app
```

## Key Behaviors

- `server/main.py` calls `os.environ.clear()` at import time (line 7) — environment variables are wiped on startup.
- `ConfigManager` is a singleton; it loads `config.toml` from the project root. Call `ConfigManager.reset()` in tests to allow re-initialization.
- Models can inherit `schema`/`api_url`/`api_key` from a named provider, or override them inline.
- Transfer rules: when a request targets model X, it can be rerouted to model Y via `[[transfer]]` entries.
- The `:generateContent` and `:streamGenerateContent` endpoints are currently non-functional (raise 404).

## Configuration

`config.toml` is gitignored. It contains API keys and endpoint URLs. A local copy must exist to run the server.

## Dependencies

- `fastapi` + `uvicorn` — HTTP server
- `google-genai` — Gemini client and types (used for both request/response schemas and API calls)
- `openai` — OpenAI-compatible backend client (for proxying to non-Gemini providers)
