import logging
import sys

from uvicorn.logging import DefaultFormatter

COLOR = "\x1b[36m"
RESET = "\x1b[0m"


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
