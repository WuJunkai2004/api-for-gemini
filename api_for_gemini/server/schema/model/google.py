from typing import Optional

from google.genai.types import Content, GenerateContentConfig

from api_for_gemini.server.schema.model.base import ClientRequest
from api_for_gemini.server.schema.request import APIRequest


class GoogleRequest(ClientRequest):
    config: Optional[GenerateContentConfig]
    model: str
    contents: list[Content]

    @staticmethod
    def build(
        data: APIRequest, model_name: str, isStream: bool = False
    ) -> "GoogleRequest":
        config = None
        if data.generation_config or data.system_instruction or data.tools:
            config = data.generation_config or GenerateContentConfig()
            if data.system_instruction is not None:
                config.system_instruction = data.system_instruction
            if data.tools is not None:
                config.tools = data.tools

        return GoogleRequest(
            model=model_name,
            contents=data.contents,
            config=config,
        )
