import json
from pathlib import Path

from api_for_gemini.server.schema.model.deepseek import DeepseekRequest
from api_for_gemini.server.schema.request import APIRequest

file_path = Path(__file__).parent.parent / "example/cli_sent.json"


def main():
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    model = APIRequest.model_validate(data)
    print(DeepseekRequest.build(model, "test"))


if __name__ == "__main__":
    main()
