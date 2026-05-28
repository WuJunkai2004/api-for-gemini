import sys

from api_for_gemini.app.utils.settings import Settings
from api_for_gemini.utils.logger import log


def ui_handler():
    settings = Settings()
    try:
        import mesop as me
        from mesop.bin.bin import main as mesop_main
    except ImportError:
        log.error(
            "Mesop not found. Please install the 'ui' extra: pip install api-for-gemini[ui]"
        )
        sys.exit(1)

    # Path to the UI main file
    from api_for_gemini.utils.path import PACKAGE_ROOT

    ui_main = PACKAGE_ROOT / "ui" / "main.py"

    if not ui_main.exists():
        log.error(f"UI main file not found at {ui_main}")
        sys.exit(1)

    log.info(f"Starting Mesop UI on port {settings.port}...")
    try:
        mesop_main(["mesop"])
    except KeyboardInterrupt:
        log.info("UI stopped by user")
