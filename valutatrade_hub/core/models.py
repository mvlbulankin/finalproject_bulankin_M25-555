import hashlib
from datetime import datetime
from typing import Any, Dict, Optional

from .currencies import Currency, get_currency
from .exceptions import InsufficientFundsError


class User:
    """Класс пользователя системы с хранением зашифрованного пароля."""

    def __init__(
            self,
            user_id: int,
            username: str,
            hashed_password: str,
            salt: str,
            registration_date: datetime,
        ):
        """Инициализация пользователя с валидацией."""
        if not username:
            raise ValueError("Имя не может быть пустым")
        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    def get_user_info(self) -> str:
        """Выводит информацию о пользователе без пароля."""
        return (
            f"ID: {self._user_id}, "
            f"Username: {self._username}, "
            f"Registered: {self._registration_date}"
        )

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль с хешированием."""
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        self._hashed_password = hashlib.sha256(
            (new_password + self._salt).encode()
        ).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Проверяет введённый пароль."""
        hashed = hashlib.sha256((password + self._salt).encode()).hexdigest()
        return hashed == self._hashed_password

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        if not value:
            raise ValueError("Имя не может быть пустым")
        self._username = value

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь для JSON с timestamp "YYYY-MM-DDTHH:MM:SS"."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.strftime("%Y-%m-%dT%H:%M:%S")
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Десериализация из словаря."""
        try:
            reg_date = datetime.strptime(data["registration_date"], "%Y-%m-%dT%H:%M:%S")
        except ValueError as e:
            raise ValueError(
                f"Неверный формат даты регистрации '{data['registration_date']}': {e}"
            )
        return cls(
            data["user_id"],
            data["username"],
            data["hashed_password"],
            data["salt"],
            reg_date,
        )


class Wallet:
    """Кошелёк для одной валюты с балансом и операциями."""

    def __init__(self, currency_code: str, balance: float = 0.0):
        """Инициализация с интеграцией Currency."""
        self.currency: Currency = get_currency(currency_code)
        self._balance = balance

    def deposit(self, amount: float) -> None:
        """Пополнение баланса."""
        if amount <= 0:
            raise ValueError("Сумма должна быть положительным числом")
        if not isinstance(amount, (int, float)):
            raise ValueError("Сумма должна быть числом")
        self._balance += amount

    def withdraw(self, amount: float) -> None:
        """Снятие средств с проверкой баланса."""
        if amount <= 0:
            raise ValueError("Сумма должна быть положительным числом")
        if not isinstance(amount, (int, float)):
            raise ValueError("Сумма должна быть числом")
        if amount > self._balance:
            raise InsufficientFundsError(self._balance, amount, self.currency.code)
        self._balance -= amount

    def get_balance_info(self) -> str:
        """Информация о балансе."""
        return f"{self.currency.get_display_info()}: {self._balance:.4f}"

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Сеттер баланса (для прямого присвоения, с проверкой <0)."""
        if not isinstance(value, (int, float)):
            raise ValueError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = value

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация."""
        return {
            "currency_code": self.currency.code,
            "balance": self._balance
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Wallet':
        """Десериализация."""
        currency_code = data.get("currency_code")
        balance = float(data.get("balance", 0.0))
        return cls(currency_code, balance)


class Portfolio:
    """Портфель пользователя с набором кошельков."""

    def __init__(self, user: User):
        """Инициализация с USD по умолчанию."""
        self._user = user
        self._wallets: Dict[str, Wallet] = {}
        self.add_currency("USD")

    def add_currency(self, currency_code: str) -> None:
        """Добавление нового кошелька."""
        if currency_code in self._wallets:
            raise ValueError(f"Кошелёк {currency_code} уже существует")
        self._wallets[currency_code] = Wallet(currency_code)

    def get_wallet(self, currency_code: str) -> Optional[Wallet]:
        """Получение кошелька."""
        return self._wallets.get(currency_code.upper())

    def get_total_value(self, base_currency: str = "USD") -> float:
        """Общая стоимость в базовой валюте (любая из supported)."""
        total = 0.0
        from .usecases import get_rate
        for code, wallet in self._wallets.items():
            if code == base_currency:
                total += wallet.balance
            else:
                try:
                    rate, _ = get_rate(code, base_currency)
                    total += wallet.balance * rate
                except ValueError:
                    pass
        return total

    @property
    def user(self) -> User:
        """Геттер пользователя (read-only)."""
        return self._user

    @property
    def wallets(self) -> Dict[str, Wallet]:
        """Копия словаря кошельков."""
        return self._wallets.copy()

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация."""
        wallets_dict = {
            code: wallet.to_dict() for code, wallet in self._wallets.items()
        }
        return {
            "user_id": self._user.user_id,
            "wallets": wallets_dict
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], user: User) -> 'Portfolio':
        """Десериализация."""
        portfolio = cls(user)
        for code, w_data in data.get("wallets", {}).items():
            currency_code = w_data.get("currency_code", code)
            balance = float(w_data.get("balance", 0.0))
            wallet = Wallet(currency_code, balance)
            portfolio._wallets[code] = wallet
        return portfolio
