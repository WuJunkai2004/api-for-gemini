import json

from fastapi import Request


async def print_request(request: Request, path: str):
    body_bytes = await request.body()
    body_text = body_bytes.decode("utf-8", errors="replace") if body_bytes else None
    body_display = body_text
    if body_text:
        try:
            body_display = json.dumps(json.loads(body_text), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pass

    headers = dict(request.headers)
    headers_display = json.dumps(headers, indent=2, ensure_ascii=False)

    print(
        f"\n{'='*60}"
        f"\n[PROBE] {request.method} /{path}"
        f"\n{'='*60}"
        f"\nClient    : {request.client.host if request.client else 'N/A'}"
        f"\nURL       : {request.url}"
        f"\nHeaders   : {headers_display}"
        f"\nQuery     : {dict(request.query_params)}"
        f"\nBody      : {body_display or '(empty)'}"
        f"\n{'='*60}\n"
    )
