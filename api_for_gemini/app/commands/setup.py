import json
import shutil
from pathlib import Path

from api_for_gemini.app.utils.settings import Settings


def setup_handler():
    settings = Settings()
    """Handle the setup command."""
    print(
        f"Setting up (global={settings.is_global}, local={settings.is_local}, config={settings.config_path})"
    )

    # 1. Handle config.toml setup
    src = Path("config.example.toml")
    if not src.exists():
        # Try to find it relative to this file inside the package
        src = Path(__file__).parent.parent.parent / "config.example.toml"

    dst = Path(settings.config_path) if settings.config_path else Path("config.toml")

    if not src.exists():
        print(
            f"Error: config.example.toml not found. (Checked CWD and {src.absolute()})"
        )
    else:
        should_copy = True
        if dst.exists():
            confirm = input(f"{dst} already exists. Overwrite? (y/n): ").lower()
            if confirm != "y":
                should_copy = False

        if should_copy:
            shutil.copy(src, dst)
            print(f"Initialized {dst} from {src}")

    # 2. Handle Gemini hooks setup
    if settings.is_global or settings.is_local:
        setup_gemini_hooks(settings.is_global)


def setup_gemini_hooks(is_global: bool):
    """Add hook to .gemini/settings.json"""
    if is_global:
        gemini_dir = Path.home() / ".gemini"
    else:
        gemini_dir = Path(".gemini")

    settings_path = gemini_dir / "settings.json"

    if not gemini_dir.exists():
        gemini_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {gemini_dir}")

    settings_data = {}
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings_data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to read existing {settings_path}: {e}")

    # Define the hook to add
    # Using 'gema start' as a hook for SessionStart or similar if needed
    # But based on user request, we just need to "add hook" to settings.json
    # We'll add a sample SessionStart hook that might be useful for the project
    if "hooks" not in settings_data:
        settings_data["hooks"] = {}

    if "SessionStart" not in settings_data["hooks"]:
        settings_data["hooks"]["SessionStart"] = []

    # Check if already exists
    exists = False
    for hook_type, matchers in settings_data["hooks"].items():
        if isinstance(matchers, list):
            for matcher_obj in matchers:
                if isinstance(matcher_obj, dict) and "hooks" in matcher_obj:
                    for hook in matcher_obj["hooks"]:
                        if (
                            isinstance(hook, dict)
                            and hook.get("name") == "gema-context"
                        ):
                            exists = True
                            break
                if exists:
                    break
        if exists:
            break

    if not exists:
        if "SessionStart" not in settings_data["hooks"]:
            settings_data["hooks"]["SessionStart"] = []

        settings_data["hooks"]["SessionStart"].append(
            {
                "matcher": "*",
                "hooks": [
                    {
                        "name": "gema-context",
                        "type": "command",
                        "command": "gema context",
                        "timeout": 10000,
                    }
                ],
            }
        )

        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings_data, f, indent=4)
        print(f"Added gema-context hook to {settings_path}")
    else:
        print(f"gema-context hook already exists in {settings_path}")
