import tomllib
from pathlib import Path
from typing import Any, Dict


class SingletonMeta(type):#TODO pyproject.toml → секция [tool.valutatrade] 
    _instances: Dict[type, 'SettingsLoader'] = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

class SettingsLoader(metaclass=SingletonMeta):
    def __init__(self):
        self._config: Dict[str, Any] = {}
        self.reload()

    def reload(self):
        config_path = Path("pyproject.toml")
        if config_path.exists():
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
                self._config = data.get("tool", {}).get("valutatrade", {})
        else:
            # Дефолтные значения
            self._config = {
                "data_path": "data",
                "rates_ttl_seconds": 300,  # 5 мин
                "default_base_currency": "USD",
                "log_path": "logs",
                "log_level": "INFO",
                "supported_currencies": ["USD", "EUR", "BTC", "ETH", "RUB"]
            }

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)
