# API for Gemini

Gemini API proxy that receives Google Gemini API requests and routes them to Gemini or OpenAI-compatible backends based on `config.toml` rules.

## Setup

- **Python 3.10+** (uses `match/case`). Standard venv + pip.
- Install: `pip install -e .`
- CLI entry point: `gema` (defined in `pyproject.toml` `[project.scripts]`).
- Version is read from `VERSION.txt` via hatch dynamic versioning.
- Publishing: CI triggers on `VERSION.txt` changes via GitHub Actions (`uv build` → `uv publish` to PyPI with OIDC).

## CLI Commands (`gema`)

```
gema setup [-g|--global] [-l|--local] [-c CONFIG_PATH]    # Initialize config.toml + Gemini hooks + env var
gema config -n [PATH]                                     # Create new config file at path (default: ./config.toml)
gema start [-c CONFIG_PATH] [-d|--debug]                  # Start proxy server
gema context                                               # Output JSON context for Gemini CLI hooks (used internally)
```

- `gema start --debug` — uvicorn on `127.0.0.1:18000` with hot reload scoped to `api_for_gemini/server/`.
- `gema start -c path/to/config.toml` — specifies the configuration file to use.
- `gema setup -g` — copies `config.toml` to `~/.gemini/`, writes a `gema-context` SessionStart hook into `~/.gemini/settings.json`, and sets `GOOGLE_GEMINI_BASE_URL=http://127.0.0.1:18000` in shell rc files (or via `setx` on Windows). `-l` writes to `.gemini/` in CWD instead.
- `gema context` — checks if server is running on `127.0.0.1:18000`, auto-starts it in background if not, then prints JSON to stdout and exits. Used as a Gemini CLI hook, not meant for interactive use.

## Architecture

```
Request → APIRequest (Gemini types)
       → ConfigManager.resolve_model() → ModelSchema (with template)
       → ClientRequest.build()         → per-template request (GoogleRequest / OpenaiRequest / DeepseekRequest)
       → aiclient.getChatFuncion()     → backend call
       → response conversion back to Gemini format
```

### Key Files

```
api_for_gemini/
├── config.example.toml          # Template copied by `gema setup` / `gema config -n`
├── app/main.py                  # CLI entry point, dispatches to command handlers
├── app/commands/                # Per-command handlers (setup, config, start, context)
├── server/main.py               # FastAPI app, mounts routers under /v1beta/models
├── server/api/
│   ├── generateContent.py       # POST /{model}:generateContent (non-streaming)
│   ├── generateStreaming.py     # POST /{model}:streamGenerateContent (streaming SSE)
│   ├── status.py                # GET /status — health check
│   └── probe.py                 # Catch-all debug route
├── server/schema/
│   ├── request.py               # APIRequest model (Gemini-native input)
│   ├── response.py              # APIResponse / APIStreamChunk / APIStreamFinal
│   └── model/                   # Per-backend request builders (ClientRequest subclasses)
│       ├── base.py              # Abstract base: build(), args()
│       ├── google.py            # GoogleRequest — pass-through to google-genai
│       ├── openai.py            # OpenaiRequest — Gemini→OpenAI conversion
│       └── deepseek.py          # DeepseekRequest — like OpenAI, preserves reasoning_content + extra_body
├── server/utils/config.py      # ConfigManager singleton, loads config.toml
├── server/utils/aiclient.py     # Client factory with caching (GeminiClient / AsyncOpenAI)
├── utils/logger.py             # LogFactory singleton `log` — used by app commands and config.py
├── utils/path.py               # ROOT, PACKAGE_ROOT, CONFIG_EXAMPLE, CONFIG_DEFAULT, GEMINI_CONFIG_DIR
└── utils/stars.py               # StarMatch — wildcard pattern matching for transfer rules
```

### Two Logger Modules

- `api_for_gemini/utils/logger.py` — `LogFactory` singleton `log`, used by app commands and `config.py`. Import: `from api_for_gemini.utils.logger import log`.
- `api_for_gemini/server/utils/logger.py` — `print_request()` async helper for the probe route. Not a general-purpose logger.

### Schema-Driven Request Layer (`server/schema/model/`)

- `build()` is a static method receiving `APIRequest` (Gemini-native) and produces the backend-specific request.
- `args()` serializes to a dict for `**kwargs` passing to the backend client.
- `clean_json_schema()` is duplicated in both `openai.py` and `deepseek.py` — changes to one should be mirrored.

### Response Layer (`server/schema/response.py`)

- `APIResponse` — non-streaming.
- `APIStreamChunk` — streaming, no usage metadata.
- `APIStreamFinal` — streaming final chunk, forces `usage_metadata`.
- All three inherit directly from `google.genai.types.GenerateContentResponse`.

### Config (`server/utils/config.py`)

- `ConfigManager` — singleton, loads `config.toml` at import time.
- Config search order: (1) explicit `config_path` argument, (2) `config.toml` in CWD, (3) `CONFIG_DEFAULT` (repo root).
- Pydantic models: `ProviderSchema`, `ModelSchema`, `TransferSchema`, `Config`.
- **`template`** (not `schema`) selects the backend: `"gemini"` | `"openai"` | `"deepseek"`.
- Models inherit `template`/`api_url`/`api_key` from a named `[provider.*]`, or define them inline.
- `[[transfer]]` entries reroute one model name to another via `resolve_model()`. The `make` field supports the `*` wildcard via `StarMatch` (from `utils/stars.py`). Rules are processed in order, and the first match wins.
- `config.toml` is **gitignored**; copy from `api_for_gemini/config.example.toml`.

### Client Factory (`server/utils/aiclient.py`)

- `getClient(model)` → `GeminiClient` for `"gemini"`, `AsyncOpenAI` for `"openai"`/`"deepseek"`. Results are cached by `template:api_key:api_url`.
- `getChatFuncion(model, isStream)` → returns the async callable (`client.aio.models.generate_content[_stream]` or `client.chat.completions.create`).

## Key Behaviors

- No formal test runner. `tests/` contains standalone scripts (not pytest), run them individually with `python`.
- `example/standard.jsonl` contains a reference SSE stream output — use it to verify streaming format compliance.
- Both `ConfigManager` and `Settings` are singletons. In tests, reset `ConfigManager._instance` / `Settings._instance` to allow re-initialization.
- The codebase uses `match/case` on `target.template` extensively — adding a new template requires updating: `config.py` (`Literal` type), `schema/model/` (new class), `aiclient.py`, and both API route files.
- `pydantic` is not a direct dependency — it comes from `fastapi` and `google-genai`.
- `uvloop` and `httptools` are runtime dependencies on non-Windows platforms (see `pyproject.toml` platform markers).
