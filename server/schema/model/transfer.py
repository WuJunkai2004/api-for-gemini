from server.schema.model.to_gemini import transfer as to_gemini
from server.schema.model.to_openai import transfer as to_openai
from server.schema.request import GoogleRequest
from server.utils.config import config


def transfer(req: GoogleRequest, model: str, isStream: bool):
    target_model = config.resolve_model(model)
    if not target_model:
        raise ValueError(f"Model {model} not found in config.")
    if target_model.schema == "gemini":
        return to_gemini(req, target_model.model, isStream)
    else:
        return to_openai(req, target_model.model, isStream)
