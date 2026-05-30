# API for Gemini

A lightweight API proxy that receives Google Gemini API requests and routes them to Gemini, OpenAI-compatible, or DeepSeek backends based on `config.toml` rules. Designed primarily for use with [Gemini CLI](https://github.com/google-gemini/gemini-cli), enabling you to use any LLM provider as the backend.

## Features

- **Multi-backend support** — Route requests to Gemini, OpenAI, DeepSeek, or any OpenAI-compatible endpoint (e.g. Ollama, vLLM)
- **Model routing** — Transparently map model names to different backends via transfer rules
- **Streaming & non-streaming** — Full support for both SSE streaming and standard request/response
- **Tool calls** — Transparent function calling / tool use conversion between Gemini and OpenAI formats
- **Thinking support** — DeepSeek `reasoning_content` is mapped to Gemini's `thought` parts
- **Zero-config Gemini CLI integration** — `gema setup` writes hooks so the proxy auto-starts with Gemini CLI

## Requirements

- Python 3.10+

## Installation

Using [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv pip install -e .
```

Using pip:

```bash
pip install -e .
```

After installation, the `gema` CLI command is available.

## Quick Start

### 1. Create Configuration

```bash
gema config -n
```

This creates `config.toml` in the current directory. Edit it with your API keys and model mappings:

```toml
[provider.google]
template = "gemini"
api_url = "https://generativelanguage.googleapis.com"
api_key = "YOUR_GEMINI_API_KEY"

[provider.openai_official]
template = "openai"
api_url = "https://api.openai.com/v1"
api_key = "YOUR_OPENAI_API_KEY"

[provider.deepseek_official]
template = "deepseek"
api_url = "https://api.deepseek.com/v1"
api_key = "YOUR_DEEPSEEK_API_KEY"

[model.gemini-2-5-flash]
provider = "google"
model = "gemini-2.5-flash"

[model.gpt-4o]
provider = "openai_official"
model = "gpt-4o"

[model.ds-chat]
provider = "deepseek_official"
model = "deepseek-chat"

[model.local-llama]
template = "openai"
api_url = "http://localhost:11434/v1"
model = "llama3"

[[transfer]]
make = "gemini-pro"
to = "gemini-2-5-flash"

[[transfer]]
make = "gpt-4"
to = "ds-chat"
```

### 2. Start the Proxy

```bash
gema start
```

The server runs on `http://127.0.0.1:18000`.

For development with hot reload:

```bash
gema start --debug
```

### 3. Use with Gemini CLI

One-command setup for Gemini CLI integration:

```bash
gema setup -l
```

This writes a `gema-context` hook to `.gemini/settings.json`. When Gemini CLI starts a session, the proxy auto-starts in the background.

## CLI Reference

```
gema setup [-g|--global] [-l|--local] [-c CONFIG_PATH]   # Initialize config + Gemini CLI hooks
gema config -n [PATH]                                     # Create a new config file
gema start [-c CONFIG_PATH] [-d|--debug]                  # Start the proxy server
gema context                                               # Output JSON context (used by Gemini CLI hooks)
```

| Command | Description |
|---------|-------------|
| `gema setup -l` | Create `config.toml` + write hook to local `.gemini/settings.json` |
| `gema setup -g` | Create `config.toml` + write hook to global `~/.gemini/settings.json` |
| `gema config -n ./my-config.toml` | Create config at a specific path |
| `gema start -c ./my-config.toml` | Start server with a custom config file |
| `gema start --debug` | Start server with hot reload (watches `api_for_gemini/server/`) |

## Configuration Reference

### Providers (`[provider.ID]`)

Define reusable backend connections:

| Field | Description |
|-------|-------------|
| `template` | Backend type: `"gemini"`, `"openai"`, or `"deepseek"` |
| `api_url` | Base URL of the API endpoint |
| `api_key` | API key for authentication |

### Models (`[model.NAME]`)

Define available models, optionally inheriting from a provider:

| Field | Description |
|-------|-------------|
| `provider` | Reference to a `[provider.ID]` (inherits `template`, `api_url`, `api_key`) |
| `model` | Actual model name sent to the backend |
| `template` | Backend type (required if no `provider`) |
| `api_url` | API endpoint (required if no `provider`) |
| `api_key` | API key (required if no `provider`) |

### Transfers (`[[transfer]]`)

Route one model name to another. The `make` field supports the `*` wildcard for flexible matching (prefix, suffix, or middle):

```toml
[[transfer]]
make = "gemini-pro"      # Incoming request model name
to = "gemini-2-5-flash"  # Actual model to route to

[[transfer]]
make = "gpt-4*"          # Suffix matching: gpt-4, gpt-4-turbo, gpt-4o, etc.
to = "ds-chat"

[[transfer]]
make = "h*d"             # Middle matching: Matches "helloworld", "head", "hd", etc.
to = "some-model"
```

## Architecture

```
Gemini CLI Request
       |
       v
  Gema Proxy (FastAPI, :18000)
       |
       +-- ConfigManager.resolve_model() --> ModelSchema
       |
       +-- ClientRequest.build() --> GoogleRequest / OpenaiRequest / DeepseekRequest
       |
       +-- Backend API Call (Gemini / OpenAI / DeepSeek)
       |
       +-- Response conversion back to Gemini format
       |
       v
  Gemini CLI receives response
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1beta/models/{model}:generateContent` | Non-streaming generation |
| POST | `/v1beta/models/{model}:streamGenerateContent` | SSE streaming generation |
| GET | `/status` | Health check |

All endpoints accept and return Gemini API wire format, regardless of the backend being used.

## License

MIT
