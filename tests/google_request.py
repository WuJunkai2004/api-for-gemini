import json
from pathlib import Path

from server.schema.request import APIRequest

file_path = Path(__file__).parent.parent / "example" / "cli_sent.json"


def main():
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    model = APIRequest.model_validate(data)
    print(model)


if __name__ == "__main__":
    main()
