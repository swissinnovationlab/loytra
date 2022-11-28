from typing import Any, Optional
import json
import os
import os.path

_TOKENS_FILE_PATH = "~/.local/share/loytra/storage.json"
_TOKENS_FULL_PATH = os.path.abspath(os.path.expanduser(_TOKENS_FILE_PATH))

def _read() -> dict[str, Any]:
    if not os.path.exists(_TOKENS_FULL_PATH):
        return {}
    try:
        with open(_TOKENS_FULL_PATH, "r") as f:
            data = json.loads(f.read())
        if data is not None and isinstance(data, dict):
            return data
    except:
        pass
    return {}

def _write(data: dict[str, Any]) -> bool:
    dir_path = os.path.dirname(_TOKENS_FULL_PATH)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    try:
        with open(_TOKENS_FULL_PATH, "w+") as f:
            f.write(json.dumps(data, indent=2))
        return True
    except:
        return False

def storage_read_value(key: str) -> Optional[str]:
    data = _read()
    return data.get(key)

def storage_write_value(key: str, value: Any) -> bool:
    data = _read()
    data[key] = value
    return _write(data)

