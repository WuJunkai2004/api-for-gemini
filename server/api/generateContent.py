import json
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from google.genai.types import (
    Candidate,
    Content,
    FinishReason,
    FunctionCall,
    GenerateContentConfig,
    GenerateContentResponse,
    GenerateContentResponseUsageMetadata,
    Part,
    TrafficType,
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


def _convert_openai_response(response, model_name: str) -> GenerateContentResponse:
    choice = response.choices[0]
    parts: list[Part] = []
    if hasattr(choice.message, "reasoning_content") and choice.message.reasoning_content:
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
        if hasattr(response.usage, "completion_tokens_details") and response.usage.completion_tokens_details:
            thoughts_token_count = getattr(response.usage.completion_tokens_details, "reasoning_tokens", None)

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

    return GenerateContentResponse(
        candidates=[candidate],
        usage_metadata=usage,
        model_version=model_name,
        response_id=response.id,
        create_time=create_time,
    )


def _convert_openai_stream_chunk(chunk, model_name: str) -> GenerateContentResponse | None:
    if not chunk.choices:
        return None
    choice = chunk.choices[0]
    delta = choice.delta
    parts: list[Part] = []
    if hasattr(delta, "reasoning_content") and delta.reasoning_content:
        parts.append(Part(text=delta.reasoning_content, thought=True))
    if delta.content:
        parts.append(Part(text=delta.content))

    # Skip empty chunks with no finish reason (tool_calls are handled by accumulator)
    if not parts and not choice.finish_reason:
        return None

    candidate = Candidate(
        content=Content(role="model", parts=parts),
        finish_reason=_map_finish_reason(choice.finish_reason),
        index=choice.index,
    )

    usage = GenerateContentResponseUsageMetadata(traffic_type=TrafficType.ON_DEMAND)
    if hasattr(chunk, "usage") and chunk.usage:
        thoughts_token_count = None
        if hasattr(chunk.usage, "completion_tokens_details") and chunk.usage.completion_tokens_details:
            thoughts_token_count = getattr(chunk.usage.completion_tokens_details, "reasoning_tokens", None)
        usage = GenerateContentResponseUsageMetadata(
            prompt_token_count=chunk.usage.prompt_tokens,
            candidates_token_count=chunk.usage.completion_tokens,
            total_token_count=chunk.usage.total_tokens,
            thoughts_token_count=thoughts_token_count,
            traffic_type=TrafficType.ON_DEMAND,
        )

    create_time = None
    if hasattr(chunk, "created") and chunk.created:
        create_time = datetime.fromtimestamp(chunk.created, tz=timezone.utc)

    return GenerateContentResponse(
        candidates=[candidate],
        usage_metadata=usage,
        model_version=model_name,
        response_id=chunk.id,
        create_time=create_time,
    )


@router.post("/{model}:generateContent")
async def generate_content(
    google_request: GoogleRequest,
    model: str
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
        response = await client.aio.models.generate_content(**call_kwargs)
        return response.model_dump(by_alias=True, exclude_none=True, mode="json")

    response = await client.chat.completions.create(**kwargs)
    gemini_response = _convert_openai_response(response, target.model or model)
    return gemini_response.model_dump(by_alias=True, exclude_none=True, mode="json")


@router.post("/{model}:streamGenerateContent")
async def stream_generate_content(
    google_request: GoogleRequest,
    model: str
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
            request_start_time = datetime.now(timezone.utc)
            async for chunk in response_stream:
                if not chunk.create_time:
                    chunk.create_time = request_start_time
                if not chunk.usage_metadata:
                    chunk.usage_metadata = GenerateContentResponseUsageMetadata(traffic_type=TrafficType.ON_DEMAND)
                elif not chunk.usage_metadata.traffic_type:
                    chunk.usage_metadata.traffic_type = TrafficType.ON_DEMAND
                chunk_dict = chunk.model_dump(by_alias=True, exclude_none=True, mode="json")
                yield f"data: {json.dumps(chunk_dict)}\n\n"

        return StreamingResponse(_sse_generator(), media_type="text/event-stream")

    kwargs["stream"] = True
    response_stream = await client.chat.completions.create(**kwargs)

    async def _sse_generator():
        first_chunk = True
        accumulated_tool_calls = {} # tool_call_index -> {name, args_str}

        async for chunk in response_stream:
            # Check for tool calls in the chunk (OpenAI style)
            if chunk.choices and chunk.choices[0].delta.tool_calls:
                for tc in chunk.choices[0].delta.tool_calls:
                    idx = tc.index
                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {"name": "", "args": ""}
                    if tc.function.name:
                        accumulated_tool_calls[idx]["name"] += tc.function.name
                    if tc.function.arguments:
                        accumulated_tool_calls[idx]["args"] += tc.function.arguments

            gemini_chunk = _convert_openai_stream_chunk(chunk, target.model or model)

            # If this is the final chunk, or if it has finish_reason, we might need to flush tool calls
            is_finished = chunk.choices and chunk.choices[0].finish_reason is not None

            if gemini_chunk is None and not is_finished:
                continue

            if gemini_chunk is None:
                # Create a minimal chunk for finish_reason if needed
                gemini_chunk = GenerateContentResponse(
                    candidates=[Candidate(index=0, finish_reason=_map_finish_reason(chunk.choices[0].finish_reason))],
                    model_version=target.model or model,
                    response_id=chunk.id
                )

            # If finished, inject all accumulated tool calls into the last (or current) chunk
            if is_finished and accumulated_tool_calls:
                tool_parts = []
                for idx in sorted(accumulated_tool_calls.keys()):
                    tc_data = accumulated_tool_calls[idx]
                    try:
                        args = json.loads(tc_data["args"]) if tc_data["args"] else {}
                    except json.JSONDecodeError:
                        args = {}
                    tool_parts.append(Part(function_call=FunctionCall(name=tc_data["name"], args=args)))

                if gemini_chunk.candidates:
                    if not gemini_chunk.candidates[0].content:
                        gemini_chunk.candidates[0].content = Content(role="model", parts=[])
                    gemini_chunk.candidates[0].content.parts.extend(tool_parts)
                accumulated_tool_calls = {} # Clear after flushing

            # Ensure role and usage metadata consistency
            if gemini_chunk.candidates and gemini_chunk.candidates[0].content:
                gemini_chunk.candidates[0].content.role = "model"

            if gemini_chunk.usage_metadata is None:
                gemini_chunk.usage_metadata = GenerateContentResponseUsageMetadata(traffic_type=TrafficType.ON_DEMAND)

            chunk_dict = gemini_chunk.model_dump(by_alias=True, exclude_none=True, mode="json")
            yield f"data: {json.dumps(chunk_dict)}\n\n"

    return StreamingResponse(_sse_generator(), media_type="text/event-stream")
