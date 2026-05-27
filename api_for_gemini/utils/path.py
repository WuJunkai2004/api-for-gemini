from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GEMINI_CONFIG_DIR = Path.home() / ".gemini"

CONFIG_EXAMPLE = Path(__file__).parent.parent / "config.example.toml"
CONFIG_DEFAULT = ROOT / "config.toml"
