import shutil
from pathlib import Path

from api_for_gemini.app.utils.settings import Settings


def setup_handler():
    settings = Settings()
    """Handle the setup command."""
    print(
        f"Setting up (global={settings.is_global}, local={settings.is_local}, config={settings.config_path})"
    )

    src = Path("config.example.toml")
    if not src.exists():
        # Try to find it relative to this file inside the package
        src = Path(__file__).parent.parent.parent / "config.example.toml"

    dst = Path(settings.config_path) if settings.config_path else Path("config.toml")

    if not src.exists():
        print(
            f"Error: config.example.toml not found. (Checked CWD and {src.absolute()})"
        )
        return

    if dst.exists():
        confirm = input(f"{dst} already exists. Overwrite? (y/n): ").lower()
        if confirm != "y":
            return

    shutil.copy(src, dst)
    print(f"Initialized {dst} from {src}")
