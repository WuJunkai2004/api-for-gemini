from google.genai.types import GenerateContentResponse


class APIResponse(GenerateContentResponse):
    """非流式的返回格式。"""

    pass


class APIStreamChunk(GenerateContentResponse):
    """流式返回时，不是末尾的格式。"""

    pass


class APIStreamFinal(GenerateContentResponse):
    """流式返回时，末尾最后一条的格式。
    重点在于强制包含 usage_metadata。
    """

    pass
