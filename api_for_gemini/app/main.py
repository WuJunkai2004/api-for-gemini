from api_for_gemini.app.commands import (
    config_handler,
    context_handler,
    setup_handler,
    start_handler,
    ui_handler,
)
from api_for_gemini.app.utils.settings import Settings


def main():
    settings = Settings()

    handlers = {
        "setup": setup_handler,
        "config": config_handler,
        "start": start_handler,
        "context": context_handler,
        "ui": ui_handler,
    }

    handler = handlers.get(settings.command or "")
    if handler:
        handler()


if __name__ == "__main__":
    main()
