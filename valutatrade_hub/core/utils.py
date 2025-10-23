import json
import os
from typing import Any, Dict, List

from .currencies import get_currency


def ensure_dir(directory: str):
    os.makedirs(directory, exist_ok=True)

def load_json(filename: str) -> List[Dict[str, Any]]:
    ensure_dir("data")
    path = os.path.join("data", filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_json(filename: str, data: List[Dict[str, Any]]):
    ensure_dir("data")
    path = os.path.join("data", filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, default=str)

def validate_currency_code(code: str) -> str:
    try:
        currency = get_currency(code)
        return currency.code
    except Exception:
        raise ValueError(f"Некорректный код валюты: {code}")

def convert_amount(amount: float, from_code: str, to_code: str, rate: float) -> float:
    if from_code == to_code:
        return amount
    return amount * rate if rate else 0.0

def load_env_file():
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )

    env_path = os.path.join(project_root, ".env")

    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ[key.strip()] = value.strip()
