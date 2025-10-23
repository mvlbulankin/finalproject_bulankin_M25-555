import functools
import logging
from datetime import datetime
from typing import Any, Callable

from valutatrade_hub.infra.settings import SettingsLoader

logger = logging.getLogger("ValutaTrade")
settings = SettingsLoader()

def log_action(action: str):
    """Декоратор для логирования операций."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            verbose = kwargs.get("verbose", False)
            user_id = kwargs.get("user_id")
            username = None
            currency = kwargs.get("currency_code") or kwargs.get("currency")
            amount = kwargs.get("amount")
            rate = None
            base = settings.get("default_base_currency", "USD")
            try:
                result = func(*args, **kwargs)
                log_msg = {
                    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                    "action": action,
                    "user_id": user_id,
                    "username": username,
                    "currency": currency,
                    "amount": amount,
                    "rate": rate,
                    "base": base,
                    "result": "OK",
                }
                if verbose:
                    log_msg["context"] = "Детали изменений (было→стало)"
                logger.info(" ".join(
                    [f'{k}="{v}"' for k, v in log_msg.items() if v is not None]
                ))
                return result
            except Exception as e:
                log_msg = {
                    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                    "action": action,
                    "user_id": user_id,
                    "username": username,
                    "currency": currency,
                    "amount": amount,
                    "rate": rate,
                    "base": base,
                    "result": "ERROR",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
                logger.error(" ".join(
                    [f'{k}="{v}"' for k, v in log_msg.items() if v is not None]
                ))
                raise
        return wrapper
    return decorator
