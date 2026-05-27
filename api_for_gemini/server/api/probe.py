from fastapi import APIRouter, Request

from api_for_gemini.server.utils.logger import print_request

router = APIRouter()


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def probe(request: Request, path: str):
    await print_request(request, path)

    return {
        "method": request.method,
        "path": f"/{path}",
        "client": request.client.host if request.client else None,
    }
