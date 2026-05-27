import os
from pathlib import Path
import uvicorn

def start_handler(settings):
    """Handle the start command."""
    if settings.config_path:
        config_file = Path(settings.config_path)
        if not config_file.exists():
            print(f"Error: Config file {settings.config_path} does not exist.")
            return
        os.environ["GROVIDER_CONFIG"] = str(config_file.absolute())
        print(f"Using config: {settings.config_path}")

    print("Starting Grovider server...")
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=18000,
        reload=True,
        reload_dirs=["server"],
    )
