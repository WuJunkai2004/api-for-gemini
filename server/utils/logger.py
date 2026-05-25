import json
import logging
import sys

from fastapi import Request
from uvicorn.logging import DefaultFormatter

COLOR = "\x1b[36m"
RESET = "\x1b[0m"


async def print_request(request: Request, path: str):
    body_bytes = await request.body()
    body_text = body_bytes.decode("utf-8", errors="replace") if body_bytes else None
    body_display = body_text
    if body_text:
        try:
            body_display = json.dumps(
                json.loads(body_text), indent=2, ensure_ascii=False
            )
        except json.JSONDecodeError:
            pass

    headers = dict(request.headers)
    headers_display = json.dumps(headers, indent=2, ensure_ascii=False)

    print(
        f"\n{'=' * 60}"
        f"\n[PROBE] {request.method} /{path}"
        f"\n{'=' * 60}"
        f"\nClient    : {request.client.host if request.client else 'N/A'}"
        f"\nURL       : {request.url}"
        f"\nHeaders   : {headers_display}"
        f"\nQuery     : {dict(request.query_params)}"
        f"\nBody      : {body_display or '(empty)'}"
        f"\n{'=' * 60}\n"
    )


class LogFactory:
    def __init__(self):
        self.logger = self._setup_logger(
            "default.logger", logging.INFO, "%(levelprefix)s %(message)s"
        )

    @staticmethod
    def _setup_logger(name: str, level: int | str, fmt: str) -> logging.Logger:
        logger = logging.getLogger(name)
        if logger.handlers:
            return logger
        logger.setLevel(level)
        logger.propagate = False
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(DefaultFormatter(fmt=fmt, use_colors=True))
        logger.addHandler(console_handler)
        return logger

    def __call__(self, name: str) -> logging.Logger:
        return self._setup_logger(
            name, logging.INFO, f"%(levelprefix)s [{COLOR}%(name)s{RESET}] %(message)s"
        )

    def __getattr__(self, func_name: str):
        if hasattr(self.logger, func_name):
            return getattr(self.logger, func_name)
        else:
            raise AttributeError(f"'LogFactory' object has no attribute '{func_name}'")


log = LogFactory()
