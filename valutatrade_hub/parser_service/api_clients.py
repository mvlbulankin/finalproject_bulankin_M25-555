import abc
from typing import Any, Dict

import requests

from ..core.exceptions import ApiRequestError
from .config import ParserConfig


class BaseApiClient(abc.ABC):
    @abc.abstractmethod
    def fetch_rates(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает {pair: {'rate': float, 'meta': dict}}"""
        pass

class CoinGeckoClient(BaseApiClient):
    def __init__(self, config: ParserConfig):
        self.config = config

    def fetch_rates(self) -> Dict[str, Dict[str, Any]]:
        ids = ",".join(
            self.config.CRYPTO_ID_MAP[code] for code in self.config.CRYPTO_CURRENCIES
        )
        url = (
            f"{self.config.COINGECKO_URL}?ids={ids}"
            f"&vs_currencies={self.config.BASE_CURRENCY.lower()}"
        )
        try:
            resp = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            rates = {}
            for code, coin_id in self.config.CRYPTO_ID_MAP.items():
                if (
                    coin_id in data
                    and self.config.BASE_CURRENCY.lower() in data[coin_id]
                    ):
                    pair = f"{code}_{self.config.BASE_CURRENCY}"
                    rates[pair] = {
                        "rate": data[coin_id][self.config.BASE_CURRENCY.lower()],
                        "meta": {
                            "raw_id": coin_id,
                            "request_ms": resp.elapsed.total_seconds() * 1000,
                            "status_code": resp.status_code,
                            "etag": resp.headers.get("etag", "")
                        }
                    }
            return rates
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"CoinGecko: {str(e)}")

class ExchangeRateApiClient(BaseApiClient):
    def __init__(self, config: ParserConfig):
        self.config = config

    def fetch_rates(self) -> Dict[str, Dict[str, Any]]:
        if not self.config.EXCHANGERATE_API_KEY:
            raise ValueError("EXCHANGERATE_API_KEY не установлен")
        url = (
            f"{self.config.EXCHANGERATE_API_URL}/"
            f"{self.config.EXCHANGERATE_API_KEY}/latest/"
            f"{self.config.BASE_CURRENCY}"
        )
        try:
            resp = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if data.get("result") != "success":
                raise ApiRequestError(f"ExchangeRate-API: {data}")
            rates = {}
            base = self.config.BASE_CURRENCY
            for code in self.config.FIAT_CURRENCIES:
                if code in data["rates"]:
                    usd_to_code = data["rates"][code]
                    rate_code_usd = 1 / usd_to_code if usd_to_code != 0 else 0.0
                    pair = f"{code}_{base}"
                    rates[pair] = {
                        "rate": rate_code_usd,
                        "meta": {
                            "raw_rate": usd_to_code,
                            "request_ms": resp.elapsed.total_seconds() * 1000,
                            "status_code": resp.status_code,
                            "time_last_update_utc": data.get("time_last_update_utc", "")
                        }
                    }
            return rates
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"ExchangeRate-API: {str(e)}")
