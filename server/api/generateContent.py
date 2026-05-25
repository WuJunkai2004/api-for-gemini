import json

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse, StreamingResponse
from google.genai import Client
from google.genai.types import GenerateContentConfig

from server.schema.request.google import GoogleRequest

router = APIRouter()


def _build_config(req: GoogleRequest) -> GenerateContentConfig | None:
    if req.generation_config is None and req.system_instruction is None:
        return None
    config = req.generation_config or GenerateContentConfig()
    if req.system_instruction is not None:
        config.system_instruction = req.system_instruction
    return config


@router.post("{model}:generateContent")
async def generate_content(
    google_request: GoogleRequest,
    model: str,
    x_goog_api_key: str = Header(default=""),
):
    client = Client(api_key=x_goog_api_key)
    config = _build_config(google_request)

    kwargs: dict = {"model": model, "contents": google_request.contents}
    if config is not None:
        kwargs["config"] = config

    response = await client.aio.models.generate_content(**kwargs)
    data = response.model_dump(exclude_none=True, mode="json")
    return JSONResponse(content=data)


@router.post("{model}:streamGenerateContent")
async def stream_generate_content(
    google_request: GoogleRequest,
    model: str,
    x_goog_api_key: str = Header(default=""),
):
    client = Client(api_key=x_goog_api_key)
    config = _build_config(google_request)

    kwargs: dict = {"model": model, "contents": google_request.contents}
    if config is not None:
        kwargs["config"] = config

    response_stream = await client.aio.models.generate_content_stream(**kwargs)

    async def _sse_generator():
        async for chunk in response_stream:
            chunk_dict = chunk.model_dump(exclude_none=True, mode="json")
            yield f"data: {json.dumps(chunk_dict)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
    )
