from typing import Optional

from google.genai.types import (
    Content,
    GenerateContentConfig,
    Part,
    ThinkingConfig,
)
from pydantic import BaseModel


class GoogleRequest(BaseModel):
    model_config = GenerateContentConfig.model_config

    contents: list[Content]
    system_instruction: Optional[Content] = None
    generation_config: Optional[GenerateContentConfig] = None
