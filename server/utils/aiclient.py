from google.genai import Client as GeminiClient
from openai import AsyncOpenAI as OpenAIClient

from server.utils.config import AIClient, ModelSchema


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
