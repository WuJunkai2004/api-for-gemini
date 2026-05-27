from google.genai import Client as GeminiClient
from openai import AsyncOpenAI as OpenAIClient

from api_for_gemini.server.utils.config import AIClient, ModelSchema


def getClient(model: ModelSchema) -> AIClient:
    if model.template == "gemini":
        return GeminiClient(
            api_key=model.api_key,
            http_options={
                "base_url": model.api_url,
            },
        )
    elif model.template == "openai" or model.template == "deepseek":
        return OpenAIClient(
            api_key=model.api_key,
            base_url=model.api_url,
        )
    else:
        raise ValueError(f"Unsupported model template: {model.template}")


def getChatFuncion(model: ModelSchema, isStream=False):
    client = getClient(model)

    def openaiFuncs(client: OpenAIClient):
        if isStream:
            return client.chat.completions.create
        else:
            return client.chat.completions.create

    def geminiFuncs(client: GeminiClient):
        if isStream:
            return client.aio.models.generate_content
        else:
            return client.aio.models.generate_content

    if isinstance(client, OpenAIClient):
        return openaiFuncs(client)
    elif isinstance(client, GeminiClient):
        return geminiFuncs(client)
    else:
        raise ValueError("Unsupported client type")
