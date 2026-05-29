from pathlib import Path

import uvicorn

from api_for_gemini.app.utils.settings import Settings
from api_for_gemini.server.utils.config import ConfigManager
from api_for_gemini.utils.logger import log


def start_handler():
    """Handle the start command."""
    settings = Settings()
    if settings.config_path:
        config_file = Path(settings.config_path)
        if not config_file.exists():
            log("app").error(f"Config file {settings.config_path} does not exist.")
            return
        ConfigManager(config_path=config_file.absolute())
        log("app").info(f"Using config: {settings.config_path}")

    log("app").info(f"Starting API for Gemini (debug={settings.debug})...")
    uvicorn.run(
        "api_for_gemini.server.main:app",
        host="127.0.0.1",
        port=18000,
        reload=settings.debug,
        reload_dirs=["api_for_gemini/server"] if settings.debug else None,
    )
