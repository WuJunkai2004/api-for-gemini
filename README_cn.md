# API for Gemini

[English](README.md) | 中文

轻量级 API 代理，接收 Google Gemini API 请求并根据 `config.toml` 规则将其路由到 Gemini、OpenAI 兼容或 DeepSeek 后端。主要为 [Gemini CLI](https://github.com/google-gemini/gemini-cli) 设计，让你可以使用任意 LLM 提供商作为后端。

## 功能特性

- **多后端支持** — 将请求路由到 Gemini、OpenAI、DeepSeek 或任何 OpenAI 兼容端点（如 Ollama、vLLM）
- **模型路由** — 通过转发规则透明地将模型名映射到不同后端
- **流式与非流式** — 完整支持 SSE 流式和标准请求/响应
- **工具调用** — Gemini 与 OpenAI 格式之间的函数调用/工具使用透明转换
- **思考支持** — DeepSeek 的 `reasoning_content` 映射为 Gemini 的 `thought` 部分
- **零配置 Gemini CLI 集成** — `gema setup` 写入钩子，代理随 Gemini CLI 自动启动

## 环境要求

- Python 3.10+

## 安装

使用 [uv](https://docs.astral.sh/uv/)（推荐）：

```bash
uv tool install api-for-gemini
```

使用 pip：

```bash
pip install api-for-gemini
```

安装完成后，`gema` 命令行工具即可使用。

## 快速开始

### 1. 创建配置文件

```bash
gema config -n
```

这会在当前目录创建 `config.toml`。编辑它，填入你的 API 密钥和模型映射：

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

### 2. 启动代理服务

```bash
gema start
```

服务运行在 `http://127.0.0.1:18000`。

开发模式（热重载）：

```bash
gema start --debug
```

### 3. 与 Gemini CLI 配合使用

1. **自动启动配置 (推荐)**：执行以下命令，将 `gema-context` 钩子写入全局 Gemini CLI 设置。这可以确保无论你在哪个目录下启动 Gemini CLI，代理服务都会自动在后台启动。
```bash
gema setup -g
```

2. **配置环境变量**：设置 `GOOGLE_GEMINI_BASE_URL` 环境变量，将其指向代理服务。为了方便使用，建议将其设为永久环境变量：
```bash
# Windows (PowerShell) - 当前会话
$env:GOOGLE_GEMINI_BASE_URL = "http://127.0.0.1:18000"
# Windows (PowerShell) - 永久设置 (用户级)
[Environment]::SetEnvironmentVariable("GOOGLE_GEMINI_BASE_URL", "http://127.0.0.1:18000", "User")

# Linux / macOS - 当前会话
export GOOGLE_GEMINI_BASE_URL="http://127.0.0.1:18000"
# Linux / macOS - 永久设置 (添加到 ~/.bashrc 或 ~/.zshrc)
echo 'export GOOGLE_GEMINI_BASE_URL="http://127.0.0.1:18000"' >> ~/.bashrc
```

3. **Gemini CLI 认证**：在 Gemini CLI 会话中，运行 `/auth` 命令：
   - 选择 **"2. Use Gemini API Key"**。
   - 输入任意字符串作为 API 密钥（实际的密钥由你的 `config.toml` 管理）。

## CLI 命令参考

```
gema setup [-g|--global] [-l|--local] [-c CONFIG_PATH]   # 初始化配置 + Gemini CLI 钩子
gema config -n [PATH]                                     # 创建新的配置文件
gema start [-c CONFIG_PATH] [-d|--debug]                  # 启动代理服务器
gema context                                               # 输出 JSON 上下文（Gemini CLI 钩子使用）
```

| 命令 | 说明 |
|------|------|
| `gema setup -l` | 创建 `config.toml` + 将钩子写入本地 `.gemini/settings.json` |
| `gema setup -g` | 创建 `config.toml` + 将钩子写入全局 `~/.gemini/settings.json` |
| `gema config -n ./my-config.toml` | 在指定路径创建配置文件 |
| `gema start -c ./my-config.toml` | 使用自定义配置文件启动服务 |
| `gema start --debug` | 以热重载模式启动（监听 `api_for_gemini/server/` 目录） |

## 配置文件参考

### 提供商（`[provider.ID]`）

定义可复用的后端连接：

| 字段 | 说明 |
|------|------|
| `template` | 后端类型：`"gemini"`、`"openai"` 或 `"deepseek"` |
| `api_url` | API 端点的 Base URL |
| `api_key` | 用于认证的 API 密钥 |

### 模型（`[model.NAME]`）

定义可用模型，可选择从提供商继承配置：

| 字段 | 说明 |
|------|------|
| `provider` | 引用 `[provider.ID]`（继承 `template`、`api_url`、`api_key`） |
| `model` | 发送到后端的实际模型名 |
| `template` | 后端类型（无 `provider` 时必填） |
| `api_url` | API 端点（无 `provider` 时必填） |
| `api_key` | API 密钥（无 `provider` 时必填） |

### 转发规则（`[[transfer]]`）

将一个模型名路由到另一个模型。`make` 字段支持使用 `*` 通配符进行灵活匹配（支持前缀、后缀或中间匹配）：

```toml
[[transfer]]
make = "gemini-pro"      # 请求中的模型名
to = "gemini-2-5-flash"  # 实际路由到的模型

[[transfer]]
make = "gpt-4*"          # 后缀匹配：匹配 gpt-4, gpt-4-turbo, gpt-4o 等
to = "ds-chat"

[[transfer]]
make = "h*d"             # 中间匹配：匹配 "helloworld", "head", "hd" 等
to = "some-model"
```

## 架构

```
Gemini CLI 请求
       |
       v
  Gema 代理 (FastAPI, :18000)
       |
       +-- ConfigManager.resolve_model() --> ModelSchema
       |
       +-- ClientRequest.build() --> GoogleRequest / OpenaiRequest / DeepseekRequest
       |
       +-- 后端 API 调用 (Gemini / OpenAI / DeepSeek)
       |
       +-- 响应转换回 Gemini 格式
       |
       v
  Gemini CLI 接收响应
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1beta/models/{model}:generateContent` | 非流式生成 |
| POST | `/v1beta/models/{model}:streamGenerateContent` | SSE 流式生成 |
| GET | `/status` | 健康检查 |

所有端点均接收和返回 Gemini API 格式，无论实际使用的是哪种后端。

## 许可证

MIT
