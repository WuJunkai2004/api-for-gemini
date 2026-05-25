import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from server.schema.request.google import GoogleRequest
from server.schema.response.google import GoogleReponse

router = APIRouter()

GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com"


@router.post("{model}:generateContent")
async def generate_content(request: Request, model: str):
    body = await request.json()
    GoogleRequest.model_validate(body)

    api_key = request.headers.get("x-goog-api-key", "")
    url = f"{GOOGLE_BASE_URL}/v1beta/models/{model}:generateContent?key={api_key}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()

    GoogleReponse.model_validate(data)
    return data


@router.post("{model}:streamGenerateContent")
async def stream_generate_content(request: Request, model: str):
    body = await request.json()
    GoogleRequest.model_validate(body)

    api_key = request.headers.get("x-goog-api-key", "")
    url = f"{GOOGLE_BASE_URL}/v1beta/models/{model}:streamGenerateContent?key={api_key}&alt=sse"

    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, json=body) as resp:
            resp.raise_for_status()

            async def stream():
                async for chunk in resp.aiter_bytes():
                    yield chunk

            return StreamingResponse(
                stream(),
                media_type="text/event-stream",
            )
