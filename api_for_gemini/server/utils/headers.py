from fastapi import Request

from api_for_gemini.server.utils.types import ai_provider_template


def filter_headers(req: Request) -> dict:
    headers = dict(req.headers)
    exclude_prefixes = ()
    exclude_exact = (
        "authorization",
        "accept-encoding",
        "x-goog-api-key",
        "content-length",
    )
    return {
        k: v
        for k, v in headers.items()
        if not k.lower().startswith(exclude_prefixes) and k.lower() not in exclude_exact
    }


def inject_headers(template: ai_provider_template, headers: dict) -> dict:
    match template:
        case "openai":
            return {"extra_headers": headers}
        case _:
            return {}
