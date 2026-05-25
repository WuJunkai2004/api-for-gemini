import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from google.genai import Client as GeminiClient
from openai import AsyncOpenAI as OpenAIClient

type AIClient = OpenAIClient | GeminiClient | None


@dataclass
class ProviderConfig:
    name: str
    schema: str
    api_url: str
    api_key: str


@dataclass
class ModelConfig:
    name: str
    schema: str = ""
    api_url: str = ""
    api_key: str = ""
    model: str = ""
    _client: Any = field(default=None, init=False, repr=False)

    def __post_init__(self):
        if self.schema == "gemini":
            self._client = GeminiClient(api_key=self.api_key)
        else:
            self._client = OpenAIClient(
                base_url=self.api_url,
                api_key=self.api_key,
            )

    def get_client(self) -> AIClient:
        return self._client


@dataclass
class TransferConfig:
    from_model: str
    as_model: str


@dataclass
class Config:
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    models: dict[str, ModelConfig] = field(default_factory=dict)
    transfers: list[TransferConfig] = field(default_factory=list)


class ConfigManager:
    _instance: "ConfigManager | None" = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self, config_path: str | Path | None = None):
        if self._loaded:
            return
        self._loaded = True
        self._config = Config()
        if config_path is not None:
            self.load(config_path)

    def load(self, config_path: str | Path):
        path = Path(config_path)
        with open(path, "rb") as f:
            data = tomllib.load(f)
        self._parse(data)

    def _parse(self, data: dict):
        providers = data.get("provider", {})
        for name, entries in providers.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                self._config.providers[name] = ProviderConfig(
                    name=name,
                    schema=entry.get("schema", ""),
                    api_url=entry.get("api_url", ""),
                    api_key=entry.get("api_key", ""),
                )

        models = data.get("model", {})
        for name, entries in models.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                provider_name = entry.get("provider", "")
                provider = self._config.providers.get(provider_name)
                self._config.models[name] = ModelConfig(
                    name=name,
                    schema=entry.get("schema", "")
                    or (provider.schema if provider else ""),
                    api_url=entry.get("api_url", "")
                    or (provider.api_url if provider else ""),
                    api_key=entry.get("api_key", "")
                    or (provider.api_key if provider else ""),
                    model=entry.get("model", ""),
                )

        transfers = data.get("transfer", [])
        for entry in transfers:
            self._config.transfers.append(
                TransferConfig(
                    from_model=entry.get("from", ""),
                    as_model=entry.get("as", ""),
                )
            )

    @property
    def config(self) -> Config:
        return self._config

    def get_provider(self, name: str) -> ProviderConfig | None:
        return self._config.providers.get(name)

    def get_model(self, name: str) -> ModelConfig | None:
        return self._config.models.get(name)

    def get_client(self, name: str) -> AIClient:
        model = self._config.models.get(name)
        if model:
            return model.get_client()
        return None

    def resolve_model(self, model_name: str) -> ModelConfig | None:
        for t in self._config.transfers:
            if t.from_model == model_name:
                model = self.get_model(t.as_model)
                if model:
                    return model
        return self.get_model(model_name)

    @classmethod
    def reset(cls):
        cls._instance = None


config = ConfigManager(Path(__file__).parent.parent.parent / "config.toml")
