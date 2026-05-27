import os
from pathlib import Path

import uvicorn
from utils.logger import log


def start_handler(settings):
    """Handle the start command."""
    if settings.config_path:
        config_file = Path(settings.config_path)
        if not config_file.exists():
            log("app").error(f"Config file {settings.config_path} does not exist.")
            return
        os.environ["GROVIDER_CONFIG"] = str(config_file.absolute())
        log("app").info(f"Using config: {settings.config_path}")

    log("app").info(f"Starting API for Gemini (debug={settings.debug})...")
    uvicorn.run(
        "api_for_gemini.server.main:app",
        host="0.0.0.0",
        port=18000,
        reload=settings.debug,
        reload_dirs=["api_for_gemini/server"] if settings.debug else None,
    )
