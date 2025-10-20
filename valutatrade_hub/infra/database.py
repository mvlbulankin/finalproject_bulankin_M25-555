import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.utils import ensure_dir
from ..infra.settings import SingletonMeta


class DatabaseManager(metaclass=SingletonMeta):  # Используем тот же метакласс
    def __init__(self):
        self._lock = threading.Lock()
        self.data_path: str = "data"  # Будет перезаписано из Settings

    def set_data_path(self, path: str):
        self.data_path = path

    def load(self, filename: str) -> List[Dict[str, Any]]:
        with self._lock:
            path = Path(self.data_path) / filename
            ensure_dir(self.data_path)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return []

    def save(self, filename: str, data: List[Dict[str, Any]]):
        with self._lock:
            path = Path(self.data_path) / filename
            ensure_dir(self.data_path)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, default=str)

    def find_by_id(
            self,
            filename: str,
            id_key: str,
            target_id: int,
        ) -> Optional[Dict[str, Any]]:
        data = self.load(filename)
        return next((item for item in data if item.get(id_key) == target_id), None)

    def update_by_id(
            self,
            filename: str,
            id_key: str,
            target_id: int,
            new_data: Dict[str, Any],
        ):
        data = self.load(filename)
        for i, item in enumerate(data):
            if item.get(id_key) == target_id:
                data[i] = new_data
                self.save(filename, data)
                return
        raise ValueError(f"Элемент с ID {target_id} не найден")
