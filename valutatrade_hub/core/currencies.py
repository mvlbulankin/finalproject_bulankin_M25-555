from abc import ABC, abstractmethod
from typing import Dict

from .exceptions import CurrencyNotFoundError


class Currency(ABC):#TODO фабричный метод get_currency() и обработка неизвестных кодов?
    def __init__(self, name: str, code: str):
        if not name or not isinstance(name, str):
            raise ValueError("name не может быть пустой строкой")
        if (
            not code
            or not isinstance(code, str)
            or len(code) < 2
            or len(code) > 5
            or not code.isupper()
            or ' ' in code
            ):
            raise ValueError("code — верхний регистр, 2–5 символов, без пробелов")
        self.name = name  # человекочитаемое имя (например, "US Dollar", "Bitcoin")
        self.code = code  # ISO-код или общепринятый тикер ("USD", "EUR", "BTC", "ETH")

    @abstractmethod
    def get_display_info(self) -> str:
        pass

# Реестр валют
_CURRENCIES_REGISTRY: Dict[str, Currency] = {}

def register_currency(currency: Currency):
    _CURRENCIES_REGISTRY[currency.code] = currency

def get_currency(code: str) -> Currency:
    code = code.upper()
    if code not in _CURRENCIES_REGISTRY:
        raise CurrencyNotFoundError(code)
    return _CURRENCIES_REGISTRY[code]

class FiatCurrency(Currency):
    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self.issuing_country = issuing_country  # страна эмиссии

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"

class CryptoCurrency(Currency):
    def __init__(self, name: str, code: str, algorithm: str, market_cap: float):
        super().__init__(name, code)
        self.algorithm = algorithm    # алгоритм
        if market_cap < 0:
            raise ValueError("market_cap не может быть отрицательным")
        self.market_cap = market_cap  # последняя известная капитализация

    def get_display_info(self) -> str:
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"
        )

# Инициализация реестра
register_currency(FiatCurrency("US Dollar", "USD", "United States"))
register_currency(FiatCurrency("Euro", "EUR", "Eurozone"))
register_currency(CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12))
register_currency(CryptoCurrency("Ethereum", "ETH", "Ethash", 4.50e11))
register_currency(FiatCurrency("Russian Ruble", "RUB", "Russia"))
