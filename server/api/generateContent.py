import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from google.genai.types import (
    Candidate,
    Content,
    FinishReason,
    FunctionCall,
    GenerateContentResponseUsageMetadata,
    Part,
    TrafficType,
)

from server.schema.model import (
    BaseRequest,
    DeepseekRequest,
    GoogleRequest,
    OpenaiRequest,
)
from server.schema.request import APIRequest
from server.schema.response import APIResponse
from server.utils.aiclient import getChatFuncion
from server.utils.config import ConfigManager

router = APIRouter()
config = ConfigManager()


def _map_finish_reason(reason: str | None) -> FinishReason | None:
    if reason is None:
        return None
    mapping = {
        "stop": FinishReason.STOP,
        "length": FinishReason.MAX_TOKENS,
        "content_filter": FinishReason.SAFETY,
        "tool_calls": FinishReason.STOP,
    }
    return mapping.get(reason)


def _convert_tool_calls_to_parts(tool_calls) -> list[Part]:
    parts = []
    for tc in tool_calls:
        args = {}
        if tc.function.arguments:
            try:
                args = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, TypeError):
                args = {}
        parts.append(Part(function_call=FunctionCall(name=tc.function.name, args=args)))
    return parts


def _convert_openai_response(response, model_name: str) -> APIResponse:
    choice = response.choices[0]
    parts: list[Part] = []
    if (
        hasattr(choice.message, "reasoning_content")
        and choice.message.reasoning_content
    ):
        parts.append(Part(text=choice.message.reasoning_content, thought=True))
    if choice.message.content:
        parts.append(Part(text=choice.message.content))
    if choice.message.tool_calls:
        parts.extend(_convert_tool_calls_to_parts(choice.message.tool_calls))
    candidate = Candidate(
        content=Content(role="model", parts=parts),
        finish_reason=_map_finish_reason(choice.finish_reason),
        index=choice.index,
    )
    usage = GenerateContentResponseUsageMetadata(traffic_type=TrafficType.ON_DEMAND)
    if response.usage:
        thoughts_token_count = None
        if (
            hasattr(response.usage, "completion_tokens_details")
            and response.usage.completion_tokens_details
        ):
            thoughts_token_count = getattr(
                response.usage.completion_tokens_details, "reasoning_tokens", None
            )

        usage = GenerateContentResponseUsageMetadata(
            prompt_token_count=response.usage.prompt_tokens,
            candidates_token_count=response.usage.completion_tokens,
            total_token_count=response.usage.total_tokens,
            thoughts_token_count=thoughts_token_count,
            traffic_type=TrafficType.ON_DEMAND,
        )

    create_time = None
    if hasattr(response, "created") and response.created:
        create_time = datetime.fromtimestamp(response.created, tz=timezone.utc)

    return APIResponse(
        candidates=[candidate],
        usage_metadata=usage,
        model_version=model_name,
        response_id=response.id,
        create_time=create_time,
    )


@router.post("/{model}:generateContent")
async def generate_content(req: APIRequest, model: str):
    target = config.resolve_model(model)
    if not target:
        raise HTTPException(status_code=404, detail="Model not found")

    new_model = target.model
    data: Optional[BaseRequest] = None
    match target.template:
        case "deepseek":
            data = DeepseekRequest.build(req, new_model, False)
        case "openai":
            data = OpenaiRequest.build(req, new_model, False)
        case "gemini":
            data = GoogleRequest.build(req, new_model, False)

    if not data:
        raise HTTPException(
            status_code=400, detail="Invalid request for the specified model"
        )

    func = getChatFuncion(target, False)
    print(data.args())
    result = await func(**data.args())

    match target.template:
        case "deepseek":
            gemini_response = _convert_openai_response(result, model)
            return gemini_response.model_dump(
                by_alias=True, exclude_none=True, mode="json"
            )
        case "openai":
            gemini_response = _convert_openai_response(result, model)
            return gemini_response.model_dump(
                by_alias=True, exclude_none=True, mode="json"
            )
        case "gemini":
            return result.model_dump(by_alias=True, exclude_none=True, mode="json")
