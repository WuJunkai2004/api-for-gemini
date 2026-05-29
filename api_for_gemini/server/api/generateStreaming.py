import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from google.genai.types import (
    Candidate,
    Content,
    FinishReason,
    FunctionCall,
    GenerateContentResponseUsageMetadata,
    Part,
    TrafficType,
)

from api_for_gemini.server.schema.model import (
    BaseRequest,
    DeepseekRequest,
    GoogleRequest,
    OpenaiRequest,
)
from api_for_gemini.server.schema.request import APIRequest
from api_for_gemini.server.schema.response import APIStreamChunk, APIStreamFinal
from api_for_gemini.server.utils.aiclient import getChatFuncion
from api_for_gemini.server.utils.config import ConfigManager
from api_for_gemini.utils.logger import log

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


def _convert_openai_stream_chunk(
    chunk, model_name: str
) -> APIStreamChunk | APIStreamFinal | None:
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

    create_time = None
    if hasattr(chunk, "created") and chunk.created:
        create_time = datetime.fromtimestamp(chunk.created, tz=timezone.utc)

    if hasattr(chunk, "usage") and chunk.usage:
        thoughts_token_count = None
        if (
            hasattr(chunk.usage, "completion_tokens_details")
            and chunk.usage.completion_tokens_details
        ):
            thoughts_token_count = getattr(
                chunk.usage.completion_tokens_details, "reasoning_tokens", None
            )
        usage = GenerateContentResponseUsageMetadata(
            prompt_token_count=chunk.usage.prompt_tokens,
            candidates_token_count=chunk.usage.completion_tokens,
            total_token_count=chunk.usage.total_tokens,
            thoughts_token_count=thoughts_token_count,
            traffic_type=TrafficType.ON_DEMAND,
        )
        return APIStreamFinal(
            candidates=[candidate],
            usage_metadata=usage,
            model_version=model_name,
            response_id=chunk.id,
            create_time=create_time,
        )

    return APIStreamChunk(
        candidates=[candidate],
        model_version=model_name,
        response_id=chunk.id,
        create_time=create_time,
    )


@router.post("/{model}:streamGenerateContent")
async def stream_generate_content(req: APIRequest, model: str):
    target = config.resolve_model(model)
    if not target:
        raise HTTPException(status_code=404, detail="Model not found")

    new_model = target.model
    data: Optional[BaseRequest] = None
    log("template").info(f"is {target.template}")
    match target.template:
        case "deepseek":
            data = DeepseekRequest.build(req, new_model, True)
        case "openai":
            data = OpenaiRequest.build(req, new_model, True)
        case "gemini":
            data = GoogleRequest.build(req, new_model, True)

    if not data:
        raise HTTPException(
            status_code=400, detail="Invalid request for the specified model"
        )

    func = getChatFuncion(target, True)
    response_stream = await func(**data.args())

    async def _google_sse_generator():
        request_start_time = datetime.now(timezone.utc)
        async for chunk in response_stream:  # type: ignore
            # Determine if this is the final chunk based on finish_reason to match standard.jsonl
            is_final = chunk.candidates and any(
                c.finish_reason for c in chunk.candidates
            )

            update = {}
            if not chunk.create_time:
                update["create_time"] = request_start_time
            if not chunk.model_version:
                update["model_version"] = target.model or model

            if not is_final:
                # Non-final chunk: strictly only include traffic_type in usage_metadata to match standard.jsonl
                current_traffic_type = TrafficType.ON_DEMAND
                if chunk.usage_metadata and chunk.usage_metadata.traffic_type:
                    current_traffic_type = chunk.usage_metadata.traffic_type

                update["usage_metadata"] = GenerateContentResponseUsageMetadata(
                    traffic_type=current_traffic_type
                )
            else:
                # Final chunk: ensure traffic_type is set and keep full usage metadata
                if not chunk.usage_metadata:
                    update["usage_metadata"] = GenerateContentResponseUsageMetadata(
                        traffic_type=TrafficType.ON_DEMAND
                    )
                elif not chunk.usage_metadata.traffic_type:
                    new_usage = chunk.usage_metadata.model_copy(
                        update={"traffic_type": TrafficType.ON_DEMAND}
                    )
                    update["usage_metadata"] = new_usage

            if update:
                chunk = chunk.model_copy(update=update)

            if is_final:
                api_chunk = APIStreamFinal(**chunk.model_dump(exclude_none=True))
            else:
                api_chunk = APIStreamChunk(**chunk.model_dump(exclude_none=True))

            # Exclude internal SDK fields and fields not present in standard.jsonl
            exclude_fields = {
                "sdk_http_response",
                "model_status",
                "parsed",
                "automatic_function_calling_history",
                "prompt_feedback",
            }
            chunk_dict = api_chunk.model_dump(
                by_alias=True, exclude_none=True, mode="json", exclude=exclude_fields
            )
            yield f"data: {json.dumps(chunk_dict)}\n\n"

    async def _openai_sse_generator():
        accumulated_tool_calls = {}  # tool_call_index -> {name, args_str}

        async for chunk in response_stream:  # type: ignore
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
                gemini_chunk = APIStreamFinal(
                    candidates=[
                        Candidate(
                            index=0,
                            finish_reason=_map_finish_reason(
                                chunk.choices[0].finish_reason
                            ),
                        )
                    ],
                    usage_metadata=GenerateContentResponseUsageMetadata(
                        traffic_type=TrafficType.ON_DEMAND
                    ),
                    model_version=target.model or model,
                    response_id=chunk.id,
                )
            elif is_finished and not isinstance(gemini_chunk, APIStreamFinal):
                # Upgrade to APIStreamFinal if it's finished but doesn't have usage yet
                gemini_chunk = APIStreamFinal(
                    candidates=gemini_chunk.candidates,
                    usage_metadata=GenerateContentResponseUsageMetadata(
                        traffic_type=TrafficType.ON_DEMAND
                    ),
                    model_version=gemini_chunk.model_version,
                    response_id=gemini_chunk.response_id,
                    create_time=gemini_chunk.create_time,
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
                    tool_parts.append(
                        Part(
                            function_call=FunctionCall(name=tc_data["name"], args=args)
                        )
                    )

                if gemini_chunk.candidates:
                    if not gemini_chunk.candidates[0].content:
                        gemini_chunk.candidates[0].content = Content(
                            role="model", parts=[]
                        )
                    if not gemini_chunk.candidates[0].content.parts:
                        gemini_chunk.candidates[0].content.parts = []
                    gemini_chunk.candidates[0].content.parts.extend(tool_parts)
                accumulated_tool_calls = {}  # Clear after flushing

            # Ensure role and usage metadata consistency
            if gemini_chunk.candidates and gemini_chunk.candidates[0].content:
                gemini_chunk.candidates[0].content.role = "model"

            chunk_dict = gemini_chunk.model_dump(
                by_alias=True, exclude_none=True, mode="json"
            )
            yield f"data: {json.dumps(chunk_dict)}\n\n"

    match target.template:
        case "deepseek":
            return StreamingResponse(
                _openai_sse_generator(), media_type="text/event-stream"
            )
        case "openai":
            return StreamingResponse(
                _openai_sse_generator(), media_type="text/event-stream"
            )
        case "gemini":
            return StreamingResponse(
                _google_sse_generator(), media_type="text/event-stream"
            )
