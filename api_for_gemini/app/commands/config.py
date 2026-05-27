import shutil
from pathlib import Path

from api_for_gemini.app.utils.settings import Settings
from api_for_gemini.utils.logger import log
from api_for_gemini.utils.path import CONFIG_EXAMPLE


def config_handler():
    """Handle the config command."""
    settings = Settings()
    if not settings.new:
        log.info("Available options for 'config': -n/--new [path]")

    dest_path = Path(settings.path)

    # If it's an existing directory or doesn't look like a file, assume it's a directory
    if dest_path.is_dir() or not dest_path.suffix:
        dest_file = dest_path / "config.toml"
    else:
        dest_file = dest_path

    if dest_file.exists():
        log.error(f"Config file already exists at {dest_file}")
        return

    # Ensure parent directory exists
    dest_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        shutil.copy(CONFIG_EXAMPLE, dest_file)
        log.info(f"Successfully created config file at {dest_file}")
    except Exception as e:
        log.error(f"Failed to create config file: {e}")
