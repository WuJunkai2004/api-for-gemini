from google.genai import Client as GeminiClient
from openai import AsyncOpenAI as OpenAIClient

from api_for_gemini.server.utils.config import AIClient, ModelSchema

# Simple client cache: model_id -> client
_client_cache: dict[str, AIClient] = {}


def getClient(model: ModelSchema) -> AIClient:
    # Use a unique key based on API key and URL to avoid conflicts
    cache_key = f"{model.template}:{model.api_key}:{model.api_url}"
    if cache_key in _client_cache:
        return _client_cache[cache_key]

    if model.template == "gemini":
        client = GeminiClient(
            api_key=model.api_key,
            http_options={
                "base_url": model.api_url,
            },
        )
    elif model.template == "openai" or model.template == "deepseek":
        client = OpenAIClient(
            api_key=model.api_key,
            base_url=model.api_url,
        )
    else:
        raise ValueError(f"Unsupported model template: {model.template}")

    _client_cache[cache_key] = client
    return client


def getChatFuncion(model: ModelSchema, isStream=False):
    client = getClient(model)

    def openaiFuncs(client: OpenAIClient):
        if isStream:
            return client.chat.completions.create
        else:
            return client.chat.completions.create

    def geminiFuncs(client: GeminiClient):
        if isStream:
            return client.aio.models.generate_content_stream
        else:
            return client.aio.models.generate_content

    if isinstance(client, OpenAIClient):
        return openaiFuncs(client)
    elif isinstance(client, GeminiClient):
        return geminiFuncs(client)
    else:
        raise ValueError("Unsupported client type")
