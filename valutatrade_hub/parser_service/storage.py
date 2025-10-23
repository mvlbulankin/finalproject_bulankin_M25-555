import json
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List

from .config import ParserConfig


class Storage:
    def __init__(self, config: ParserConfig):
        self.config = config
        self.rates_path = config.RATES_FILE_PATH
        self.history_path = config.HISTORY_FILE_PATH
        os.makedirs(os.path.dirname(self.rates_path), exist_ok=True)

    def save_rates(self, pairs: Dict[str, Dict[str, Any]]):
        data = {
            "pairs": pairs,
            "last_refresh": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        }
        self._atomic_write(self.rates_path, data)

    def append_history(self, records: List[Dict[str, Any]]):
        existing = self._load_json(self.history_path, default=[])
        new_ids = {r["id"] for r in records}
        filtered_existing = [e for e in existing if e["id"] not in new_ids]
        updated = filtered_existing + records
        self._atomic_write(self.history_path, updated)

    def _load_json(self, path: str, default: Any = None):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def _atomic_write(self, path: str, data: Any):
        dir_path = os.path.dirname(path)
        os.makedirs(dir_path, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            suffix=".json",
            dir=dir_path,
            encoding="utf-8",
            ) as tmp:
            json.dump(data, tmp, indent=4, default=str)
            tmp_path = tmp.name
        os.replace(tmp_path, path)
