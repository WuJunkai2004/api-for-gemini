from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
PACKAGE_ROOT = Path(__file__).parent.parent
GEMINI_CONFIG_DIR = Path.home() / ".gemini"

CONFIG_EXAMPLE = PACKAGE_ROOT / "config.example.toml"
CONFIG_DEFAULT = ROOT / "config.toml"
