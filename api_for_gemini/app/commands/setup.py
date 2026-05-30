import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

from api_for_gemini.app.utils.settings import Settings
from api_for_gemini.utils.logger import log


def setup_handler():
    settings = Settings()
    """Handle the setup command."""
    log("setup").info(
        f"Setting up (global={settings.is_global}, local={settings.is_local}, config={settings.config_path})"
    )

    # 1. Handle config.toml setup
    src = Path(settings.config_path) if settings.config_path else Path("config.toml")

    if not src.exists():
        log.error("config.toml not found.")
        raise FileNotFoundError(
            f"config.toml not found. Please create one at {src.absolute()} or specify --config with a valid path."
        )

    if settings.is_global:
        dst = Path.home() / ".gemini" / "config.toml"
    else:
        dst = Path("config.toml")

    should_copy = True
    if dst.exists():
        confirm = input(f"{dst} already exists. Overwrite? (y/n): ").lower()
        if confirm != "y":
            should_copy = False

    if should_copy:
        shutil.copy(src, dst)
        log.info(f"Initialized {dst} from {src}")

    # 2. Handle Gemini hooks setup
    setup_gemini_hooks(settings.is_global)

    # 3. Handle environment variables
    setup_environment_variables(settings.is_global, settings.is_local)


def setup_gemini_hooks(is_global: bool):
    """Add hook to .gemini/settings.json"""
    if is_global:
        gemini_dir = Path.home() / ".gemini"
    else:
        gemini_dir = Path(".gemini")

    settings_path = gemini_dir / "settings.json"

    if not gemini_dir.exists():
        gemini_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"Created directory: {gemini_dir}")

    settings_data = {}
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings_data = json.load(f)
        except Exception as e:
            log.warning(f"Failed to read existing {settings_path}: {e}")

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
    for matcher_obj in settings_data["hooks"]["SessionStart"]:
        if isinstance(matcher_obj, dict) and "hooks" in matcher_obj:
            for hook in matcher_obj["hooks"]:
                if isinstance(hook, dict) and hook.get("name") == "gema-context":
                    exists = True
                    break
        if exists:
            break

    if not exists:
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
        log.info(f"Added gema-context hook to {settings_path}")
    else:
        log.info(f"gema-context hook already exists in {settings_path}")


def setup_environment_variables(is_global: bool, is_local: bool):
    """Setup GOOGLE_GEMINI_BASE_URL environment variable."""
    var_name = "GOOGLE_GEMINI_BASE_URL"
    var_value = "http://127.0.0.1:18000"

    if is_global:
        updated_any = False
        home = Path.home()

        # 1. Unix-like shells (including Git Bash on Windows)
        rc_files = [
            home / ".bashrc",
            home / ".zshrc",
        ]
        export_line = f'export {var_name}="{var_value}"'

        for rc in rc_files:
            if not rc.exists():
                continue
            try:
                content = rc.read_text(encoding="utf-8", errors="ignore")
                if f"export {var_name}" not in content:
                    with open(rc, "a", encoding="utf-8") as f:
                        f.write(f"\n# Added by gema setup\n{export_line}\n")
                    log.info(f"Added {var_name} to {rc}")
                    updated_any = True
                else:
                    log.info(f"{var_name} already present in {rc}")
            except Exception as e:
                log.warning(f"Failed to update {rc}: {e}")

        # 2. Windows-specific persistence
        if platform.system() == "Windows":
            try:
                # Check if already set to the same value in the current session
                # or try to set it via setx
                current_val = os.environ.get(var_name)
                if current_val != var_value:
                    # setx sets it permanently for the user (HKEY_CURRENT_USER\Environment)
                    subprocess.run(
                        ["setx", var_name, var_value], check=True, capture_output=True
                    )
                    log.info(
                        f"Set persistent environment variable {var_name} for the current user."
                    )
                    updated_any = True
                else:
                    log.info(f"{var_name} is already set correctly in environment.")
            except Exception as e:
                log.warning(f"Failed to set persistent variable via setx: {e}")

        if updated_any:
            log.info(f"Global environment variable {var_name} configured.")
            log.info(
                "Please restart your shell or run the following to apply to the current session:"
            )
            if platform.system() == "Windows":
                log.info(f'PowerShell: $env:{var_name} = "{var_value}"')
                log.info(f"CMD:        set {var_name}={var_value}")
            else:
                log.info(
                    f'Shell:      source <your_rc_file> or export {var_name}="{var_value}"'
                )

    if is_local:
        # Help user inject into current shell
        log.info(f"To inject {var_name} into your CURRENT shell session, please run:")
        if platform.system() == "Windows":
            # Heuristic to detect PowerShell
            if "PSModulePath" in os.environ:
                log.info(f'$env:{var_name} = "{var_value}"')
            else:
                log.info(f"set {var_name}={var_value}")
        else:
            log.info(f'export {var_name}="{var_value}"')
