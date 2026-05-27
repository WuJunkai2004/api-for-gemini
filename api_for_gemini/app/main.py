from api_for_gemini.app.utils.settings import Settings
from api_for_gemini.app.commands import setup_handler, config_handler, start_handler

def main():
    settings = Settings()

    handlers = {
        "setup": setup_handler,
        "config": config_handler,
        "start": start_handler,
    }

    handler = handlers.get(settings.command or "")
    if handler:
        handler()

if __name__ == "__main__":
    main()
