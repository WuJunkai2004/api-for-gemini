import json

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from google.genai.types import (
    Candidate,
    Content,
    FinishReason,
    GenerateContentConfig,
    GenerateContentResponse,
    GenerateContentResponseUsageMetadata,
    Part,
)

from server.schema.model.transfer import transfer
from server.schema.request import GoogleRequest
from server.utils.config import config as app_config

router = APIRouter()


def _build_config(req: GoogleRequest) -> GenerateContentConfig | None:
    if (
        req.generation_config is None
        and req.system_instruction is None
        and req.tools is None
    ):
        return None
    config = req.generation_config or GenerateContentConfig()
    if req.system_instruction is not None:
        config.system_instruction = req.system_instruction
    if req.tools is not None:
        config.tools = req.tools
    return config


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


def _convert_openai_response(response) -> GenerateContentResponse:
    choice = response.choices[0]
    parts = [Part(text=choice.message.content)] if choice.message.content else []
    candidate = Candidate(
        content=Content(role="model", parts=parts),
        finish_reason=_map_finish_reason(choice.finish_reason),
    )
    usage = None
    if response.usage:
        usage = GenerateContentResponseUsageMetadata(
            prompt_token_count=response.usage.prompt_tokens,
            candidates_token_count=response.usage.completion_tokens,
            total_token_count=response.usage.total_tokens,
        )
    return GenerateContentResponse(
        candidates=[candidate],
        usage_metadata=usage,
    )


def _convert_openai_stream_chunk(chunk) -> GenerateContentResponse:
    if not chunk.choices:
        return GenerateContentResponse(candidates=[])
    choice = chunk.choices[0]
    delta = choice.delta
    text = delta.content or ""
    candidate = Candidate(
        content=Content(role="model", parts=[Part(text=text)] if text else []),
        finish_reason=_map_finish_reason(choice.finish_reason),
    )
    return GenerateContentResponse(candidates=[candidate])


@router.post("/{model}:generateContent")
async def generate_content(
    google_request: GoogleRequest,
    model: str,
    x_goog_api_key: str = Header(default=""),
):
    target = app_config.resolve_model(model)
    if not target:
        raise HTTPException(status_code=404, detail=f"Model {model} not found")

    kwargs = transfer(google_request, model, False)
    client = target.get_client()

    if target.schema == "gemini":
        config = _build_config(kwargs)
        call_kwargs: dict = {
            "model": target.model or model,
            "contents": kwargs.contents,
        }
        if config is not None:
            call_kwargs["config"] = config
        return await client.aio.models.generate_content(**call_kwargs)

    response = await client.chat.completions.create(**kwargs)
    return _convert_openai_response(response)


@router.post("/{model}:streamGenerateContent")
async def stream_generate_content(
    google_request: GoogleRequest,
    model: str,
    x_goog_api_key: str = Header(default=""),
):
    target = app_config.resolve_model(model)
    if not target:
        raise HTTPException(status_code=404, detail=f"Model {model} not found")

    kwargs = transfer(google_request, model, True)
    client = target.get_client()

    if target.schema == "gemini":
        config = _build_config(kwargs)
        call_kwargs: dict = {
            "model": target.model or model,
            "contents": kwargs.contents,
        }
        if config is not None:
            call_kwargs["config"] = config
        response_stream = await client.aio.models.generate_content_stream(**call_kwargs)

        async def _sse_generator():
            async for chunk in response_stream:
                chunk_dict = chunk.model_dump(exclude_none=True, mode="json")
                yield f"data: {json.dumps(chunk_dict)}\n\n"

        return StreamingResponse(_sse_generator(), media_type="text/event-stream")

    kwargs["stream"] = True
    response_stream = await client.chat.completions.create(**kwargs)

    async def _sse_generator():
        async for chunk in response_stream:
            gemini_chunk = _convert_openai_stream_chunk(chunk)
            chunk_dict = gemini_chunk.model_dump(exclude_none=True, mode="json")
            yield f"data: {json.dumps(chunk_dict)}\n\n"

    return StreamingResponse(_sse_generator(), media_type="text/event-stream")
