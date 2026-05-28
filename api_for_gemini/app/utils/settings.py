import argparse
from typing import Optional


class Settings:
    _instance: Optional["Settings"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if self._loaded:
            return
        self._loaded = True
        self._parse_args()

    def _parse_args(self):
        parser = argparse.ArgumentParser(
            prog="gema", description="Gema CLI - Gemini API Proxy Manager"
        )
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # setup command
        setup_parser = subparsers.add_parser(
            "setup", help="Setup the environment and configuration"
        )
        setup_parser.add_argument(
            "-g",
            "--global",
            action="store_true",
            dest="is_global",
            help="Setup globally",
        )
        setup_parser.add_argument(
            "-l", "--local", action="store_true", dest="is_local", help="Setup locally"
        )
        setup_parser.add_argument(
            "-c", "--config", dest="config_path", help="Path to config file"
        )

        # config command
        config_parser = subparsers.add_parser("config", help="Manage configuration")
        config_parser.add_argument(
            "-n", "--new", action="store_true", help="Create a new configuration"
        )
        config_parser.add_argument(
            "path",
            nargs="?",
            default=".",
            help="Path to create the config file (default: current directory)",
        )

        # start command
        start_parser = subparsers.add_parser("start", help="Start the proxy server")
        start_parser.add_argument(
            "-c", "--config", dest="config_path", help="Path to config file"
        )
        start_parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            dest="debug",
            help="Enable debug mode with hot reload",
        )

        # context command (used as hook)
        subparsers.add_parser("context", help="Provide context for Gemini CLI")

        # ui command
        ui_parser = subparsers.add_parser("ui", help="Start the Mesop UI")
        ui_parser.add_argument(
            "-p", "--port", type=int, default=32123, help="Port to run the UI on"
        )
        ui_parser.add_argument(
            "-d", "--debug", action="store_true", help="Run in debug mode"
        )

        self.args = parser.parse_args()

    @property
    def command(self) -> Optional[str]:
        return self.args.command

    def __getattr__(self, name):
        """Allow direct access to args attributes."""
        return getattr(self.args, name)
