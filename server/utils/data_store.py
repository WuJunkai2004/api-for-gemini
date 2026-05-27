import json
import time
from pathlib import Path
from typing import Any

from server.utils.logger import log


def save_request_log(request_data: Any, transformed_data: Any):
    """
    Saves the original request data and the transformed data to the datas/ directory.

    Args:
        request_data: The incoming APIRequest object.
        transformed_data: The transformed BaseRequest object (or similar).
    """
    timestamp = int(time.time())

    # Define directories
    base_dir = Path("datas")
    requests_dir = base_dir / "requests"
    transformed_dir = base_dir / "transformed"

    # Ensure directories exist
    requests_dir.mkdir(parents=True, exist_ok=True)
    transformed_dir.mkdir(parents=True, exist_ok=True)

    # Save request data as .json
    request_path = requests_dir / f"{timestamp}.json"
    try:
        data_to_save = request_data.model_dump(exclude_none=True)
        try:
            text_to_save = json.dumps(data_to_save, ensure_ascii=False, indent=2)
        except:
            log("error").info(f"储存 {request_path} 出错")
            text_to_save = str(data_to_save)

        with open(request_path, "w", encoding="utf-8") as f:
            print(text_to_save, file=f)
    except Exception as e:
        print(f"Failed to save request log: {e}")

    # Save transformed data as .py (using str())
    transformed_path = transformed_dir / f"{timestamp}.py"
    try:
        with open(transformed_path, "w", encoding="utf-8") as f:
            f.write(str(transformed_data))
    except Exception as e:
        print(f"Failed to save transformed log: {e}")
