import json
from pathlib import Path

from api_for_gemini.server.schema.model.openai import OpenaiRequest
from api_for_gemini.server.schema.request import APIRequest

file_path = Path(__file__).parent.parent / "referrence/receive/1779807931.json"


def main():
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    model = APIRequest.model_validate(data)
    print(OpenaiRequest.build(model, "test"))


if __name__ == "__main__":
    main()
