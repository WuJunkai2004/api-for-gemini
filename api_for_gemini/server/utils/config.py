try:
    import tomllib  # type: ignore
except ImportError:
    import tomli as tomllib  # type: ignore
from pathlib import Path
from typing import Literal, Optional

from google.genai import Client as GeminiClient
from openai import AsyncOpenAI as OpenAIClient
from pydantic import BaseModel, model_validator

from api_for_gemini.utils.logger import log
from api_for_gemini.utils.path import CONFIG_DEFAULT
from api_for_gemini.utils.stars import StarMatch

AIClient = OpenAIClient | GeminiClient


class ProviderSchema(BaseModel):
    template: Literal["gemini", "openai", "deepseek"] = "openai"
    api_url: str
    api_key: Optional[str] = None


class ModelSchema(BaseModel):
    provider: Optional[str] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    template: Literal["gemini", "openai", "deepseek"] = "openai"
    model: str

    # 验证：
    # provider 和 api_url 不能同时存在也不能同时不存在
    # 如果 provider 存在，则 api_url 和 api_key 必须为 None
    # 如果同时不存在，则抛出异常
    @model_validator(mode="after")
    def fix(self) -> "ModelSchema":
        if self.provider and self.api_url:
            self.api_url = None
            self.api_key = None
        elif not self.provider and not self.api_url:
            raise ValueError("Either provider or api_url must be provided.")
        return self


class TransferSchema(BaseModel):
    make: str
    to: str


class Config(BaseModel):
    provider: dict[str, ProviderSchema]
    model: dict[str, ModelSchema]
    transfer: list[TransferSchema]

    @model_validator(mode="after")
    def finish(self) -> "Config":
        # 回填 model 中缺失的 api_url 和 api_key
        for model_name, model in self.model.items():
            if not model.provider:
                continue
            if model.provider not in self.provider:
                raise ValueError(
                    f"Model {model_name} references unknown provider {model.provider}."
                )
            # 如果 model.provider 存在，则回填 model.api_url 和 model.api_key
            provider = self.provider[model.provider]
            model.api_url = provider.api_url
            model.api_key = provider.api_key
            model.template = provider.template
        # 验证 transfer 中的 to 是否都存在于 model 中
        for pair in self.transfer:
            if pair.to not in self.model:
                raise ValueError(
                    f"Transfer to {pair.to} references unknown model {pair.to}."
                )
        return self


def _load(path: Path):
    with path.open("rb") as f:
        return tomllib.load(f)


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
        if not config_path:
            # First check CWD (standard for user running the CLI)
            config_path = Path("config.toml")
            if not config_path.exists():
                # Then check next to the package (for development)
                config_path = CONFIG_DEFAULT
            if not config_path.exists():
                log("config").error("No config file found. Please run `gema setup`")
                exit(1)

        self._config = Config.model_validate(_load(Path(config_path)))
        self._rules = [(StarMatch(p.make), p.to) for p in self._config.transfer]

        log("config").info(f"Config loaded from {config_path}")
        log("config").info(f"provider: {', '.join(self._config.provider.keys())}")
        log("config").info(f"model: {', '.join(self._config.model.keys())}")

    def get_model(self, name: str) -> Optional[ModelSchema]:
        """根据模型名称获取模型配置"""
        return self._config.model.get(name)

    def resolve_model(self, name: str) -> Optional[ModelSchema]:
        """根据模型名称获取转换后的模型配置"""
        for rule, to_model in self._rules:
            if rule.match(name):
                return self.get_model(to_model)

        return self.get_model(name)
